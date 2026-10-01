"""Equivalentes Python das funções padrão ADVPL usadas pelas rotinas migradas."""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")
SABADO = 5


def arredondar(valor: Decimal) -> Decimal:
    """`Round(x, 2)`."""
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def truncar(valor: Decimal) -> Decimal:
    """`NoRound(x, 2)`."""
    return valor.quantize(CENTAVOS, rounding=ROUND_DOWN)


def stod(texto: str) -> date:
    """`SToD("AAAAMMDD")`."""
    return datetime.strptime(texto, "%Y%m%d").date()


def dtos(data: date) -> str:
    """`DToS(d)`."""
    return data.strftime("%Y%m%d")


def ultimo_dia(data: date) -> date:
    """`LastDay(d)`."""
    return data.replace(day=calendar.monthrange(data.year, data.month)[1])


def data_valida(data: date, feriados: Iterable[date] = ()) -> date:
    """`DataValida(d, .T.)`: próximo dia útil (fim de semana e feriados da tabela 63 do SX5)."""
    nao_uteis = frozenset(feriados)
    while data.weekday() >= SABADO or data in nao_uteis:
        data += timedelta(days=1)
    return data


def val(texto: str) -> Decimal:
    """`Val(c)`: converte o prefixo numérico do texto; retorna 0 quando não há número."""
    texto = texto.strip()
    fim = 0
    ponto = False
    for indice, caractere in enumerate(texto):
        if caractere.isdigit():
            fim = indice + 1
        elif caractere == "." and not ponto:
            ponto = True
        elif not (indice == 0 and caractere in "+-"):
            break
    numero = texto[:fim]
    if not numero.strip("+-."):
        return Decimal(0)
    return Decimal(numero)
