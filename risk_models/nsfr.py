"""Net stable funding ratio (ASF / RSF). Port of ``legacy/models/nsfr.quill``.

Business rules (Quill line numbers refer to ``legacy/models/nsfr.quill``):

| Rule                                                                 | Quill     | Python        |
|----------------------------------------------------------------------|-----------|---------------|
| Factor from ``nsfr_factors.csv`` by side / category / maturity bucket; missing is an error | L15-21 | ``factor`` |
| Lines with maturity <= as-of are dropped; nil maturity is open-ended | L29-32    | ``compute``   |
| Maturity buckets LT6M / 6M1Y / GE1Y via ``daycount.mat_bucket`` (A365) | L34     | ``compute``   |
| Weighted amount = amount x factor, summed per side                   | L35-40    | ``compute``   |
| ASF and RSF rounded to 2 dp, ratio to 6 dp                           | L44-46    | ``compute``   |
| Status: RED < 1.00, AMBER < 1.05, else GREEN                         | L12-13, L47-52 | ``status_for`` |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.daycount import mat_bucket
from risk_models.common.rounding import money, rate

NSFR_MIN = Decimal("1.00")
NSFR_BUFFER = Decimal("1.05")


@dataclass(frozen=True)
class NsfrResult:
    n_lines: int
    asf: Decimal
    rsf: Decimal
    nsfr: Decimal
    status: str


def factor(side: str, category: str, bucket: str) -> Decimal:
    f = data.lookup("nsfr_factors.csv", "factor", side, category, bucket)
    if f is None:
        raise KeyError(f"no nsfr factor {side}/{category}/{bucket}")
    return f


def status_for(ratio: Decimal) -> str:
    if ratio < NSFR_MIN:
        return "RED"
    if ratio < NSFR_BUFFER:
        return "AMBER"
    return "GREEN"


def compute(as_of: dt.date, entity: str) -> NsfrResult:
    totals = {"ASF": Decimal(0), "RSF": Decimal(0)}
    n = 0
    for line in data.where("nsfr_balance_sheet.csv", entity=entity):
        maturity = line["maturity_date"]
        if maturity is not None and maturity <= as_of:
            continue
        weighted = line["amount_usd"] * factor(line["side"], line["category"],
                                               mat_bucket(as_of, maturity))
        totals["ASF" if line["side"] == "ASF" else "RSF"] += weighted
        n += 1
    asf, rsf = money(totals["ASF"]), money(totals["RSF"])
    ratio = rate(asf / rsf)
    return NsfrResult(n, asf, rsf, ratio, status_for(ratio))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["entity"]))
