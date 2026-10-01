#Include "Protheus.ch"

/*/{Protheus.doc} ZAGEFIN
Ponto de entrada chamado pela agenda quando um atendimento PARTICULAR e confirmado.
Gera os titulos a receber (SE1) conforme a forma de pagamento.

  PIX    - 5% de desconto, titulo unico com vencimento no dia
  CARTAO - ate 3x sem juros, vencimento a cada 30 dias; centavos na 1a parcela
  BOLETO - titulo unico, vencimento em 3 dias (proximo dia util)

@param  cNumAte  numero do atendimento (SZ1)
@return lRet     .T. se gerou os titulos
@author TI Rede Clinica Exemplo
@since  21/06/2015
/*/
User Function ZAGEFIN(cNumAte)
	Local lRet     := .T.
	Local nValor   := 0
	Local nParc    := 0
	Local nVlParc  := 0
	Local nResto   := 0
	Local cParcela := ""
	Local cTipo    := ""
	Local dVencto  := CToD("")
	Local nX       := 0

	SZ1->(DbSetOrder(1)) // Z1_FILIAL + Z1_NUMATE
	If !SZ1->(DbSeek(xFilial("SZ1") + cNumAte)) .Or. SZ1->Z1_TIPO <> "P"
		Return .F.
	EndIf

	SA1->(DbSetOrder(1))
	SA1->(DbSeek(xFilial("SA1") + SZ1->Z1_PACIENT))
	ConOut("ZAGEFIN: gerando titulos atendimento " + cNumAte + " CPF " + AllTrim(SA1->A1_CGC))

	SZ3->(DbSetOrder(1))
	If !SZ3->(DbSeek(xFilial("SZ3") + "PAR" + SZ1->Z1_PROCED))
		GravaRejeicao(cNumAte, "SEM_PRECO")
		Return .F.
	EndIf
	nValor := SZ3->Z3_VALOR

	Do Case
	Case AllTrim(SZ1->Z1_FORMPG) == "PIX"
		GravaSE1(cNumAte, " ", "PIX", Round(nValor * 0.95, 2), SZ1->Z1_DATA)

	Case AllTrim(SZ1->Z1_FORMPG) == "CARTAO"
		nParc := Val(SZ1->Z1_PARCELA)
		If nParc < 1 .Or. nParc > 3
			GravaRejeicao(cNumAte, "PARCELAS_INVALIDAS")
			lRet := .F.
		Else
			nVlParc := NoRound(nValor / nParc, 2)
			nResto  := nValor - (nVlParc * nParc)
			For nX := 1 To nParc
				cParcela := IIf(nParc == 1, " ", Chr(64 + nX)) // A, B, C
				dVencto  := SZ1->Z1_DATA + (30 * nX)
				GravaSE1(cNumAte, cParcela, "CC", nVlParc + IIf(nX == 1, nResto, 0), dVencto)
			Next nX
		EndIf

	Case AllTrim(SZ1->Z1_FORMPG) == "BOLETO"
		GravaSE1(cNumAte, " ", "BOL", nValor, DataValida(SZ1->Z1_DATA + 3, .T.))

	OtherWise
		GravaRejeicao(cNumAte, "FORMA_INVALIDA")
		lRet := .F.
	EndCase

Return lRet

Static Function GravaSE1(cNumAte, cParcela, cTipo, nValor, dVencto)
	RecLock("SE1", .T.)
	SE1->E1_FILIAL  := xFilial("SE1")
	SE1->E1_PREFIXO := "ATE"
	SE1->E1_NUM     := cNumAte
	SE1->E1_PARCELA := cParcela
	SE1->E1_TIPO    := cTipo
	SE1->E1_CLIENTE := SZ1->Z1_PACIENT
	SE1->E1_EMISSAO := SZ1->Z1_DATA
	SE1->E1_VENCTO  := dVencto
	SE1->E1_VALOR   := nValor
	SE1->(MsUnlock())
Return

Static Function GravaRejeicao(cNumAte, cMotivo)
	RecLock("SZ8", .T.)
	SZ8->Z8_FILIAL := xFilial("SZ8")
	SZ8->Z8_NUMATE := cNumAte
	SZ8->Z8_MOTIVO := cMotivo
	SZ8->(MsUnlock())
Return
