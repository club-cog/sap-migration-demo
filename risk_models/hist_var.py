"""1-day / 10-day historical-simulation VaR. Port of ``legacy/models/hist_var.quill``.

Business rules (Quill line numbers refer to ``legacy/models/hist_var.quill``):

| Rule                                                               | Quill     | Python          |
|--------------------------------------------------------------------|-----------|-----------------|
| 250-day window, equal weights, ending at (and including) as-of     | L13, L24-30 | ``pnl_series`` |
| Daily P&L = sum(exposure x factor return) from ``var_exposures.csv`` | L31-38  | ``pnl_series``  |
| Portfolio without exposures is an error                            | L19-22    | ``pnl_series``  |
| Fewer than 200 observations -> INSUFFICIENT, all metrics empty     | L14, L54-56 | ``compute``   |
| VaR = k-th worst loss, k = ceil(n x (1-conf)), no interpolation    | L64 + lib/stats.quill L17-24 | ``stats.quantile_loss`` |
| VaR floored at 0 (MRM-2012-31)                                     | L63-64    | ``compute``     |
| 10-day VaR = 1-day x sqrt(10)                                      | L15, L65  | ``SCALE_10D``   |
| Worst day = first day with the lowest P&L                          | L57-62    | ``compute``     |
| Money outputs rounded to 2 dp                                      | L65       | ``compute``     |

``pnl_series`` / ``WINDOW`` / ``MIN_OBS`` / ``SCALE_10D`` are reused by ``expected_shortfall``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models.common import data
from risk_models.common.rounding import money
from risk_models.common.stats import quantile_loss

WINDOW = 250
MIN_OBS = 200
SCALE_10D = Decimal(10).sqrt()


@dataclass(frozen=True)
class DailyPnl:
    date: dt.date
    pnl: Decimal


@dataclass(frozen=True)
class VarResult:
    n_obs: int
    var_1d: Decimal | None
    var_10d: Decimal | None
    worst_loss: Decimal | None
    worst_date: dt.date | None
    status: str


def pnl_series(portfolio: str, as_of: dt.date, n: int) -> list[DailyPnl]:
    exposures = data.where("var_exposures.csv", portfolio=portfolio)
    if not exposures:
        raise KeyError(f"no exposures for {portfolio}")
    history = [r for r in data.rows("market_history.csv") if r["date"] <= as_of][-n:]
    out = []
    for day in history:
        p = Decimal(0)
        for e in exposures:
            p = p + e["exposure"] * day[e["factor"]]
        out.append(DailyPnl(day["date"], p))
    return out


def compute(portfolio: str, as_of: dt.date, confidence: Decimal) -> VarResult:
    series = pnl_series(portfolio, as_of, WINDOW)
    n = len(series)
    if n < MIN_OBS:
        return VarResult(n, None, None, None, None, "INSUFFICIENT")
    worst = min(series, key=lambda s: s.pnl)
    var_1d = max(quantile_loss((s.pnl for s in series), confidence), Decimal(0))
    return VarResult(n, money(var_1d), money(var_1d * SCALE_10D), money(-worst.pnl),
                     worst.date, "OK")


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(case["portfolio"], dt.date.fromisoformat(case["as_of"]),
                          Decimal(case["confidence"])))
