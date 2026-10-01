#Include "Protheus.ch"
#Include "TopConn.ch"

/*/{Protheus.doc} FATCONV
Gera o lote de faturamento de convenio da competencia.
Le os atendimentos realizados (SZ1), valoriza pela tabela do convenio (SZ3),
aplica as regras de glosa e grava o lote (SZ5) e os itens do lote (SZ6).

Perguntas (grupo FATCONV):
  MV_PAR01 - Convenio            (C,3)
  MV_PAR02 - Competencia AAAAMM  (C,6)
  MV_PAR03 - Data de envio       (D,8)

@author  TI Rede Clinica Exemplo
@since   14/03/2011
@version 3.7 - 2019: regra de RM acima de R$ 1.000 (chamado 48211)
              2021: desconto contratual Saude Mais (aditivo 2021/04)
/*/
User Function FATCONV()
	Local cConven  := ""
	Local cCompet  := ""
	Local dEnvio   := CToD("")
	Local cLote    := ""
	Local aItens   := {}
	Local aGuias   := {}
	Local nPrazo   := 0
	Local nCopart  := 0
	Local cExigAut := ""
	Local nVlTab   := 0
	Local nVlDesc  := 0
	Local nVlCop   := 0
	Local nVlFat   := 0
	Local nVlGlo   := 0
	Local cMotivo  := ""
	Local cCobre   := ""
	Local nTotBru  := 0
	Local nTotDes  := 0
	Local nTotCop  := 0
	Local nTotFat  := 0
	Local nTotGlo  := 0
	Local nX       := 0

	If !Pergunte("FATCONV", .T.)
		Return .F.
	EndIf

	cConven := MV_PAR01
	cCompet := MV_PAR02
	dEnvio  := MV_PAR03

	// Parametros do convenio
	DbSelectArea("SZ2")
	SZ2->(DbSetOrder(1)) // Z2_FILIAL + Z2_COD
	If !SZ2->(DbSeek(xFilial("SZ2") + cConven))
		MsgStop("Convenio " + cConven + " nao cadastrado.", "FATCONV")
		Return .F.
	EndIf
	nPrazo   := SZ2->Z2_PRAZO
	nCopart  := SZ2->Z2_COPART
	cExigAut := SZ2->Z2_EXIGAUT

	// Atendimentos de convenio realizados na competencia e ainda nao faturados
	DbSelectArea("SZ1")
	SZ1->(DbSetOrder(3)) // Z1_FILIAL + Z1_CONVEN + DTOS(Z1_DATA) + Z1_NUMATE
	SZ1->(DbSeek(xFilial("SZ1") + cConven + cCompet, .T.))

	While SZ1->(!Eof()) .And. SZ1->Z1_FILIAL == xFilial("SZ1") ;
			.And. SZ1->Z1_CONVEN == cConven ;
			.And. Left(DToS(SZ1->Z1_DATA), 6) == cCompet

		If SZ1->Z1_TIPO <> "C" .Or. SZ1->Z1_STATUS <> "R" .Or. !Empty(SZ1->Z1_FATURA)
			SZ1->(DbSkip())
			Loop
		EndIf

		// LOG de auditoria pedido pela operadora (2014)
		SA1->(DbSetOrder(1))
		SA1->(DbSeek(xFilial("SA1") + SZ1->Z1_PACIENT))
		ConOut("FATCONV: atendimento " + SZ1->Z1_NUMATE + " paciente " + AllTrim(SA1->A1_NOME) + ;
			" CPF " + AllTrim(SA1->A1_CGC) + " guia " + AllTrim(SZ1->Z1_GUIA))

		nVlTab  := 0
		nVlDesc := 0
		nVlCop  := 0
		nVlFat  := 0
		nVlGlo  := 0
		cMotivo := ""
		cCobre  := "N"

		SZ3->(DbSetOrder(1)) // Z3_FILIAL + Z3_CONVEN + Z3_PROCED
		If SZ3->(DbSeek(xFilial("SZ3") + cConven + SZ1->Z1_PROCED))
			nVlTab := SZ3->Z3_VALOR
			cCobre := SZ3->Z3_COBERTO
		EndIf

		// ---- Regras de glosa (a primeira que bater define o motivo) ----
		If nVlTab == 0
			cMotivo := "G05" // procedimento sem preco na tabela
		ElseIf cCobre <> "S"
			cMotivo := "G02" // procedimento nao coberto pelo plano
		ElseIf Empty(SZ1->Z1_AUTORIZ) .And. (cExigAut == "S" .Or. nVlTab > 1000)
			// chamado 48211: operadoras glosam RM/alto custo sem senha, mesmo sem exigencia contratual
			cMotivo := "G01" // guia sem autorizacao
		ElseIf (dEnvio - SZ1->Z1_DATA) > nPrazo
			cMotivo := "G03" // enviado fora do prazo contratual
		ElseIf aScan(aGuias, AllTrim(SZ1->Z1_GUIA)) > 0
			cMotivo := "G04" // guia em duplicidade no lote
		EndIf

		If Empty(cMotivo)
			// aditivo 2021/04: Saude Mais tem 10% de desconto em consultas
			If cConven == "005" .And. Left(SZ1->Z1_PROCED, 4) == "1010"
				nVlDesc := Round(nVlTab * 0.10, 2)
			EndIf
			nVlCop := Round((nVlTab - nVlDesc) * nCopart / 100, 2)
			nVlFat := nVlTab - nVlDesc - nVlCop
		Else
			nVlGlo := nVlTab
		EndIf

		aAdd(aGuias, AllTrim(SZ1->Z1_GUIA))
		aAdd(aItens, {SZ1->(Recno()), SZ1->Z1_NUMATE, SZ1->Z1_GUIA, SZ1->Z1_PROCED, ;
			nVlTab, nVlDesc, nVlCop, nVlFat, nVlGlo, cMotivo})

		nTotBru += nVlTab
		nTotDes += nVlDesc
		nTotCop += nVlCop
		nTotFat += nVlFat
		nTotGlo += nVlGlo

		SZ1->(DbSkip())
	EndDo

	If Len(aItens) == 0
		MsgInfo("Nenhum atendimento a faturar para o convenio " + cConven + ".", "FATCONV")
		Return .F.
	EndIf

	Begin Transaction

		cLote := GetSXENum("SZ5", "Z5_LOTE")
		ConfirmSX8()

		RecLock("SZ5", .T.)
		SZ5->Z5_FILIAL  := xFilial("SZ5")
		SZ5->Z5_LOTE    := cLote
		SZ5->Z5_CONVEN  := cConven
		SZ5->Z5_COMPET  := cCompet
		SZ5->Z5_DTENVIO := dEnvio
		SZ5->Z5_QTDGUIA := Len(aItens)
		SZ5->Z5_VLBRUTO := nTotBru
		SZ5->Z5_VLDESC  := nTotDes
		SZ5->Z5_VLCOPAR := nTotCop
		SZ5->Z5_VLFAT   := nTotFat
		SZ5->Z5_VLGLOSA := nTotGlo
		SZ5->(MsUnlock())

		For nX := 1 To Len(aItens)
			RecLock("SZ6", .T.)
			SZ6->Z6_FILIAL  := xFilial("SZ6")
			SZ6->Z6_LOTE    := cLote
			SZ6->Z6_NUMATE  := aItens[nX][2]
			SZ6->Z6_GUIA    := aItens[nX][3]
			SZ6->Z6_PROCED  := aItens[nX][4]
			SZ6->Z6_VLTAB   := aItens[nX][5]
			SZ6->Z6_VLDESC  := aItens[nX][6]
			SZ6->Z6_VLCOPAR := aItens[nX][7]
			SZ6->Z6_VLFAT   := aItens[nX][8]
			SZ6->Z6_VLGLOSA := aItens[nX][9]
			SZ6->Z6_MOTGLO  := aItens[nX][10]
			SZ6->(MsUnlock())

			SZ1->(DbGoTo(aItens[nX][1]))
			RecLock("SZ1", .F.)
			SZ1->Z1_FATURA := cLote
			SZ1->(MsUnlock())
		Next nX

	End Transaction

	MsgInfo("Lote " + cLote + " gerado: " + cValToChar(Len(aItens)) + " guias, faturado R$ " + ;
		AllTrim(Transform(nTotFat, "@E 999,999,999.99")), "FATCONV")

Return .T.
