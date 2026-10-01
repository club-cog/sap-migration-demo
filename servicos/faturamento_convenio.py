"""Migração de FATCONV.prw: lote de faturamento de convênio com regras de glosa."""

import logging
from datetime import date
from decimal import Decimal

from servicos.modelos import Atendimento, Convenio, ItemLote, Lote
from servicos.repositorio import BaseLegado
from servicos.util import arredonda, dtos

log = logging.getLogger(__name__)

SEM_AUTORIZACAO = "G01"
NAO_COBERTO = "G02"
FORA_DO_PRAZO = "G03"
GUIA_DUPLICADA = "G04"
SEM_PRECO = "G05"

LIMITE_ALTO_CUSTO = Decimal("1000")  # chamado 48211
CONVENIO_DESCONTO_CONSULTA = "005"  # aditivo 2021/04
DESCONTO_CONSULTA = Decimal("0.10")


class ConvenioNaoCadastrado(Exception):
    pass


def _motivo_glosa(
    atendimento: Atendimento,
    convenio: Convenio,
    vl_tabela: Decimal,
    coberto: bool,
    data_envio: date,
    guias_no_lote: set[str],
) -> str:
    if vl_tabela == 0:
        return SEM_PRECO
    if not coberto:
        return NAO_COBERTO
    if not atendimento.autorizacao and (convenio.exige_autorizacao or vl_tabela > LIMITE_ALTO_CUSTO):
        return SEM_AUTORIZACAO
    if (data_envio - atendimento.data).days > convenio.prazo_dias:
        return FORA_DO_PRAZO
    if atendimento.guia in guias_no_lote:
        return GUIA_DUPLICADA
    return ""


def gerar_lote(
    base: BaseLegado, numero_lote: str, cod_convenio: str, competencia: str, data_envio: date
) -> Lote | None:
    """FATCONV: retorna None quando não há atendimentos a faturar (MsgInfo no legado)."""
    convenio = base.convenios.get(cod_convenio)
    if convenio is None:
        raise ConvenioNaoCadastrado(cod_convenio)

    elegiveis = sorted(
        (
            a
            for a in base.atendimentos
            if a.convenio == cod_convenio and dtos(a.data)[:6] == competencia and a.tipo == "C" and a.status == "R"
        ),
        key=lambda a: (a.data, a.numero),
    )

    itens: list[ItemLote] = []
    guias: set[str] = set()
    for atendimento in elegiveis:
        log.info("FATCONV: atendimento %s guia %s", atendimento.numero, atendimento.guia)

        preco = base.precos.get((cod_convenio, atendimento.procedimento))
        vl_tabela = preco.valor if preco else Decimal("0")
        coberto = preco.coberto if preco else False

        motivo = _motivo_glosa(atendimento, convenio, vl_tabela, coberto, data_envio, guias)
        vl_desc = vl_cop = vl_fat = vl_glosa = Decimal("0")
        if motivo:
            vl_glosa = vl_tabela
        else:
            if cod_convenio == CONVENIO_DESCONTO_CONSULTA and atendimento.procedimento.startswith("1010"):
                vl_desc = arredonda(vl_tabela * DESCONTO_CONSULTA)
            vl_cop = arredonda((vl_tabela - vl_desc) * convenio.copart_perc / 100)
            vl_fat = vl_tabela - vl_desc - vl_cop

        guias.add(atendimento.guia)
        itens.append(
            ItemLote(
                lote=numero_lote,
                atendimento=atendimento.numero,
                guia=atendimento.guia,
                procedimento=atendimento.procedimento,
                vl_tabela=vl_tabela,
                vl_desconto=vl_desc,
                vl_copart=vl_cop,
                vl_faturado=vl_fat,
                vl_glosa=vl_glosa,
                motivo_glosa=motivo,
            )
        )

    if not itens:
        return None
    return Lote(numero_lote, cod_convenio, competencia, data_envio, tuple(itens))


def gerar_lotes_competencia(base: BaseLegado, competencia: str, data_envio: date) -> list[Lote]:
    """Roda o FATCONV para cada convênio (exceto particular), numerando os lotes em sequência."""
    lotes: list[Lote] = []
    for cod in sorted(c for c in base.convenios if c != "PAR"):
        lote = gerar_lote(base, f"{len(lotes) + 1:06d}", cod, competencia, data_envio)
        if lote is not None:
            lotes.append(lote)
    return lotes
