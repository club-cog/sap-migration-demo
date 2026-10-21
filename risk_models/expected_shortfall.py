"""97.5% expected shortfall, current vs stressed window.
Port of ``legacy/models/expected_shortfall.quill``.

Business rules (Quill line numbers refer to ``legacy/models/expected_shortfall.quill``):

| Rule                                                                 | Quill    | Python            |
|----------------------------------------------------------------------|----------|-------------------|
| P&L series and 250d window / 200 min obs reused from ``hist_var``    | L7, L30-33 | ``compute``     |
| ES = mean of worst k losses, k = floor(n x 2.5%), min 1              | L11, L35-36 + lib/stats.quill L27-38 | ``stats.tail_mean`` |
| Stress window fixed 2023-02-01 .. 2023-05-31 (do not roll)           | L12-14, L17-26 | ``stressed_pnl`` |
| Reported ES = max(current, 75% x stressed); binding = CURRENT/STRESS | L15, L37-42 | ``compute``     |
| 10-day ES = reported x sqrt(10); money outputs to 2 dp               | L43      | ``compute``       |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models import hist_var as hv
from risk_models.common.rounding import money
from risk_models.common.stats import tail_mean

ES_CONF = Decimal("0.975")
STRESS_FROM = dt.date(2023, 2, 1)
STRESS_TO = dt.date(2023, 5, 31)
STRESS_WEIGHT = Decimal("0.75")
STRESS_LOOKBACK = 400


@dataclass(frozen=True)
class EsResult:
    n_obs: int
    es_1d: Decimal | None
    es_stress_1d: Decimal | None
    es_reported_1d: Decimal | None
    es_10d: Decimal | None
    binding: str | None
    status: str


def stressed_pnl(portfolio: str) -> list[Decimal]:
    return [s.pnl for s in hv.pnl_series(portfolio, STRESS_TO, STRESS_LOOKBACK)
            if s.date >= STRESS_FROM]


def compute(portfolio: str, as_of: dt.date) -> EsResult:
    series = hv.pnl_series(portfolio, as_of, hv.WINDOW)
    n = len(series)
    if n < hv.MIN_OBS:
        return EsResult(n, None, None, None, None, None, "INSUFFICIENT")
    current = tail_mean([s.pnl for s in series], ES_CONF)
    stressed = tail_mean(stressed_pnl(portfolio), ES_CONF)
    reported, binding = current, "CURRENT"
    if STRESS_WEIGHT * stressed > current:
        reported, binding = STRESS_WEIGHT * stressed, "STRESS"
    return EsResult(n, money(current), money(stressed), money(reported),
                    money(reported * hv.SCALE_10D), binding, "OK")


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(case["portfolio"], dt.date.fromisoformat(case["as_of"])))
