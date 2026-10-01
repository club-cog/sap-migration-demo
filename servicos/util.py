from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


def arredonda(valor: Decimal) -> Decimal:
    """Equivalente ao Round(x, 2) do ADVPL (meio para cima)."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def trunca(valor: Decimal) -> Decimal:
    """Equivalente ao NoRound(x, 2) do ADVPL."""
    return valor.quantize(CENTAVO, rounding=ROUND_DOWN)


def proximo_dia_util(dia: date) -> date:
    """Equivalente ao DataValida(d, .T.): fins de semana vão para segunda-feira."""
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def ultimo_dia(competencia: str) -> date:
    ano, mes = int(competencia[:4]), int(competencia[4:])
    proximo = date(ano + mes // 12, mes % 12 + 1, 1)
    return proximo - timedelta(days=1)


def para_data(texto: str) -> date:
    return datetime.strptime(texto, "%Y%m%d").date()


def dtos(dia: date) -> str:
    return dia.strftime("%Y%m%d")
