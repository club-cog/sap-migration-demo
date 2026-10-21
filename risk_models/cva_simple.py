"""Unilateral CVA on a discrete expected-exposure profile. Port of ``legacy/models/cva_simple.quill``.

Business rules (Quill line numbers refer to ``legacy/models/cva_simple.quill``):

| Rule                                                                  | Quill     | Python          |
|-----------------------------------------------------------------------|-----------|-----------------|
| Recovery from counterparty record, default 40% when blank; LGD = 1 - R | L12, L31-34 | ``compute``   |
| Spread = quoted CDS if present, else rating x sector proxy (``rating_spreads.csv``) | L18-27 | ``credit_spread`` |
| EM uplift x1.10 on proxy spreads only (XVA committee 2014-03)          | L15-16, L23-25 | ``credit_spread`` |
| Spread floor 10 bp                                                    | L14, L20, L26 | ``credit_spread`` |
| Flat 4% continuous discounting                                        | L13, L45  | ``compute``     |
| Marginal PD from hazard s / LGD between profile points, floored at 0  | L46       | ``compute``     |
| Trapezoid on discounted EE, starting from (t=0, first EE, DF=1)       | L38-52    | ``compute``     |
| CVA = LGD x sum, 2 dp; spread 6 dp; LGD and peak EE unrounded         | L53       | ``compute``     |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.rounding import money, rate

DEFAULT_RECOVERY = Decimal("0.40")
DISC_RATE = Decimal("0.04")
SPREAD_FLOOR_BP = Decimal(10)
EM_UPLIFT = Decimal("1.10")
ZERO = Decimal(0)


@dataclass(frozen=True)
class CvaResult:
    spread_bp: Decimal
    spread_src: str
    lgd: Decimal
    peak_ee: Decimal
    cva: Decimal


def credit_spread(cpty: Mapping[str, Any]) -> tuple[Decimal, str]:
    if cpty["cds_bp"] is not None:
        return max(cpty["cds_bp"], SPREAD_FLOOR_BP), "CDS"
    s = data.lookup("rating_spreads.csv", "spread_bp", cpty["rating"], cpty["sector"])
    if cpty["region"] == "EM":
        s = s * EM_UPLIFT
    return max(s, SPREAD_FLOOR_BP), "PROXY"


def compute(as_of: dt.date, cpty_id: str) -> CvaResult:
    cpty = data.where("counterparties.csv", cpty_id=cpty_id)[0]
    recovery = cpty["recovery"] if cpty["recovery"] is not None else DEFAULT_RECOVERY
    lgd = 1 - recovery
    spread_bp, src = credit_spread(cpty)
    s = spread_bp / 10000
    profile = data.where("cva_exposures.csv", as_of=as_of, cpty_id=cpty_id)
    t0, ee0, df0 = ZERO, profile[0]["ee"], Decimal(1)
    cva, peak = ZERO, ZERO
    for p in profile:
        t, ee = p["tenor_years"], p["ee"]
        df = (-DISC_RATE * t).exp()
        pd = max((-s * t0 / lgd).exp() - (-s * t / lgd).exp(), ZERO)
        cva = cva + pd * (ee0 * df0 + ee * df) / 2
        peak = max(peak, ee)
        t0, ee0, df0 = t, ee, df
    return CvaResult(rate(spread_bp), src, lgd, peak, money(lgd * cva))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["cpty_id"]))
