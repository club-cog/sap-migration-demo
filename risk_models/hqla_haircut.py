"""HQLA stock after haircuts and Level 2 caps. Port of ``legacy/models/hqla_haircut.quill``.

Business rules (Quill line numbers refer to ``legacy/models/hqla_haircut.quill``):

| Rule                                                                 | Quill   | Python            |
|----------------------------------------------------------------------|---------|-------------------|
| Level + haircut from ``hqla_haircuts.csv`` (asset class, rating; ``*`` wildcard, first match) | L28-29 | ``classify``  |
| Foreign-ccy non-AAA sovereign downgraded L1 -> L2A at 15% (LP-07 3.4(b)) | L30-34 | ``classify``      |
| Home currency per entity                                             | L13     | ``HOME_CCY``      |
| Encumbered or matured (maturity <= as-of) positions excluded         | L38-48  | ``is_eligible``   |
| Level "NONE" positions excluded                                      | L57     | ``hqla_stock``    |
| Optional extra haircut by level (used by LCR stress), capped at 100% | L60     | ``hqla_stock``    |
| Convert to USD with ``fx_rates.csv``; missing rate is an error       | L18-24  | ``to_usd``        |
| L2B cap 15% and L2 cap 40%, adjusted-amount method (LP-07 3.6)       | L15-16, L66-68 | ``hqla_stock`` |
| Outputs rounded via ``rounding.money`` (2 dp half-up)                | L69     | ``HqlaStock``     |

Public API used by other ports: ``to_usd``, ``hqla_stock``, ``NO_ADDON`` (``lcr_outflows`` depends
on them, exactly like ``lcr_outflows.quill`` L7 uses ``hqla_haircut.quill``).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.rounding import money

HOME_CCY: dict[str, str] = {"EXB-NY": "USD", "EXB-LDN": "GBP", "EXB-SGP": "SGD"}
LEVELS = ("L1", "L2A", "L2B")
NO_ADDON: Mapping[str, Decimal] = {lvl: Decimal(0) for lvl in LEVELS}
L2B_CAP = Decimal("0.15")
L2_CAP = Decimal("0.40")
FOREIGN_SOV_HAIRCUT = Decimal("0.15")


@dataclass(frozen=True)
class HqlaStock:
    n_eligible: int
    n_excluded: int
    l1: Decimal
    l2a: Decimal
    l2b: Decimal
    adj_15: Decimal
    adj_40: Decimal
    hqla: Decimal


def to_usd(amount: Decimal, ccy: str) -> Decimal:
    usd_rate = data.lookup("fx_rates.csv", "usd_rate", ccy)
    if usd_rate is None:
        raise KeyError(f"no fx rate for {ccy}")
    return amount * usd_rate


def classify(position: Mapping[str, Any], entity: str) -> tuple[str, Decimal]:
    level = data.lookup("hqla_haircuts.csv", "level", position["asset_class"], position["rating"])
    haircut = data.lookup("hqla_haircuts.csv", "haircut", position["asset_class"], position["rating"])
    if (level == "L1" and position["asset_class"] == "SOV"
            and position["ccy"] != HOME_CCY[entity] and position["rating"] != "AAA"):
        return "L2A", FOREIGN_SOV_HAIRCUT
    return level, haircut


def is_eligible(position: Mapping[str, Any], as_of: dt.date) -> bool:
    if position["encumbered"] == "Y":
        return False
    maturity = position["maturity_date"]
    return maturity is None or maturity > as_of


def hqla_stock(as_of: dt.date, entity: str,
               addon: Mapping[str, Decimal] = NO_ADDON) -> HqlaStock:
    by_level = {lvl: Decimal(0) for lvl in LEVELS}
    n_ok = n_excluded = 0
    for p in data.where("positions.csv", entity=entity):
        level, haircut = classify(p, entity)
        if not is_eligible(p, as_of) or level == "NONE":
            n_excluded += 1
            continue
        hc = min(haircut + addon[level], Decimal(1))
        by_level[level] += to_usd(p["market_value"], p["ccy"]) * (1 - hc)
        n_ok += 1
    l1, l2a, l2b = by_level["L1"], by_level["L2A"], by_level["L2B"]
    adj15 = max(l2b - L2B_CAP / (1 - L2B_CAP) * (l1 + l2a), Decimal(0))
    adj40 = max(l2a + l2b - adj15 - L2_CAP / (1 - L2_CAP) * l1, Decimal(0))
    total = l1 + l2a + l2b - adj15 - adj40
    return HqlaStock(n_ok, n_excluded, money(l1), money(l2a), money(l2b),
                     money(adj15), money(adj40), money(total))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(hqla_stock(dt.date.fromisoformat(case["as_of"]), case["entity"]))
