from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from servicos.competencia import SaidasCompetencia, processar_competencia
from servicos.dados import carregar_base
from servicos.modelos import Atendimento, BaseProtheus, Convenio, Preco, RegraRepasse

COMPETENCIA = "202608"
DATA_ENVIO = date(2026, 9, 5)


@pytest.fixture(scope="session")
def base_protheus() -> BaseProtheus:
    return carregar_base()


@pytest.fixture(scope="session")
def saidas(base_protheus: BaseProtheus) -> SaidasCompetencia:
    return processar_competencia(base_protheus, COMPETENCIA, DATA_ENVIO)


ATENDIMENTO_PADRAO = Atendimento(
    numate="X0001",
    data=date(2026, 8, 10),
    paciente="P900",
    tipo="C",
    convenio="900",
    procedimento="10101012",
    medico="M90",
    guia="G9001",
    autorizacao="AUT9001",
    status="R",
    forma_pagamento="",
    parcelas="",
)


def atendimento(**campos: object) -> Atendimento:
    return replace(ATENDIMENTO_PADRAO, **campos)  # type: ignore[arg-type]


def montar_base(
    atendimentos: list[Atendimento],
    precos: list[Preco] | None = None,
    convenios: list[Convenio] | None = None,
    regras: list[RegraRepasse] | None = None,
) -> BaseProtheus:
    convenios = convenios or [Convenio("900", 30, Decimal("0"), "N"), Convenio("PAR", 0, Decimal("0"), "N")]
    precos = precos or [
        Preco("900", "10101012", Decimal("100.00"), "S"),
        Preco("PAR", "10101012", Decimal("100.00"), "S"),
    ]
    regras = regras or [RegraRepasse("M90", Decimal("50"), "N")]
    return BaseProtheus(
        atendimentos=tuple(atendimentos),
        convenios={c.codigo: c for c in convenios},
        precos={(p.convenio, p.procedimento): p for p in precos},
        regras_repasse={r.medico: r for r in regras},
    )
