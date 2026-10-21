"""SA-CCR add-on, PFE multiplier and EAD for unmargined netting sets (IR + FX only).
Port of ``legacy/models/saccr_addon.quill``.

Business rules (Quill line numbers refer to ``legacy/models/saccr_addon.quill``):

| Rule                                                               | Quill      | Python                  |
|--------------------------------------------------------------------|------------|-------------------------|
| Only live trades (end date after as-of)                            | L44        | ``compute``             |
| Direction S = -1, otherwise +1                                     | L45-48     | ``compute``             |
| Start/end in years, A365 (``daycount.yearfrac``), start floored at 0 | L49-50   | ``compute``             |
| Maturity factor sqrt(min(max(M, 10/250), 1))                       | L16, L22-24 | ``maturity_factor``    |
| Supervisory duration (exp(-0.05 S) - exp(-0.05 E)) / 0.05           | L18-20     | ``supervisory_duration`` |
| IR maturity buckets <1y, 1-5y, >5y                                 | L26-33     | ``ir_bucket``           |
| IR effective notional with 1.4 / 1.4 / 0.6 bucket correlations, SF 0.5% | L13, L64-70 | ``compute``       |
| FX add-on = 4% x abs(net effective notional) per currency pair     | L14, L61, L71-74 | ``compute``       |
| Multiplier min(1, 5% + 95% exp(V-C / (2 x 95% x AddOn)))           | L15, L76-80 | ``compute``            |
| RC = max(V - C, 0); EAD = 1.4 x (RC + PFE)                         | L12, L81-83 | ``compute``            |
| Money outputs 2 dp, multiplier 6 dp                                | L83        | ``compute``             |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.daycount import yearfrac
from risk_models.common.rounding import money, rate

ALPHA = Decimal("1.4")
SF_IR = Decimal("0.005")
SF_FX = Decimal("0.04")
FLOOR_M = Decimal("0.05")
MIN_MAT_YEARS = Decimal(10) / Decimal(250)
ZERO, ONE = Decimal(0), Decimal(1)


@dataclass(frozen=True)
class SaccrResult:
    n_trades: int
    addon_ir: Decimal
    addon_fx: Decimal
    addon: Decimal
    multiplier: Decimal
    rc: Decimal
    pfe: Decimal
    ead: Decimal


def supervisory_duration(s: Decimal, e: Decimal) -> Decimal:
    k = Decimal("-0.05")
    return ((k * s).exp() - (k * e).exp()) / Decimal("0.05")


def maturity_factor(m: Decimal) -> Decimal:
    return min(max(m, MIN_MAT_YEARS), ONE).sqrt()


def ir_bucket(e: Decimal) -> int:
    if e < 1:
        return 0
    if e <= 5:
        return 1
    return 2


def compute(as_of: dt.date, netting_set: str) -> SaccrResult:
    collateral = data.lookup("netting_sets.csv", "collateral_held", netting_set)
    ir: dict[str, list[Decimal]] = {}
    fx: dict[str, Decimal] = {}
    mtm = ZERO
    n = 0
    for t in data.where("trades_saccr.csv", netting_set=netting_set):
        if t["end_date"] <= as_of:
            continue
        delta = -ONE if t["direction"] == "S" else ONE
        s = max(yearfrac(as_of, t["start_date"], "A365"), ZERO)
        e = yearfrac(as_of, t["end_date"], "A365")
        mf = maturity_factor(e)
        mtm = mtm + t["mtm"]
        n += 1
        if t["asset_class"] == "IR":
            d = ir.setdefault(t["hedging_set"], [ZERO, ZERO, ZERO])
            k = ir_bucket(e)
            d[k] = d[k] + delta * t["notional"] * supervisory_duration(s, e) * mf
        else:
            fx[t["hedging_set"]] = fx.get(t["hedging_set"], ZERO) + delta * t["notional"] * mf
    addon_ir = ZERO
    for d1, d2, d3 in ir.values():
        en2 = (d1 * d1 + d2 * d2 + d3 * d3 + Decimal("1.4") * d1 * d2
               + Decimal("1.4") * d2 * d3 + Decimal("0.6") * d1 * d3)
        addon_ir = addon_ir + SF_IR * max(en2, ZERO).sqrt()
    addon_fx = ZERO
    for net in fx.values():
        addon_fx = addon_fx + SF_FX * abs(net)
    addon = addon_ir + addon_fx
    v_minus_c = mtm - collateral
    mult = ONE
    if addon > 0:
        mult = min(ONE, FLOOR_M + (1 - FLOOR_M) * (v_minus_c / (2 * (1 - FLOOR_M) * addon)).exp())
    rc = max(v_minus_c, ZERO)
    pfe = mult * addon
    return SaccrResult(n, money(addon_ir), money(addon_fx), money(addon), rate(mult), money(rc),
                       money(pfe), money(ALPHA * (rc + pfe)))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["netting_set"]))
