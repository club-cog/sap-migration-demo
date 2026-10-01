from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from servicos.protheus import arredondar, data_valida, truncar, ultimo_dia, val


def test_round_meio_para_cima() -> None:
    assert arredondar(Decimal("161.4275")) == Decimal("161.43")
    assert arredondar(Decimal("0.125")) == Decimal("0.13")


def test_noround_trunca() -> None:
    assert truncar(Decimal("161.4275")) == Decimal("161.42")
    assert truncar(Decimal("86.6666")) == Decimal("86.66")


def test_lastday() -> None:
    assert ultimo_dia(date(2026, 2, 10)) == date(2026, 2, 28)


def test_datavalida_fim_de_semana_e_feriado() -> None:
    assert data_valida(date(2026, 8, 29)) == date(2026, 8, 31)
    assert data_valida(date(2026, 9, 7), feriados=[date(2026, 9, 7)]) == date(2026, 9, 8)
    assert data_valida(date(2026, 9, 15)) == date(2026, 9, 15)


@pytest.mark.parametrize(("texto", "esperado"), [("3", "3"), (" 2", "2"), ("", "0"), ("X", "0"), ("2.5", "2.5")])
def test_val(texto: str, esperado: str) -> None:
    assert val(texto) == Decimal(esperado)
