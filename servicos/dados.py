"""Leitura da extração do Protheus (`legacy/dados`) e gravação das saídas no layout das tabelas."""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Generic, TypeVar

from servicos.modelos import (
    Atendimento,
    BaseProtheus,
    Convenio,
    ItemLote,
    ItemRepasse,
    LoteFaturamento,
    Preco,
    RegraRepasse,
    Rejeicao,
    TituloPagar,
    TituloReceber,
)
from servicos.protheus import dtos, stod

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "legacy" / "dados"
DIR_REFERENCIA = RAIZ / "legacy" / "saidas_referencia"
SEPARADOR = ";"

Linha = dict[str, str]
T = TypeVar("T")


def ler_csv(caminho: Path) -> list[Linha]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=SEPARADOR))


def carregar_base(diretorio: Path = DIR_DADOS) -> BaseProtheus:
    """Carrega SZ1..SZ4. O SA1 (nome/CPF) não é lido: nenhuma regra migrada depende dele."""
    atendimentos = tuple(
        Atendimento(
            numate=linha["Z1_NUMATE"],
            data=stod(linha["Z1_DATA"]),
            paciente=linha["Z1_PACIENT"],
            tipo=linha["Z1_TIPO"],
            convenio=linha["Z1_CONVEN"],
            procedimento=linha["Z1_PROCED"],
            medico=linha["Z1_MEDICO"],
            guia=linha["Z1_GUIA"],
            autorizacao=linha["Z1_AUTORIZ"],
            status=linha["Z1_STATUS"],
            forma_pagamento=linha["Z1_FORMPG"],
            parcelas=linha["Z1_PARCELA"],
            fatura=linha.get("Z1_FATURA") or "",
        )
        for linha in ler_csv(diretorio / "SZ1_atendimentos.csv")
    )
    convenios = {
        linha["Z2_COD"]: Convenio(
            codigo=linha["Z2_COD"],
            prazo_dias=int(linha["Z2_PRAZO"]),
            coparticipacao=Decimal(linha["Z2_COPART"]),
            exige_autorizacao=linha["Z2_EXIGAUT"],
        )
        for linha in ler_csv(diretorio / "SZ2_convenios.csv")
    }
    precos = {
        (linha["Z3_CONVEN"], linha["Z3_PROCED"]): Preco(
            convenio=linha["Z3_CONVEN"],
            procedimento=linha["Z3_PROCED"],
            valor=Decimal(linha["Z3_VALOR"]),
            coberto=linha["Z3_COBERTO"],
        )
        for linha in ler_csv(diretorio / "SZ3_tabela_precos.csv")
    }
    regras = {
        linha["Z4_MEDICO"]: RegraRepasse(
            medico=linha["Z4_MEDICO"],
            percentual=Decimal(linha["Z4_PERC"]),
            retem_iss=linha["Z4_MUNISS"],
        )
        for linha in ler_csv(diretorio / "SZ4_regras_repasse.csv")
    }
    return BaseProtheus(atendimentos=atendimentos, convenios=convenios, precos=precos, regras_repasse=regras)


def _valor(numero: Decimal) -> str:
    return f"{numero:.2f}"


@dataclass(frozen=True)
class Layout(Generic[T]):
    """Layout de gravação de uma tabela: arquivo, colunas, chave (índice 1 sem filial) e conversão."""

    tabela: str
    arquivo: str
    colunas: tuple[str, ...]
    chave: tuple[str, ...]
    converter: Callable[[T], Linha]

    def linhas(self, registros: Iterable[T]) -> list[Linha]:
        linhas = [self.converter(registro) for registro in registros]
        return sorted(linhas, key=lambda linha: tuple(linha[campo] for campo in self.chave))


LAYOUT_SZ5: Layout[LoteFaturamento] = Layout(
    tabela="SZ5",
    arquivo="SZ5_lotes.csv",
    colunas=(
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
    ),
    chave=("Z5_LOTE",),
    converter=lambda r: {
        "Z5_LOTE": r.lote,
        "Z5_CONVEN": r.convenio,
        "Z5_COMPET": r.competencia,
        "Z5_DTENVIO": dtos(r.data_envio),
        "Z5_QTDGUIA": str(r.qtd_guias),
        "Z5_VLBRUTO": _valor(r.valor_bruto),
        "Z5_VLDESC": _valor(r.valor_desconto),
        "Z5_VLCOPAR": _valor(r.valor_coparticipacao),
        "Z5_VLFAT": _valor(r.valor_faturado),
        "Z5_VLGLOSA": _valor(r.valor_glosa),
    },
)

