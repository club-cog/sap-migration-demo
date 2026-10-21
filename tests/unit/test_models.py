"""Unit tests for the migrated models: one or two business rules each, independent of parity."""

import datetime as dt
from decimal import Decimal as D

import pytest

from risk_models import (collateral_margin_call as mc, cva_simple, expected_shortfall, frtb_ir_delta,
                         hist_var, hqla_haircut, lcr_outflows, nsfr, saccr_addon, stress_shock)

AS_OF = dt.date(2024, 3, 28)


# hqla_haircut
def test_foreign_non_aaa_sovereign_is_l2a_at_15pct():
    p = {"asset_class": "SOV", "rating": "AA", "ccy": "EUR"}
    assert hqla_haircut.classify(p, "EXB-NY") == ("L2A", D("0.15"))
    assert hqla_haircut.classify({**p, "ccy": "USD"}, "EXB-NY")[0] == "L1"


def test_encumbered_and_matured_positions_are_ineligible():
    base = {"encumbered": "N", "maturity_date": None}
    assert hqla_haircut.is_eligible(base, AS_OF)
    assert not hqla_haircut.is_eligible({**base, "encumbered": "Y"}, AS_OF)
    assert not hqla_haircut.is_eligible({**base, "maturity_date": AS_OF}, AS_OF)


def test_hqla_addon_only_reduces_stock():
    plain = hqla_haircut.hqla_stock(AS_OF, "EXB-LDN")
    stressed = hqla_haircut.hqla_stock(AS_OF, "EXB-LDN", lcr_outflows.STRESS_HAIRCUT)
    assert stressed.hqla <= plain.hqla and stressed.l1 == plain.l1
    assert stressed.l2a < plain.l2a


# lcr_outflows
def test_lcr_window_is_30_days_and_open_maturity_counts():
    assert lcr_outflows.in_window(None, AS_OF)
    assert lcr_outflows.in_window(AS_OF + dt.timedelta(days=30), AS_OF)
    assert not lcr_outflows.in_window(AS_OF + dt.timedelta(days=31), AS_OF)
    assert not lcr_outflows.in_window(AS_OF, AS_OF)


def test_lcr_status_thresholds():
    assert [lcr_outflows.status_for(D(x)) for x in ("0.99", "1.05", "1.10")] == [
        "RED", "AMBER", "GREEN"]


def test_lcr_stress_lowers_ratio_and_inflows_are_capped():
    base = lcr_outflows.compute(AS_OF, "EXB-SGP", False)
    stressed = lcr_outflows.compute(AS_OF, "EXB-SGP", True)
    assert stressed.lcr < base.lcr
    assert base.capped_inflows <= D("0.75") * base.gross_outflows + D("0.01")


# nsfr
def test_nsfr_missing_factor_is_an_error():
    with pytest.raises(KeyError):
        nsfr.factor("ASF", "NOPE", "GE1Y")


def test_nsfr_status_thresholds():
    assert [nsfr.status_for(D(x)) for x in ("0.9", "1.01", "1.05")] == ["RED", "AMBER", "GREEN"]


# frtb_ir_delta
def test_rho_is_one_on_diagonal_and_floored():
    assert frtb_ir_delta.rho(D(5), D(5)) == 1
    assert frtb_ir_delta.rho(D("0.25"), D(30)) == D("0.40")


def test_scenario_correlations():
    assert frtb_ir_delta.scenario_corr(D("0.9"), "HIGH") == 1
    assert frtb_ir_delta.scenario_corr(D("0.5"), "LOW") == D("0.375")
    assert frtb_ir_delta.scenario_corr(D("0.5"), "MED") == D("0.5")


def test_frtb_charge_is_max_of_scenarios():
    r = frtb_ir_delta.compute(dt.date(2024, 1, 31), "RATES-G10")
    assert r.delta_charge == max(r.delta_low, r.delta_med, r.delta_high)


# hist_var / expected_shortfall
def test_var_insufficient_history():
    r = hist_var.compute("MACRO-1", dt.date(2023, 10, 2), D("0.99"))
    assert r.status == "INSUFFICIENT" and r.var_1d is None


def test_var_10d_is_sqrt10_scaled():
    r = hist_var.compute("FX-FLOW", dt.date(2024, 6, 28), D("0.99"))
    assert abs(r.var_10d - r.var_1d * D(10).sqrt()) < D("0.01")


def test_es_reported_is_max_of_current_and_weighted_stress():
    r = expected_shortfall.compute("EQ-DERIV", dt.date(2024, 6, 28))
    want = max(r.es_1d, expected_shortfall.STRESS_WEIGHT * r.es_stress_1d)
    assert abs(r.es_reported_1d - want) <= D("0.01")


# saccr_addon
def test_saccr_maturity_factor_floor_and_cap():
    assert saccr_addon.maturity_factor(D(0)) == (D(10) / D(250)).sqrt()
    assert saccr_addon.maturity_factor(D(7)) == 1


def test_saccr_ir_buckets():
    assert [saccr_addon.ir_bucket(D(x)) for x in ("0.5", "5", "5.1")] == [0, 1, 2]


def test_saccr_ead_is_alpha_times_rc_plus_pfe():
    r = saccr_addon.compute(dt.date(2024, 2, 29), "NS-ALPHA")
    assert abs(r.ead - saccr_addon.ALPHA * (r.rc + r.pfe)) <= D("0.01")


# cva_simple
def test_cva_proxy_spread_gets_em_uplift_and_floor():
    cp = {"cds_bp": None, "rating": "AAA", "sector": "CORP", "region": "EM"}
    bp, src = cva_simple.credit_spread(cp)
    assert src == "PROXY" and bp == D(25) * D("1.10")
    assert cva_simple.credit_spread({**cp, "cds_bp": D(3)}) == (D(10), "CDS")


# stress_shock
def test_rel_shock_floored_at_minus_100pct():
    p = {"asset_class": "EQ", "sub": "DM", "mv": D(100), "pv01": None}
    assert stress_shock.position_pnl(p, "EQ_CRASH") == D(-35)


def test_hy_spread_shock_multiplier():
    p = {"asset_class": "CR", "sub": "HY", "mv": D(0), "pv01": D(1000)}
    assert stress_shock.position_pnl(p, "CREDIT_WIDEN") == D(-1000) * D(300) * D("1.5")


# collateral_margin_call
@pytest.mark.parametrize("as_of,fix", [("2024-06-15", "2024-06-14"), ("2024-06-16", "2024-06-14"),
                                       ("2024-06-14", "2024-06-14")])
def test_weekend_uses_prior_friday_fixing(as_of, fix):
    assert mc.fixing_date(dt.date.fromisoformat(as_of)) == dt.date.fromisoformat(fix)


def test_call_amount_rounds_half_up_on_weekends_too():
    r = mc.compute(dt.date(2024, 3, 30), "CSA-0101")
    assert r.raw_diff == D("516974.80") and r.call_amount == D(520000)


def test_mta_and_return_cap():
    pos = mc.MarginPosition(D(0), D(0), D(100), D(-400))
    assert mc.call_for(pos, D(500)) == ("NONE", D(0))
    assert mc.call_for(pos, D(50)) == ("RETURN", D(100))
