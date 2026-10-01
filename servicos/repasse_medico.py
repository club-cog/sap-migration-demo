"""Migração de REPMED.prw: repasse médico (PJ) e títulos a pagar com retenções."""

from datetime import timedelta
from decimal import Decimal

from servicos.modelos import ItemLote, ItemRepasse, Lote, TituloPagar
from servicos.repositorio import BaseLegado
from servicos.util import arredonda, dtos, proximo_dia_util, trunca, ultimo_dia

CONSULTA_PRONTO_ATENDIMENTO = "10101039"
ADICIONAL_PLANTAO = Decimal("5")  # 2018
SUBGRUPO_LABORATORIO = "4030"  # 2016: patologia clínica do laboratório próprio, sem repasse
DISPENSA_RETENCAO = Decimal("10")


def calcular_itens(base: BaseLegado, competencia: str, lotes: list[Lote]) -> list[ItemRepasse]:
    itens_lote: dict[str, ItemLote] = {i.atendimento: i for lote in lotes for i in lote.itens}
    itens: list[ItemRepasse] = []
    realizados = sorted(
        (a for a in base.atendimentos if dtos(a.data)[:6] == competencia and a.status == "R"),
        key=lambda a: (a.data, a.numero),
    )
    for atendimento in realizados:
        if atendimento.procedimento.startswith(SUBGRUPO_LABORATORIO):
            continue

        vl_base = Decimal("0")
        if atendimento.tipo == "C":
            item = itens_lote.get(atendimento.numero)
            if item is not None and not item.motivo_glosa:
                vl_base = item.vl_tabela - item.vl_desconto
        else:
            preco = base.precos.get(("PAR", atendimento.procedimento))
            if preco is not None:
                vl_base = preco.valor

        regra = base.regras_repasse.get(atendimento.medico)
        if vl_base <= 0 or regra is None:
            continue

        perc = regra.perc
        if atendimento.procedimento == CONSULTA_PRONTO_ATENDIMENTO:
            perc += ADICIONAL_PLANTAO
        itens.append(
            ItemRepasse(
                competencia=competencia,
                medico=atendimento.medico,
                atendimento=atendimento.numero,
                procedimento=atendimento.procedimento,
                base=vl_base,
                perc=perc,
                valor=arredonda(vl_base * perc / 100),
            )
        )
    return itens


def gerar_titulos(base: BaseLegado, competencia: str, itens: list[ItemRepasse]) -> list[TituloPagar]:
    emissao = ultimo_dia(competencia)
    vencimento = proximo_dia_util((emissao + timedelta(days=1)).replace(day=15))

    titulos: list[TituloPagar] = []
    for medico in sorted({i.medico for i in itens}):
        bruto = sum((i.valor for i in itens if i.medico == medico), Decimal("0"))

        irrf = arredonda(bruto * Decimal("1.5") / 100)
        if irrf <= DISPENSA_RETENCAO:
            irrf = Decimal("0")

        pis = arredonda(bruto * Decimal("0.65") / 100)
        cofins = arredonda(bruto * Decimal("3") / 100)
        csll = arredonda(bruto * Decimal("1") / 100)
        if pis + cofins + csll <= DISPENSA_RETENCAO:
            pis = cofins = csll = Decimal("0")

        iss = trunca(bruto * Decimal("5") / 100) if base.regras_repasse[medico].retem_iss else Decimal("0")

        titulos.append(
            TituloPagar(
                prefixo="REP",
                numero=competencia,
                fornecedor=medico,
                emissao=emissao,
                vencimento=vencimento,
                vl_bruto=bruto,
                irrf=irrf,
                pis=pis,
                cofins=cofins,
                csll=csll,
                iss=iss,
                vl_liquido=bruto - irrf - pis - cofins - csll - iss,
            )
        )
    return titulos