LAYOUT_SZ6: Layout[ItemLote] = Layout(
    tabela="SZ6",
    arquivo="SZ6_itens_lote.csv",
    colunas=(
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
    ),
    chave=("Z6_LOTE", "Z6_NUMATE"),
    converter=lambda r: {
        "Z6_LOTE": r.lote,
        "Z6_NUMATE": r.numate,
        "Z6_GUIA": r.guia,
        "Z6_PROCED": r.procedimento,
        "Z6_VLTAB": _valor(r.valor_tabela),
        "Z6_VLDESC": _valor(r.valor_desconto),
        "Z6_VLCOPAR": _valor(r.valor_coparticipacao),
        "Z6_VLFAT": _valor(r.valor_faturado),
        "Z6_VLGLOSA": _valor(r.valor_glosa),
        "Z6_MOTGLO": r.motivo_glosa,
    },
)

LAYOUT_SZ7: Layout[ItemRepasse] = Layout(
    tabela="SZ7",
    arquivo="SZ7_itens_repasse.csv",
    colunas=("Z7_COMPET", "Z7_MEDICO", "Z7_NUMATE", "Z7_PROCED", "Z7_BASE", "Z7_PERC", "Z7_VALOR"),
    chave=("Z7_COMPET", "Z7_MEDICO", "Z7_NUMATE"),
    converter=lambda r: {
        "Z7_COMPET": r.competencia,
        "Z7_MEDICO": r.medico,
        "Z7_NUMATE": r.numate,
        "Z7_PROCED": r.procedimento,
        "Z7_BASE": _valor(r.base),
        "Z7_PERC": _valor(r.percentual),
        "Z7_VALOR": _valor(r.valor),
    },
)

LAYOUT_SZ8: Layout[Rejeicao] = Layout(
    tabela="SZ8",
    arquivo="SZ8_rejeicoes.csv",
    colunas=("Z8_NUMATE", "Z8_MOTIVO"),
    chave=("Z8_NUMATE",),
    converter=lambda r: {"Z8_NUMATE": r.numate, "Z8_MOTIVO": r.motivo},
)

LAYOUT_SE1: Layout[TituloReceber] = Layout(
    tabela="SE1",
    arquivo="SE1_titulos_receber.csv",
    colunas=(
        "E1_PREFIXO",
        "E1_NUM",
        "E1_PARCELA",
        "E1_TIPO",
        "E1_CLIENTE",
        "E1_EMISSAO",
        "E1_VENCTO",
        "E1_VALOR",
    ),
    chave=("E1_PREFIXO", "E1_NUM", "E1_PARCELA", "E1_TIPO"),
    converter=lambda r: {
        "E1_PREFIXO": r.prefixo,
        "E1_NUM": r.numero,
        "E1_PARCELA": r.parcela,
        "E1_TIPO": r.tipo,
        "E1_CLIENTE": r.cliente,
        "E1_EMISSAO": dtos(r.emissao),
        "E1_VENCTO": dtos(r.vencimento),
        "E1_VALOR": _valor(r.valor),
    },
)

LAYOUT_SE2: Layout[TituloPagar] = Layout(
    tabela="SE2",
    arquivo="SE2_titulos_pagar.csv",
    colunas=(
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
    ),
    chave=("E2_PREFIXO", "E2_NUM", "E2_FORNECE"),
    converter=lambda r: {
        "E2_PREFIXO": r.prefixo,
        "E2_NUM": r.numero,
        "E2_FORNECE": r.fornecedor,
        "E2_EMISSAO": dtos(r.emissao),
        "E2_VENCTO": dtos(r.vencimento),
        "E2_VLBRUTO": _valor(r.valor_bruto),
        "E2_IRRF": _valor(r.irrf),
        "E2_PIS": _valor(r.pis),
        "E2_COFINS": _valor(r.cofins),
        "E2_CSLL": _valor(r.csll),
        "E2_ISS": _valor(r.iss),
        "E2_VALOR": _valor(r.valor),
    },
)


def gravar_csv(caminho: Path, colunas: Sequence[str], linhas: Iterable[Linha]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(colunas), delimiter=SEPARADOR, lineterminator="\r\n")
        escritor.writeheader()
        escritor.writerows(linhas)
