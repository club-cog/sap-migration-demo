"""Builtins: rounding, dates, tables."""

import datetime as dt
from decimal import Decimal

import pytest

from legacy.quill_runtime import QuillError


def ev(q, expr):
    return q(f"defn main()\n  return {expr}\nenddefn\n")


@pytest.mark.parametrize("expr,want", [
    ("ROUND(2.345, 2)", "2.35"),
    ("ROUND(-2.345, 2)", "-2.35"),
    ("ROUND(2.5, 0)", "3"),
    ("TRUNC(2.999, 2)", "2.99"),
    ("TRUNC(-2.999, 0)", "-2"),
    ("FLOOR(-1.5)", "-2"),
    ("CEIL(1.01)", "2"),
    ("MIN(3, 1, 2)", "1"),
    ("MAX([3, 1, 2])", "3"),
    ("SUM([1, 2, 3.5])", "6.5"),
    ("ABS(-4)", "4"),
    ("SQRT(16)", "4"),
    ("LEN([1, 2, 3])", "3"),
    ("NUM(\"0.975\")", "0.975"),
])
def test_numeric_builtins(q, expr, want):
    assert ev(q, expr) == Decimal(want)


def test_sort_desc(q):
    assert ev(q, 'SORT([3, 1, 2], "DESC")') == [Decimal(3), Decimal(2), Decimal(1)]


def test_append_mutates(q):
    src = "defn main()\n  let xs = []\n  APPEND(xs, 1)\n  APPEND(xs, 2)\n  return xs\nenddefn\n"
    assert q(src) == [Decimal(1), Decimal(2)]


@pytest.mark.parametrize("d,conv,want", [
    ("2024-06-15", "P", "2024-06-14"),   # Sat -> Fri
    ("2024-06-16", "F", "2024-06-17"),   # Sun -> Mon
    ("2024-06-14", "F", "2024-06-14"),   # business day unchanged
    ("2024-08-31", "MF", "2024-08-30"),  # Sat at month end: following would leave month
    ("2024-06-01", "MP", "2024-06-03"),  # Sat at month start: preceding would leave month
])
def test_date_roll(q, d, conv, want):
    assert ev(q, f'DATE.ROLL(DATE.PARSE("{d}"), "{conv}")') == dt.date.fromisoformat(want)


def test_date_roll_bad_convention(q):
    with pytest.raises(QuillError):
        ev(q, 'DATE.ROLL(DATE.PARSE("2024-06-15"), "X")')


def test_busdays_excludes_start_includes_end(q):
    assert ev(q, 'BUSDAYS(DATE.PARSE("2024-06-14"), DATE.PARSE("2024-06-21"))') == Decimal(5)
    assert ev(q, 'BUSDAYS(DATE.PARSE("2024-06-21"), DATE.PARSE("2024-06-14"))') == Decimal(-5)


def test_date_add_months_clamps_to_month_end(q):
    assert ev(q, 'DATE.ADD(DATE.PARSE("2024-01-31"), 1, "M")') == dt.date(2024, 2, 29)


def test_date_parts_and_dow(q):
    assert ev(q, 'DATE.DOW(DATE.PARSE("2024-06-15"))') == Decimal(6)
    assert ev(q, 'DATE.DIFF(DATE.PARSE("2024-01-01"), DATE.PARSE("2024-03-01"))') == Decimal(60)
    assert ev(q, 'DATE.EOM(DATE.PARSE("2023-02-10"))') == dt.date(2023, 2, 28)


def test_table_lookup_wildcard_first_match(q):
    assert ev(q, 'TABLE.LOOKUP(TABLE.LOAD("hqla_haircuts.csv"), "level", "CASH", "ZZZ")') == "L1"


def test_table_lookup_miss_is_nil(q):
    assert ev(q, 'TABLE.LOOKUP(TABLE.LOAD("fx_rates.csv"), "usd_rate", "XXX")') is None


def test_table_load_types_cells(q):
    row = ev(q, 'TABLE.ROWS(TABLE.LOAD("positions.csv"))[1]')
    assert isinstance(row["market_value"], Decimal)
    assert row["maturity_date"] is None
    assert row["ccy"] == "USD"


def test_table_where_filters(q):
    rows = ev(q, 'TABLE.WHERE(TABLE.LOAD("csa_agreements.csv"), "csa_id", "CSA-0207")')
    assert len(rows) == 1 and rows[0]["rounding_unit"] == Decimal(100000)


def test_missing_table_is_error(q):
    with pytest.raises(QuillError):
        ev(q, 'TABLE.LOAD("nope.csv")')
