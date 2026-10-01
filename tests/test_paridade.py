"""Conciliação: as saídas do serviço Python devem bater 1:1 com as saídas extraídas do Protheus."""

import csv
from datetime import date
from pathlib import Path

import pytest

from servicos.exportar import SAIDAS, processar
from servicos.repositorio import BaseLegado

REFERENCIA = Path(__file__).resolve().parent.parent / "legacy" / "saidas_referencia"


@pytest.fixture(scope="module")
def saidas() -> dict[str, list[list[str]]]:
    return processar(BaseLegado.carregar(), "202608", date(2026, 9, 5))


@pytest.mark.parametrize("arquivo", sorted(SAIDAS))
def test_saida_igual_ao_legado(saidas: dict[str, list[list[str]]], arquivo: str) -> None:
    with open(REFERENCIA / arquivo, newline="", encoding="utf-8") as f:
        esperado = list(csv.reader(f, delimiter=";"))[1:]
    assert saidas[arquivo] == esperado
