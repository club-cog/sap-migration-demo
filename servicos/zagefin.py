"""ZAGEFIN: ponto de entrada da agenda para atendimento PARTICULAR confirmado (SZ1 -> SE1/SZ8)."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

from servicos.modelos import BaseProtheus, Rejeicao, ResultadoTitulosReceber, TituloReceber
from servicos.protheus import arredondar, data_valida, truncar, val

logger = logging.getLogger(__name__)

TIPO_PARTICULAR = "P"
CONVENIO_PARTICULAR = "PAR"
PREFIXO_TITULO = "ATE"
PARCELA_UNICA = " "

FORMA_PIX = "PIX"
FORMA_CARTAO = "CARTAO"
FORMA_BOLETO = "BOLETO"

TIPO_PIX = "PIX"
TIPO_CARTAO = "CC"
TIPO_BOLETO = "BOL"

FATOR_PIX = Decimal("0.95")  # 5% de desconto no PIX
MAX_PARCELAS_CARTAO = 3  # até 3x sem juros
DIAS_ENTRE_PARCELAS = 30
DIAS_VENCIMENTO_BOLETO = 3

REJEICAO_SEM_PRECO = "SEM_PRECO"
REJEICAO_PARCELAS_INVALIDAS = "PARCELAS_INVALIDAS"
REJEICAO_FORMA_INVALIDA = "FORMA_INVALIDA"


def parcelas_cartao(valor: Decimal, quantidade: Decimal) -> list[Decimal]:
    """Parcela truncada; os centavos restantes vão na 1ª parcela (`For nX := 1 To nParc`)."""
    parcela = truncar(valor / quantidade)
    resto = valor - parcela * quantidade
    return [parcela + (resto if numero == 1 else 0) for numero in range(1, int(quantidade) + 1)]


def gerar_titulos_receber(base: BaseProtheus, numate: str, feriados: Iterable[date] = ()) -> ResultadoTitulosReceber:
    atendimento = next((a for a in base.atendimentos if a.numate == numate), None)
    if atendimento is None or atendimento.tipo != TIPO_PARTICULAR:
        return ResultadoTitulosReceber(gerou=False)

    logger.info("ZAGEFIN: gerando titulos atendimento %s", numate)

    def titulo(parcela: str, tipo: str, valor: Decimal, vencimento: date) -> TituloReceber:
        return TituloReceber(
            prefixo=PREFIXO_TITULO,
            numero=numate,
            parcela=parcela,
            tipo=tipo,
            cliente=atendimento.paciente,
            emissao=atendimento.data,
            vencimento=vencimento,
            valor=valor,
        )

    def rejeitar(motivo: str) -> ResultadoTitulosReceber:
        logger.info("ZAGEFIN: atendimento %s rejeitado (%s)", numate, motivo)
        return ResultadoTitulosReceber(gerou=False, rejeicao=Rejeicao(numate=numate, motivo=motivo))

    preco = base.precos.get((CONVENIO_PARTICULAR, atendimento.procedimento))
    if preco is None:
        return rejeitar(REJEICAO_SEM_PRECO)
    valor = preco.valor

    forma = atendimento.forma_pagamento.strip()
    if forma == FORMA_PIX:
        return ResultadoTitulosReceber(
            gerou=True, titulos=[titulo(PARCELA_UNICA, TIPO_PIX, arredondar(valor * FATOR_PIX), atendimento.data)]
        )

    if forma == FORMA_CARTAO:
        quantidade = val(atendimento.parcelas)
        if quantidade < 1 or quantidade > MAX_PARCELAS_CARTAO:
            return rejeitar(REJEICAO_PARCELAS_INVALIDAS)
        valores = parcelas_cartao(valor, quantidade)
        titulos = [
            titulo(
                PARCELA_UNICA if quantidade == 1 else chr(64 + numero),
                TIPO_CARTAO,
                valor_parcela,
                atendimento.data + timedelta(days=DIAS_ENTRE_PARCELAS * numero),
            )
            for numero, valor_parcela in enumerate(valores, start=1)
        ]
        return ResultadoTitulosReceber(gerou=True, titulos=titulos)

    if forma == FORMA_BOLETO:
        vencimento = data_valida(atendimento.data + timedelta(days=DIAS_VENCIMENTO_BOLETO), feriados)
        return ResultadoTitulosReceber(gerou=True, titulos=[titulo(PARCELA_UNICA, TIPO_BOLETO, valor, vencimento)])

    return rejeitar(REJEICAO_FORMA_INVALIDA)
