"""REPMED: repasse médico da competência (SZ6 + SZ1 particulares -> SE2/SZ7). Rodar depois do FATCONV."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from servicos.modelos import ZERO, BaseProtheus, ItemLote, ItemRepasse, ResultadoRepasse, TituloPagar
from servicos.protheus import arredondar, data_valida, dtos, stod, truncar, ultimo_dia

logger = logging.getLogger(__name__)

STATUS_REALIZADO = "R"
TIPO_CONVENIO = "C"
CONVENIO_PARTICULAR = "PAR"

# 2016: laboratório próprio, exames de patologia clínica (subgrupo 4.03) não geram repasse.
PREFIXO_LABORATORIO_PROPRIO = "4030"

# 2018: adicional de plantão no pronto atendimento.
PROCEDIMENTO_PLANTAO = "10101039"
ADICIONAL_PLANTAO = Decimal("5")

ALIQUOTA_IRRF = Decimal("1.5")
ALIQUOTA_PIS = Decimal("0.65")
ALIQUOTA_COFINS = Decimal("3")
ALIQUOTA_CSLL = Decimal("1")
ALIQUOTA_ISS = Decimal("5")
# Dispensa de retenção quando o imposto (IRRF) ou a soma (PIS+COFINS+CSLL) é até R$ 10,00.
LIMITE_DISPENSA_RETENCAO = Decimal("10")

DIA_VENCIMENTO = 15
PREFIXO_TITULO = "REP"
PARCELA_UNICA = " "
TIPO_TITULO = "NF"


@dataclass(frozen=True)
class Retencoes:
    irrf: Decimal
    pis: Decimal
    cofins: Decimal
    csll: Decimal
    iss: Decimal


@dataclass
class _Acumulado:
    retem_iss: str
    bruto: Decimal = ZERO
    itens: list[ItemRepasse] = field(default_factory=list)


def calcular_retencoes(bruto: Decimal, retem_iss: str) -> Retencoes:
    irrf = arredondar(bruto * ALIQUOTA_IRRF / 100)
    if irrf <= LIMITE_DISPENSA_RETENCAO:
        irrf = ZERO

    pis = arredondar(bruto * ALIQUOTA_PIS / 100)
    cofins = arredondar(bruto * ALIQUOTA_COFINS / 100)
    csll = arredondar(bruto * ALIQUOTA_CSLL / 100)
    if pis + cofins + csll <= LIMITE_DISPENSA_RETENCAO:
        pis = cofins = csll = ZERO

    # 2013: NoRound, a prefeitura trunca o ISS.
    iss = truncar(bruto * ALIQUOTA_ISS / 100) if retem_iss == "S" else ZERO
    return Retencoes(irrf=irrf, pis=pis, cofins=cofins, csll=csll, iss=iss)


def datas_titulo(competencia: str, feriados: Iterable[date] = ()) -> tuple[date, date]:
    """Emissão no último dia da competência; vencimento dia 15 do mês seguinte (próximo dia útil)."""
    emissao = ultimo_dia(stod(competencia + "01"))
    mes_seguinte = date.fromordinal(emissao.toordinal() + 1)
    vencimento = data_valida(mes_seguinte.replace(day=DIA_VENCIMENTO), feriados)
    return emissao, vencimento


def calcular_repasse(
    base: BaseProtheus,
    competencia: str,
    itens_lote: Iterable[ItemLote],
    feriados: Iterable[date] = (),
) -> ResultadoRepasse:
    emissao, vencimento = datas_titulo(competencia, feriados)

    # Índice 2 do SZ6 (Z6_NUMATE): o DbSeek posiciona no primeiro item gravado.
    lote_por_atendimento: dict[str, ItemLote] = {}
    for item in itens_lote:
        lote_por_atendimento.setdefault(item.numate, item)

    medicos: dict[str, _Acumulado] = {}
    # Índice 2 do SZ1: DTOS(Z1_DATA) + Z1_NUMATE
    for atendimento in sorted(base.atendimentos, key=lambda a: (a.data, a.numate)):
        if dtos(atendimento.data)[:6] != competencia or atendimento.status != STATUS_REALIZADO:
            continue
        if atendimento.procedimento[:4] == PREFIXO_LABORATORIO_PROPRIO:
            continue

        base_calculo = ZERO
        if atendimento.tipo == TIPO_CONVENIO:
            item = lote_por_atendimento.get(atendimento.numate)
            if item is not None and not item.motivo_glosa:
                # Coparticipação entra na base.
                base_calculo = item.valor_tabela - item.valor_desconto
        else:
            # Particular: repasse sobre o valor de tabela, não sobre o recebido (PIX tem desconto).
            preco = base.precos.get((CONVENIO_PARTICULAR, atendimento.procedimento))
            if preco is not None:
                base_calculo = preco.valor

        if base_calculo <= 0:
            continue
        regra = base.regras_repasse.get(atendimento.medico)
        if regra is None:
            continue

        percentual = regra.percentual
        if atendimento.procedimento == PROCEDIMENTO_PLANTAO:
            percentual += ADICIONAL_PLANTAO
        valor = arredondar(base_calculo * percentual / 100)

        acumulado = medicos.setdefault(atendimento.medico, _Acumulado(retem_iss=regra.retem_iss))
        acumulado.bruto += valor
        acumulado.itens.append(
            ItemRepasse(
                competencia=competencia,
                medico=atendimento.medico,
                numate=atendimento.numate,
                procedimento=atendimento.procedimento,
                base=base_calculo,
                percentual=percentual,
                valor=valor,
            )
        )

    titulos: list[TituloPagar] = []
    itens: list[ItemRepasse] = []
    for medico in sorted(medicos):
        acumulado = medicos[medico]
        retencoes = calcular_retencoes(acumulado.bruto, acumulado.retem_iss)
        liquido = acumulado.bruto - retencoes.irrf - retencoes.pis - retencoes.cofins - retencoes.csll - retencoes.iss
        titulos.append(
            TituloPagar(
                prefixo=PREFIXO_TITULO,
                numero=competencia,
                parcela=PARCELA_UNICA,
                tipo=TIPO_TITULO,
                fornecedor=medico,
                emissao=emissao,
                vencimento=vencimento,
                valor_bruto=acumulado.bruto,
                irrf=retencoes.irrf,
                pis=retencoes.pis,
                cofins=retencoes.cofins,
                csll=retencoes.csll,
                iss=retencoes.iss,
                valor=liquido,
            )
        )
        itens.extend(acumulado.itens)

    logger.info("REPMED: competencia %s, %d titulos a pagar", competencia, len(titulos))
    return ResultadoRepasse(titulos=titulos, itens=itens)
