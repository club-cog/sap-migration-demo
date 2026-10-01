#Include "Protheus.ch"
#Include "TopConn.ch"

/*/{Protheus.doc} REPMED
Calcula o repasse medico da competencia e gera os titulos a pagar (SE2).
Base: itens aceitos dos lotes de convenio (SZ6) + atendimentos particulares (SZ1).
Precisa rodar DEPOIS do FATCONV de todos os convenios da competencia.

Perguntas (grupo REPMED):
  MV_PAR01 - Competencia AAAAMM (C,6)

@author  TI Rede Clinica Exemplo
@since   02/09/2012
@version 2.4 - 2016: exames de laboratorio proprio sem repasse
              2018: adicional de plantao no pronto atendimento (+5 pontos)
/*/
User Function REPMED()
	Local cCompet  := ""
	Local dEmissao := CToD("")
	Local dVencto  := CToD("")
	Local aMedicos := {}
	Local nPos     := 0
	Local nBase    := 0
	Local nPerc    := 0
	Local nValor   := 0
	Local nBruto   := 0
	Local nIRRF    := 0
	Local nPIS     := 0
	Local nCOFINS  := 0
	Local nCSLL    := 0
	Local nISS     := 0
	Local nLiq     := 0
	Local nX       := 0

	If !Pergunte("REPMED", .T.)
		Return .F.
	EndIf

	cCompet  := MV_PAR01
	dEmissao := LastDay(SToD(cCompet + "01"))
	dVencto  := DataValida(SToD(Left(DToS(dEmissao + 1), 6) + "15"), .T.)

	DbSelectArea("SZ1")
	SZ1->(DbSetOrder(2)) // Z1_FILIAL + DTOS(Z1_DATA) + Z1_NUMATE
	SZ1->(DbSeek(xFilial("SZ1") + cCompet, .T.))

	While SZ1->(!Eof()) .And. Left(DToS(SZ1->Z1_DATA), 6) == cCompet

		If SZ1->Z1_STATUS <> "R"
			SZ1->(DbSkip())
			Loop
		EndIf

		// 2016: laboratorio proprio, exames de patologia clinica (subgrupo 4.03) nao geram repasse
		If Left(SZ1->Z1_PROCED, 4) == "4030"
			SZ1->(DbSkip())
			Loop
		EndIf

		nBase := 0
		If SZ1->Z1_TIPO == "C"
			// so repassa o que foi aceito no lote (glosado nao entra)
			SZ6->(DbSetOrder(2)) // Z6_FILIAL + Z6_NUMATE
			If SZ6->(DbSeek(xFilial("SZ6") + SZ1->Z1_NUMATE)) .And. Empty(SZ6->Z6_MOTGLO)
				nBase := SZ6->Z6_VLTAB - SZ6->Z6_VLDESC // coparticipacao entra na base
			EndIf
		Else
			// particular: repasse sobre o valor de TABELA, nao sobre o recebido (PIX tem desconto)
			SZ3->(DbSetOrder(1))
			If SZ3->(DbSeek(xFilial("SZ3") + "PAR" + SZ1->Z1_PROCED))
				nBase := SZ3->Z3_VALOR
			EndIf
		EndIf

		If nBase > 0
			SZ4->(DbSetOrder(1)) // Z4_FILIAL + Z4_MEDICO
			If SZ4->(DbSeek(xFilial("SZ4") + SZ1->Z1_MEDICO))
				nPerc := SZ4->Z4_PERC
				// 2018: adicional de plantao
				If SZ1->Z1_PROCED == "10101039"
					nPerc += 5
				EndIf
				nValor := Round(nBase * nPerc / 100, 2)

				nPos := aScan(aMedicos, {|x| x[1] == SZ1->Z1_MEDICO})
				If nPos == 0
					aAdd(aMedicos, {SZ1->Z1_MEDICO, 0, SZ4->Z4_MUNISS, {}})
					nPos := Len(aMedicos)
				EndIf
				aMedicos[nPos][2] += nValor
				aAdd(aMedicos[nPos][4], {SZ1->Z1_NUMATE, SZ1->Z1_PROCED, nBase, nPerc, nValor})
			EndIf
		EndIf

		SZ1->(DbSkip())
	EndDo

	aSort(aMedicos, , , {|x, y| x[1] < y[1]})

	Begin Transaction
		For nX := 1 To Len(aMedicos)
			nBruto := aMedicos[nX][2]

			// IRRF 1,5% - dispensa quando o imposto e ate R$ 10,00
			nIRRF := Round(nBruto * 1.5 / 100, 2)
			If nIRRF <= 10
				nIRRF := 0
			EndIf

			// PIS/COFINS/CSLL (CSRF) - dispensa quando a soma e ate R$ 10,00
			nPIS    := Round(nBruto * 0.65 / 100, 2)
			nCOFINS := Round(nBruto * 3 / 100, 2)
			nCSLL   := Round(nBruto * 1 / 100, 2)
			If (nPIS + nCOFINS + nCSLL) <= 10
				nPIS    := 0
				nCOFINS := 0
				nCSLL   := 0
			EndIf

			// ISS 5% retido quando o municipio exige. NoRound: a prefeitura trunca (2013)
			nISS := 0
			If aMedicos[nX][3] == "S"
				nISS := NoRound(nBruto * 5 / 100, 2)
			EndIf

			nLiq := nBruto - nIRRF - nPIS - nCOFINS - nCSLL - nISS

			RecLock("SE2", .T.)
			SE2->E2_FILIAL  := xFilial("SE2")
			SE2->E2_PREFIXO := "REP"
			SE2->E2_NUM     := cCompet
			SE2->E2_PARCELA := " "
			SE2->E2_TIPO    := "NF"
			SE2->E2_FORNECE := aMedicos[nX][1]
			SE2->E2_EMISSAO := dEmissao
			SE2->E2_VENCTO  := dVencto
			SE2->E2_VLBRUTO := nBruto
			SE2->E2_IRRF    := nIRRF
			SE2->E2_PIS     := nPIS
			SE2->E2_COFINS  := nCOFINS
			SE2->E2_CSLL    := nCSLL
			SE2->E2_ISS     := nISS
			SE2->E2_VALOR   := nLiq
			SE2->(MsUnlock())

			GravaItens(cCompet, aMedicos[nX][1], aMedicos[nX][4])
		Next nX
	End Transaction

Return .T.

/*/{Protheus.doc} GravaItens
Grava a memoria de calculo do repasse (SZ7), usada pela auditoria medica.
/*/
Static Function GravaItens(cCompet, cMedico, aItens)
	Local nY := 0
	For nY := 1 To Len(aItens)
		RecLock("SZ7", .T.)
		SZ7->Z7_FILIAL := xFilial("SZ7")
		SZ7->Z7_COMPET := cCompet
		SZ7->Z7_MEDICO := cMedico
		SZ7->Z7_NUMATE := aItens[nY][1]
		SZ7->Z7_PROCED := aItens[nY][2]
		SZ7->Z7_BASE   := aItens[nY][3]
		SZ7->Z7_PERC   := aItens[nY][4]
		SZ7->Z7_VALOR  := aItens[nY][5]
		SZ7->(MsUnlock())
	Next nY
Return
