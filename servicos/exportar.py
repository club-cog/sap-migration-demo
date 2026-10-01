"""Gera as saídas no layout das tabelas do Protheus (SZ5, SZ6, SZ7, SE1, SE2, SZ8) para conciliação."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from servicos import faturamento_convenio, repasse_medico, titulos_particular
from servicos.repositorio import BaseLegado
from servicos.util import dtos

SAIDAS = {
    "SZ5_lotes.csv": [
        "Z5_LOTE",
        "Z5_CONVEN",
        "Z5_COMPET",
        "Z5_DTENVIO",
        "Z5_QTDGUIA",
        "Z5_VLBRUTO",
        "Z5_VLDESC",
        "Z5_VLCOPAR",
        "Z5_VLFAT",
        "Z5_VLGLOSA",
    ],
    "SZ6_itens_lote.csv": [
        "Z6_LOTE",
        "Z6_NUMATE",
        "Z6_GUIA",
        "Z6_PROCED",
        "Z6_VLTAB",
        "Z6_VLDESC",
        "Z6_VLCOPAR",
        "Z6_VLFAT",
        "Z6_VLGLOSA",
        "Z6_MOTGLO",
    ],
    "SZ7_itens_repasse.csv": ["Z7_COMPET", "Z7_MEDICO", "Z7_NUMATE", "Z7_PROCED", "Z7_BASE", "Z7_PERC", "Z7_VALOR"],
    "SE2_titulos_pagar.csv": [
        "E2_PREFIXO",
        "E2_NUM",
        "E2_FORNECE",
        "E2_EMISSAO",
        "E2_VENCTO",
        "E2_VLBRUTO",
        "E2_IRRF",
        "E2_PIS",
        "E2_COFINS",
        "E2_CSLL",
        "E2_ISS",
        "E2_VALOR",
    ],
    "SE1_titulos_receber.csv": [
        "E1_PREFIXO",
        "E1_NUM",
        "E1_PARCELA",
        "E1_TIPO",
        "E1_CLIENTE",
        "E1_EMISSAO",
        "E1_VENCTO",
        "E1_VALOR",
    ],
    "SZ8_rejeicoes.csv": ["Z8_NUMATE", "Z8_MOTIVO"],
}


def _v(valor: Decimal) -> str:
    return f"{valor:.2f}"


def processar(base: BaseLegado, competencia: str, data_envio: date) -> dict[str, list[list[str]]]:
    lotes = faturamento_convenio.gerar_lotes_competencia(base, competencia, data_envio)
    itens_rep = repasse_medico.calcular_itens(base, competencia, lotes)
    tit_pagar = repasse_medico.gerar_titulos(base, competencia, itens_rep)
    tit_receber, rejeicoes = titulos_particular.processar_particulares(base)

    return {
        "SZ5_lotes.csv": [
            [
                lt.lote,
                lt.convenio,
                lt.competencia,
                dtos(lt.data_envio),
                str(lt.qtd_guias),
                *(_v(lt.total(c)) for c in ("vl_tabela", "vl_desconto", "vl_copart", "vl_faturado", "vl_glosa")),
            ]
            for lt in lotes
        ],
        "SZ6_itens_lote.csv": [
            [
                i.lote,
                i.atendimento,
                i.guia,
                i.procedimento,
                _v(i.vl_tabela),
                _v(i.vl_desconto),
                _v(i.vl_copart),
                _v(i.vl_faturado),
                _v(i.vl_glosa),
                i.motivo_glosa,
            ]
            for lt in lotes
            for i in lt.itens
        ],
        "SZ7_itens_repasse.csv": [
            [i.competencia, i.medico, i.atendimento, i.procedimento, _v(i.base), _v(i.perc), _v(i.valor)]
            for i in sorted(itens_rep, key=lambda i: (i.medico, i.atendimento))
        ],
        "SE2_titulos_pagar.csv": [
            [
                t.prefixo,
                t.numero,
                t.fornecedor,
                dtos(t.emissao),
                dtos(t.vencimento),
                _v(t.vl_bruto),
                _v(t.irrf),
                _v(t.pis),
                _v(t.cofins),
                _v(t.csll),
                _v(t.iss),
                _v(t.vl_liquido),
            ]
            for t in tit_pagar
        ],
        "SE1_titulos_receber.csv": [
            [t.prefixo, t.numero, t.parcela, t.tipo, t.cliente, dtos(t.emissao), dtos(t.vencimento), _v(t.valor)]
            for t in tit_receber
        ],
        "SZ8_rejeicoes.csv": [[r.atendimento, r.motivo] for r in rejeicoes],
    }


def gravar(saidas: dict[str, list[list[str]]], destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for nome, linhas in saidas.items():
        with open(destino / nome, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(SAIDAS[nome])
            w.writerows(linhas)
