"""Daily variation-margin call per CSA. Port of ``legacy/models/collateral_margin_call.quill``.

Business rules (Quill line numbers refer to ``legacy/models/collateral_margin_call.quill``):

| Rule                                                                  | Quill     | Python            |
|-----------------------------------------------------------------------|-----------|-------------------|
| Unknown CSA / missing fixing is an error                              | L13-19, L22-26 | ``compute``  |
| Collateral haircut by type from ``csa_haircuts.csv``                  | L28       | ``margin_position`` |
| Required = max(exposure - threshold, 0) + independent amount (IA not subject to threshold) | L29 | ``margin_position`` |
| Held = collateral MV x (1 - haircut)                                  | L30       | ``margin_position`` |
| Required / held / diff rounded to 2 dp (diff from unrounded values)   | L31       | ``margin_position`` |
| No call if abs(diff) < MTA                                            | L36-38    | ``call_for``      |
| diff > 0 -> DELIVERY of diff; else RETURN of min(-diff, held)          | L39-42    | ``call_for``      |
| Weekend as-of: no Sat/Sun fixing, use prior Friday close (COLL-OPS-04 2.3) | L49-52, L62-64 | ``fixing_date`` |
| Call amount rounded to the CSA rounding unit, **half-up** (``rounding.to_unit``) | L67 + lib/rounding.quill L21-26 | ``compute`` |

Deliberate deviation: the legacy weekend path (L55) rounds with ``rounding.to_unit_v1``
(lib/rounding.quill L29-34), which TRUNCATES. This port applies half-up rounding on every day.
The 3 weekend reference cases differ and are xfail; see ``docs/findings/collateral_margin_call.md``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.rounding import money, to_unit

ZERO = Decimal(0)


@dataclass(frozen=True)
class MarginPosition:
    exposure: Decimal
    required: Decimal
    held: Decimal
    diff: Decimal


@dataclass(frozen=True)
class MarginCall:
    fixing_date: dt.date
    exposure: Decimal
    required: Decimal
    held_post_hc: Decimal
    raw_diff: Decimal
    call_type: str
    call_amount: Decimal


def fixing_date(as_of: dt.date) -> dt.date:
    """Saturday/Sunday use the preceding Friday fixing."""
    d = as_of
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def margin_position(csa: Mapping[str, Any], fix_dt: dt.date) -> MarginPosition:
    rows = data.where("margin_mtm.csv", date=fix_dt, csa_id=csa["csa_id"])
    if not rows:
        raise KeyError(f"no fixing {fix_dt} {csa['csa_id']}")
    m = rows[0]
    haircut = data.lookup("csa_haircuts.csv", "haircut", m["coll_type"])
    required = max(m["exposure"] - csa["threshold"], ZERO) + csa["independent_amount"]
    held = m["coll_mv"] * (1 - haircut)
    return MarginPosition(m["exposure"], money(required), money(held), money(required - held))


def call_for(pos: MarginPosition, mta: Decimal) -> tuple[str, Decimal]:
    if abs(pos.diff) < mta:
        return "NONE", ZERO
    if pos.diff > 0:
        return "DELIVERY", pos.diff
    return "RETURN", min(-pos.diff, pos.held)


def compute(as_of: dt.date, csa_id: str) -> MarginCall:
    rows = data.where("csa_agreements.csv", csa_id=csa_id)
    if not rows:
        raise KeyError(f"unknown csa {csa_id}")
    csa = rows[0]
    fix_dt = fixing_date(as_of)
    pos = margin_position(csa, fix_dt)
    call_type, amount = call_for(pos, csa["mta"])
    return MarginCall(fix_dt, pos.exposure, pos.required, pos.held, pos.diff, call_type,
                      to_unit(amount, csa["rounding_unit"]))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["csa_id"]))
