"""Port of ``legacy/models/lib/daycount.quill``.

| Python        | Quill (lib/daycount.quill) | Rule                                              |
|---------------|----------------------------|---------------------------------------------------|
| ``yearfrac``  | L9-25                      | A360 / A365 / 30360 (US, no Feb EOM adjustment)    |
| ``years_to``  | L28-37                     | residual years (A365), floored at 0; None -> 99    |
| ``mat_bucket``| L40-48                     | "LT6M" (<0.5y), "6M1Y" (<1y), "GE1Y"              |
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal

Basis = Literal["A360", "A365", "30360"]
DEFAULT_BASIS: Basis = "A365"
OPEN_ENDED_YEARS = Decimal(99)


def yearfrac(d1: dt.date, d2: dt.date, basis: Basis) -> Decimal:
    if basis == "A360":
        return Decimal((d2 - d1).days) / 360
    if basis == "A365":
        return Decimal((d2 - d1).days) / 365
    if basis == "30360":
        dd1 = min(d1.day, 30)
        dd2 = min(d2.day, 30) if dd1 == 30 else d2.day
        days = 360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (dd2 - dd1)
        return Decimal(days) / 360
    raise ValueError(f"yearfrac: bad basis {basis!r}")


def years_to(as_of: dt.date, maturity: dt.date | None) -> Decimal:
    if maturity is None:
        return OPEN_ENDED_YEARS
    return max(yearfrac(as_of, maturity, DEFAULT_BASIS), Decimal(0))


def mat_bucket(as_of: dt.date, maturity: dt.date | None) -> str:
    y = years_to(as_of, maturity)
    if y < Decimal("0.5"):
        return "LT6M"
    if y < 1:
        return "6M1Y"
    return "GE1Y"
