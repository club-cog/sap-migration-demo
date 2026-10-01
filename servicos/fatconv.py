"""FATCONV: lote de faturamento de convênio da competência (SZ1 + SZ3 -> SZ5/SZ6)."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from servicos.modelos import ZERO, BaseProtheus, ItemLote, LoteFaturamento, ResultadoFaturamento
from servicos.protheus import arredondar, dtos

logger = logging.getLogger(__name__)

TIPO_CONVENIO = "C"
STATUS_REALIZADO = "R"

GLOSA_SEM_AUTORIZACAO = "G01"
GLOSA_NAO_COBERTO = "G02"
GLOSA_FORA_PRAZO = "G03"
GLOSA_GUIA_DUPLICADA = "G04"
GLOSA_SEM_PRECO = "G05"

# Chamado 48211 (2019): operadoras glosam RM/alto custo sem senha, mesmo sem exigência contratual.
LIMITE_ALTO_CUSTO = Decimal("1000")

# Aditivo 2021/04: Saúde Mais tem 10% de desconto em consultas (procedimentos com prefixo 1010).
CONVENIO_SAUDE_MAIS = "005"
PREFIXO_CONSULTA = "1010"
PERCENTUAL_DESCONTO_SAUDE_MAIS = Decimal("0.10")


class ConvenioNaoCadastrado(LookupError):
    """`MsgStop("Convenio ... nao cadastrado.")`."""


class NenhumAtendimentoAFaturar(LookupError):
    """`MsgInfo("Nenhum atendimento a faturar ...")`."""


def motivo_glosa(
    valor_tabela: Decimal,
    coberto: str,
    autorizacao: str,
    exige_autorizacao: str,
    dias_ate_envio: int,
    prazo_dias: int,
    guia_ja_no_lote: bool,
) -> str:
    """Regras de glosa: a primeira que bater define o motivo. Retorna "" quando não há glosa."""
    if valor_tabela == 0:
        return GLOSA_SEM_PRECO
    if coberto != "S":
        return GLOSA_NAO_COBERTO
    if not autorizacao.strip() and (exige_autorizacao == "S" or valor_tabela > LIMITE_ALTO_CUSTO):
        return GLOSA_SEM_AUTORIZACAO
    if dias_ate_envio > prazo_dias:
        return GLOSA_FORA_PRAZO
    if guia_ja_no_lote:
        return GLOSA_GUIA_DUPLICADA
    return ""


def desconto_contratual(convenio: str, procedimento: str, valor_tabela: Decimal) -> Decimal:
    if convenio == CONVENIO_SAUDE_MAIS and procedimento[:4] == PREFIXO_CONSULTA:
        return arredondar(valor_tabela * PERCENTUAL_DESCONTO_SAUDE_MAIS)
    return ZERO


def faturar_convenio(
    base: BaseProtheus, convenio: str, competencia: str, data_envio: date, numero_lote: str
) -> ResultadoFaturamento:
    """Gera o lote do convênio na competência (AAAAMM).

    `numero_lote` substitui o `GetSXENum("SZ5", "Z5_LOTE")` e só é consumido quando o lote é gerado.
    """
    parametros = base.convenios.get(convenio)
    if parametros is None:
        raise ConvenioNaoCadastrado(f"Convenio {convenio} nao cadastrado.")

    # Índice 3 do SZ1: Z1_CONVEN + DTOS(Z1_DATA) + Z1_NUMATE
    candidatos = sorted(
        (a for a in base.atendimentos if a.convenio == convenio and dtos(a.data)[:6] == competencia),
        key=lambda a: (a.data, a.numate),
    )

    itens: list[ItemLote] = []
    guias: list[str] = []
    for atendimento in candidatos:
        if atendimento.tipo != TIPO_CONVENIO or atendimento.status != STATUS_REALIZADO or atendimento.fatura.strip():
            continue

        logger.info("FATCONV: atendimento %s", atendimento.numate)

        preco = base.precos.get((convenio, atendimento.procedimento))
        valor_tabela = preco.valor if preco else ZERO
        coberto = preco.coberto if preco else "N"
        guia = atendimento.guia.strip()

        motivo = motivo_glosa(
            valor_tabela=valor_tabela,
            coberto=coberto,
            autorizacao=atendimento.autorizacao,
            exige_autorizacao=parametros.exige_autorizacao,
            dias_ate_envio=(data_envio - atendimento.data).days,
            prazo_dias=parametros.prazo_dias,
            guia_ja_no_lote=guia in guias,
        )

        desconto = coparticipacao = faturado = glosa = ZERO
        if not motivo:
            desconto = desconto_contratual(convenio, atendimento.procedimento, valor_tabela)
            coparticipacao = arredondar((valor_tabela - desconto) * parametros.coparticipacao / 100)
            faturado = valor_tabela - desconto - coparticipacao
        else:
            glosa = valor_tabela

        guias.append(guia)
        itens.append(
            ItemLote(
                lote=numero_lote,
                numate=atendimento.numate,
                guia=atendimento.guia,
                procedimento=atendimento.procedimento,
                valor_tabela=valor_tabela,
                valor_desconto=desconto,
                valor_coparticipacao=coparticipacao,
                valor_faturado=faturado,
                valor_glosa=glosa,
                motivo_glosa=motivo,
            )
        )

    if not itens:
        raise NenhumAtendimentoAFaturar(f"Nenhum atendimento a faturar para o convenio {convenio}.")

    lote = LoteFaturamento(
        lote=numero_lote,
        convenio=convenio,
        competencia=competencia,
        data_envio=data_envio,
        qtd_guias=len(itens),
        valor_bruto=sum((i.valor_tabela for i in itens), ZERO),
        valor_desconto=sum((i.valor_desconto for i in itens), ZERO),
        valor_coparticipacao=sum((i.valor_coparticipacao for i in itens), ZERO),
        valor_faturado=sum((i.valor_faturado for i in itens), ZERO),
        valor_glosa=sum((i.valor_glosa for i in itens), ZERO),
    )
    logger.info("FATCONV: lote %s gerado com %d guias", numero_lote, len(itens))
    return ResultadoFaturamento(lote=lote, itens=itens, faturados={i.numate: numero_lote for i in itens})
