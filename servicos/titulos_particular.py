"""Migração de ZAGEFIN.prw: títulos a receber de atendimentos particulares."""

import logging
from datetime import timedelta
from decimal import Decimal

from servicos.modelos import Atendimento, Rejeicao, TituloReceber

__all__ = ["Rejeicao", "gerar_titulos", "processar_particulares"]
from servicos.repositorio import BaseLegado
from servicos.util import arredonda, proximo_dia_util, trunca

log = logging.getLogger(__name__)

DESCONTO_PIX = Decimal("0.95")
MAX_PARCELAS = 3
DIAS_BOLETO = 3


def gerar_titulos(base: BaseLegado, atendimento: Atendimento) -> list[TituloReceber] | Rejeicao | None:
    """ZAGEFIN: None quando o atendimento não é particular (Return .F. sem rejeição)."""
    if atendimento.tipo != "P":
        return None
    log.info("ZAGEFIN: gerando titulos atendimento %s", atendimento.numero)

    preco = base.precos.get(("PAR", atendimento.procedimento))
    if preco is None:
        return Rejeicao(atendimento.numero, "SEM_PRECO")
    valor = preco.valor

    def titulo(parcela: str, tipo: str, vl: Decimal, dias: int) -> TituloReceber:
        return TituloReceber(
            prefixo="ATE",
            numero=atendimento.numero,
            parcela=parcela,
            tipo=tipo,
            cliente=atendimento.paciente,
            emissao=atendimento.data,
            vencimento=atendimento.data + timedelta(days=dias),
            valor=vl,
        )

    forma = atendimento.forma_pagamento.strip()
    if forma == "PIX":
        return [titulo(" ", "PIX", arredonda(valor * DESCONTO_PIX), 0)]

    if forma == "CARTAO":
        try:
            n = int(atendimento.parcelas)
        except ValueError:
            n = 0  # Val() do ADVPL devolve 0 para texto inválido
        if not 1 <= n <= MAX_PARCELAS:
            return Rejeicao(atendimento.numero, "PARCELAS_INVALIDAS")
        vl_parcela = trunca(valor / n)
        resto = valor - vl_parcela * n
        return [
            titulo(" " if n == 1 else chr(64 + k), "CC", vl_parcela + (resto if k == 1 else 0), 30 * k)
            for k in range(1, n + 1)
        ]

    if forma == "BOLETO":
        t = titulo(" ", "BOL", valor, DIAS_BOLETO)
        return [TituloReceber(**{**t.__dict__, "vencimento": proximo_dia_util(t.vencimento)})]

    return Rejeicao(atendimento.numero, "FORMA_INVALIDA")


def processar_particulares(base: BaseLegado) -> tuple[list[TituloReceber], list[Rejeicao]]:
    titulos: list[TituloReceber] = []
    rejeicoes: list[Rejeicao] = []
    for atendimento in sorted(base.atendimentos, key=lambda a: a.numero):
        if atendimento.status != "R":
            continue
        resultado = gerar_titulos(base, atendimento)
        if isinstance(resultado, Rejeicao):
            rejeicoes.append(resultado)
        elif resultado:
            titulos.extend(resultado)
    return titulos, rejeicoes
