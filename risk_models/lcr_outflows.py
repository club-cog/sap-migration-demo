"""LCR: stressed 30-day net cash outflows and ratio. Port of ``legacy/models/lcr_outflows.quill``.

Business rules (Quill line numbers refer to ``legacy/models/lcr_outflows.quill``):

| Rule                                                                       | Quill   | Python             |
|----------------------------------------------------------------------------|---------|--------------------|
| 30-day horizon; nil maturity = non-maturity deposit, always in window      | L13, L23-28 | ``in_window``  |
| Outflow = USD balance x run-off rate from ``lcr_runoff.csv``; missing rate is an error | L30-45 | ``outflows`` |
| Stress scenario adds ``stress_runoff_addon`` to the run-off rate, capped at 100% | L38-41 | ``outflows``   |
| Inflow rates hard-coded by category (never moved to a table)               | L18     | ``INFLOW_RATE``    |
| Open-maturity inflows are not counted                                      | L50-51  | ``inflows``        |
| Inflows capped at 75% of gross outflows                                    | L14, L68 | ``compute``       |
| **Stress haircut**: extra HQLA haircut L1 0 / L2A +10 pts / L2B +20 pts when flag = Y (ALCO 2013-06) | L20, L61-65 | ``STRESS_HAIRCUT``, ``compute`` |
| HQLA stock comes from ``hqla_haircut.hqla_stock`` (shared dependency)       | L7, L65 | ``compute``        |
| LCR = HQLA / net outflows, 6 dp; gross / inflows / capped rounded to 2 dp  | L66-70  | ``compute``        |
| Status: RED < 1.00, AMBER < 1.10 (internal buffer), else GREEN             | L15-16, L71-76 | ``status_for`` |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping

from risk_models import hqla_haircut as hq
from risk_models.common import data
from risk_models.common.rounding import money, rate

HORIZON_DAYS = 30
INFLOW_CAP = Decimal("0.75")
LCR_MIN = Decimal("1.00")
LCR_BUFFER = Decimal("1.10")
INFLOW_RATE: dict[str, Decimal] = {
    "RETAIL_LOANS": Decimal("0.50"), "FI_LOANS": Decimal("1.00"),
    "SEC_LENDING_L1": Decimal(0), "SEC_LENDING_OTHER": Decimal("0.50"),
}
STRESS_HAIRCUT: Mapping[str, Decimal] = {"L1": Decimal(0), "L2A": Decimal("0.10"),
                                         "L2B": Decimal("0.20")}


@dataclass(frozen=True)
class LcrResult:
    hqla: Decimal
    gross_outflows: Decimal
    inflows: Decimal
    capped_inflows: Decimal
    net_outflows: Decimal
    lcr: Decimal
    status: str


def in_window(maturity: dt.date | None, as_of: dt.date) -> bool:
    if maturity is None:
        return True
    return as_of < maturity <= as_of + dt.timedelta(days=HORIZON_DAYS)


def outflows(as_of: dt.date, entity: str, stressed: bool) -> Decimal:
    total = Decimal(0)
    for f in data.where("funding.csv", entity=entity):
        if not in_window(f["maturity_date"], as_of):
            continue
        runoff = data.lookup("lcr_runoff.csv", "runoff", f["category"])
        if runoff is None:
            raise KeyError(f"no runoff for {f['category']}")
        if stressed:
            runoff += data.lookup("lcr_runoff.csv", "stress_runoff_addon", f["category"])
        total += hq.to_usd(f["balance"], f["ccy"]) * min(runoff, Decimal(1))
    return total


def inflows(as_of: dt.date, entity: str) -> Decimal:
    total = Decimal(0)
    for i in data.where("lcr_inflows.csv", entity=entity):
        if i["maturity_date"] is not None and in_window(i["maturity_date"], as_of):
            total += hq.to_usd(i["balance"], i["ccy"]) * INFLOW_RATE[i["category"]]
    return total


def status_for(lcr: Decimal) -> str:
    if lcr < LCR_MIN:
        return "RED"
    if lcr < LCR_BUFFER:
        return "AMBER"
    return "GREEN"


def compute(as_of: dt.date, entity: str, stressed: bool) -> LcrResult:
    addon = STRESS_HAIRCUT if stressed else hq.NO_ADDON
    stock = hq.hqla_stock(as_of, entity, addon)
    gross = money(outflows(as_of, entity, stressed))
    infl = money(inflows(as_of, entity))
    capped = min(infl, money(INFLOW_CAP * gross))
    net = gross - capped
    lcr = rate(stock.hqla / net)
    return LcrResult(stock.hqla, gross, infl, capped, net, lcr, status_for(lcr))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["entity"],
                          case["stress_flag"] == "Y"))
