"""Scenario shocks on trading-book positions vs book loss limits.
Port of ``legacy/models/stress_shock.quill``.

Business rules (Quill line numbers refer to ``legacy/models/stress_shock.quill``):

| Rule                                                                   | Quill    | Python          |
|------------------------------------------------------------------------|----------|-----------------|
| Shock from ``stress_scenarios.csv`` by scenario / asset class / sub (``*`` wildcard); no row = not shocked | L18-23 | ``position_pnl`` |
| REL shock: P&L = MV x shock, shock floored at -100%                     | L24-27   | ``position_pnl`` |
| BP shock: P&L = -PV01 x bp                                              | L31      | ``position_pnl`` |
| HY credit spread shocks x1.5 (jump risk, ST-01 annex B)                 | L15-16, L28-30 | ``position_pnl`` |
| Loss = max(-total P&L, 0); limits per book (RMC 2013-Q2)                | L11-12, L52-53 | ``compute``  |
| Utilization 6 dp; BREACH >= 100%, WARN >= 80%, else OK                  | L13, L54-60 | ``compute``   |
| Concentrated if worst position loss > 40% of book loss                  | L14, L61-64 | ``compute``   |
| Worst position = first with the most negative P&L (only if < 0)        | L46-49   | ``compute``     |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.rounding import money, rate

LIMITS: dict[str, Decimal] = {"EQ-CASH": Decimal(60_000_000), "CREDIT-FLOW": Decimal(40_000_000),
                              "EM-MACRO": Decimal(55_000_000)}
WARN_UTIL = Decimal("0.80")
CONC_PCT = Decimal("0.40")
HY_MULT = Decimal("1.5")
ZERO = Decimal(0)


@dataclass(frozen=True)
class StressResult:
    n_pos: int
    n_shocked: int
    pnl: Decimal
    worst_pos: str
    worst_pnl: Decimal
    limit: Decimal
    utilization: Decimal
    status: str
    concentrated: bool


def position_pnl(p: Mapping[str, Any], scenario: str) -> Decimal | None:
    keys = (scenario, p["asset_class"], p["sub"])
    shock_type = data.lookup("stress_scenarios.csv", "shock_type", *keys)
    if shock_type is None:
        return None
    shock = data.lookup("stress_scenarios.csv", "shock", *keys)
    if shock_type == "REL":
        return p["mv"] * max(shock, Decimal(-1))
    if p["asset_class"] == "CR" and p["sub"] == "HY":
        shock = shock * HY_MULT
    return -p["pv01"] * shock


def compute(as_of: dt.date, book: str, scenario: str) -> StressResult:
    total, worst, worst_id = ZERO, ZERO, ""
    n = n_shocked = 0
    for p in data.where("trading_positions.csv", as_of=as_of, book=book):
        n += 1
        x = position_pnl(p, scenario)
        if x is None:
            continue
        n_shocked += 1
        total = total + x
        if x < worst:
            worst, worst_id = x, p["pos_id"]
    loss = max(-total, ZERO)
    limit = LIMITS[book]
    util = rate(loss / limit)
    status = "BREACH" if util >= 1 else "WARN" if util >= WARN_UTIL else "OK"
    concentrated = loss > 0 and -worst > CONC_PCT * loss
    return StressResult(n, n_shocked, money(total), worst_id, money(worst), limit, util, status,
                        concentrated)


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["book"], case["scenario"]))
