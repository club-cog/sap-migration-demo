"""Port of ``legacy/models/lib/rounding.quill``. All money/rate rounding goes through here.

| Python        | Quill (lib/rounding.quill) | Rule                                 |
|---------------|----------------------------|--------------------------------------|
| ``money``     | L11-13                     | 2 dp, half-up (away from zero)       |
| ``rate``      | L16-18                     | 6 dp, half-up                        |
| ``to_unit``   | L21-26                     | nearest whole ``unit``, half-up      |
| ``floor_at``  | L36-41                     | max(x, lo)                           |
| ``cap_at``    | L43-48                     | min(x, hi)                           |
| ``clamp``     | L50-52                     | cap_at(floor_at(x, lo), hi)          |

``to_unit_v1`` (L29-34, "eod batch v1") is intentionally NOT ported. A model that calls it
needs a findings note before its port can be merged (see docs/playbook-quill-to-python.md).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MONEY_DP = 2
RATE_DP = 6


def round_half_up(x: Decimal, dp: int) -> Decimal:
    return x.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def money(x: Decimal) -> Decimal:
    return round_half_up(x, MONEY_DP)


def rate(x: Decimal) -> Decimal:
    return round_half_up(x, RATE_DP)


def to_unit(x: Decimal, unit: Decimal) -> Decimal:
    if unit <= 0:
        return money(x)
    return round_half_up(x / unit, 0) * unit


def floor_at(x: Decimal, lo: Decimal) -> Decimal:
    return lo if x < lo else x


def cap_at(x: Decimal, hi: Decimal) -> Decimal:
    return hi if x > hi else x


def clamp(x: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return cap_at(floor_at(x, lo), hi)
