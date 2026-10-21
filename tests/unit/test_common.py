"""Unit tests for the shared ports in risk_models.common (ports of legacy/models/lib)."""

import datetime as dt
from decimal import Decimal as D

from risk_models.common import daycount, data, rounding, stats


def test_money_and_rate_half_up():
    assert rounding.money(D("2.345")) == D("2.35")
    assert rounding.money(D("-2.345")) == D("-2.35")
    assert rounding.rate(D("0.1234565")) == D("0.123457")


def test_to_unit_half_up():
    assert rounding.to_unit(D("516974.80"), D(10000)) == D(520000)
    assert rounding.to_unit(D("514999.99"), D(10000)) == D(510000)
    assert rounding.to_unit(D("12.345"), D(0)) == D("12.35")


def test_clamp():
    assert rounding.clamp(D(5), D(0), D(3)) == D(3)
    assert rounding.clamp(D(-1), D(0), D(3)) == D(0)


def test_yearfrac_bases():
    a, b = dt.date(2024, 1, 31), dt.date(2024, 7, 31)
    assert daycount.yearfrac(a, b, "A360") == D(182) / 360
    assert daycount.yearfrac(a, b, "A365") == D(182) / 365
    assert daycount.yearfrac(a, b, "30360") == D("0.5")


def test_mat_bucket():
    as_of = dt.date(2024, 1, 31)
    assert daycount.mat_bucket(as_of, None) == "GE1Y"
    assert daycount.mat_bucket(as_of, dt.date(2024, 3, 1)) == "LT6M"
    assert daycount.mat_bucket(as_of, dt.date(2024, 10, 1)) == "6M1Y"
    assert daycount.mat_bucket(as_of, dt.date(2023, 1, 1)) == "LT6M"


def test_stats_quantile_and_tail():
    pnl = [D(x) for x in (5, -10, 3, -2, -7, 1, -1, 0, 2, -4)]
    assert stats.losses_desc(pnl)[:3] == [D(10), D(7), D(4)]
    assert stats.quantile_loss(pnl, D("0.75")) == D(4)   # k = ceil(2.5) = 3
    assert stats.tail_mean(pnl, D("0.75")) == D("8.5")   # k = floor(2.5) = 2


def test_data_typing_and_lookup():
    row = data.rows("positions.csv")[0]
    assert isinstance(row["market_value"], D) and row["maturity_date"] is None
    assert data.lookup("hqla_haircuts.csv", "level", "CASH", "ZZZ") == "L1"
    assert data.lookup("fx_rates.csv", "usd_rate", "XXX") is None
    assert len(data.where("csa_agreements.csv", csa_id="CSA-0207")) == 1
