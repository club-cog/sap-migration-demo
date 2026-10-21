"""FRTB-style SA delta capital for interest rates (GIRR), per desk.
Port of ``legacy/models/frtb_ir_delta.quill``.

Business rules (Quill line numbers refer to ``legacy/models/frtb_ir_delta.quill``):

| Rule                                                                  | Quill     | Python            |
|-----------------------------------------------------------------------|-----------|-------------------|
| One bucket per currency; 10 fixed tenors                              | L11       | ``TENORS``        |
| Risk weight by tenor from ``frtb_ir_rw.csv``                          | L47       | ``weighted_sensitivities`` |
| "Specified" liquid currencies get risk weight / sqrt(2) (list frozen 2016) | L15-16, L18-25, L49-51 | ``LIQUID_CCY`` |
| Weighted sensitivity = rw x sensitivity, summed per (ccy, tenor)      | L42-59    | ``weighted_sensitivities`` |
| Tenor correlation rho = max(exp(-theta * abs(t1-t2) / min(t1,t2)), 40%), theta 3% | L12-13, L27-29 | ``rho`` |
| Correlation scenarios HIGH = min(1.25c, 1), LOW = max(2c-1, 0.75c), MED = c | L32-39 | ``scenario_corr`` |
| Bucket charge Kb = sqrt(max(sum rho WS_k WS_l, 0))                    | L61-76    | ``charge``        |
| Sb = sum(WS) bounded to [-Kb, Kb]                                     | L77       | ``charge``        |
| Cross-bucket gamma 50% (scenario-adjusted); total = sqrt(max(sum, 0)) | L14, L79-89 | ``charge``      |
| Capital = max over LOW / MED / HIGH; tie order MED, HIGH, LOW         | L92-106   | ``compute``       |
| Top bucket = largest MED Kb (first wins on ties)                      | L107-114  | ``compute``       |
| Money outputs rounded to 2 dp                                         | L115      | ``compute``       |
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal, Mapping

from risk_models.common import data
from risk_models.common.rounding import money

Scenario = Literal["LOW", "MED", "HIGH"]
TENORS: tuple[Decimal, ...] = tuple(Decimal(t) for t in
                                    ("0.25", "0.5", "1", "2", "3", "5", "10", "15", "20", "30"))
THETA = Decimal("0.03")
RHO_FLOOR = Decimal("0.40")
GAMMA = Decimal("0.50")
LIQUID_CCY = frozenset({"USD", "EUR", "GBP", "AUD", "JPY", "SEK", "CAD"})
ONE, ZERO = Decimal(1), Decimal(0)


@dataclass(frozen=True)
class Charge:
    total: Decimal
    kb: dict[str, Decimal]


@dataclass(frozen=True)
class FrtbResult:
    n_buckets: int
    delta_low: Decimal
    delta_med: Decimal
    delta_high: Decimal
    delta_charge: Decimal
    binding_scenario: str
    top_bucket: str
    top_bucket_kb: Decimal


def rho(t1: Decimal, t2: Decimal) -> Decimal:
    return max((-THETA * abs(t1 - t2) / min(t1, t2)).exp(), RHO_FLOOR)


def scenario_corr(c: Decimal, scenario: Scenario) -> Decimal:
    if scenario == "HIGH":
        return min(c * Decimal("1.25"), ONE)
    if scenario == "LOW":
        return max(2 * c - 1, Decimal("0.75") * c)
    return c


def weighted_sensitivities(as_of: dt.date, desk: str) -> dict[str, list[Decimal]]:
    ws: dict[str, list[Decimal]] = {}
    for r in data.where("ir_sensitivities.csv", as_of=as_of, desk=desk):
        vec = ws.setdefault(r["ccy"], [ZERO] * len(TENORS))
        rw = data.lookup("frtb_ir_rw.csv", "rw", r["tenor"])
        if r["ccy"] in LIQUID_CCY:
            rw = rw / Decimal(2).sqrt()
        k = TENORS.index(r["tenor"])
        vec[k] = vec[k] + rw * r["sens"]
    return ws


def charge(ws: Mapping[str, list[Decimal]], scenario: Scenario) -> Charge:
    kb: dict[str, Decimal] = {}
    sb: dict[str, Decimal] = {}
    n = len(TENORS)
    for ccy, v in ws.items():
        acc = ZERO
        for k in range(n):
            for l in range(n):
                if k == l:
                    acc = acc + v[k] * v[k]
                else:
                    acc = acc + scenario_corr(rho(TENORS[k], TENORS[l]), scenario) * v[k] * v[l]
        kb[ccy] = max(acc, ZERO).sqrt()
        sb[ccy] = max(min(sum(v, ZERO), kb[ccy]), -kb[ccy])
    gamma = scenario_corr(GAMMA, scenario)
    tot = ZERO
    for b in kb:
        tot = tot + kb[b] * kb[b]
        for c in kb:
            if b != c:
                tot = tot + gamma * sb[b] * sb[c]
    return Charge(max(tot, ZERO).sqrt(), kb)


def compute(as_of: dt.date, desk: str) -> FrtbResult:
    ws = weighted_sensitivities(as_of, desk)
    by_scn = {s: charge(ws, s) for s in ("LOW", "MED", "HIGH")}
    best: Scenario = "MED"
    for s in ("HIGH", "LOW"):
        if by_scn[s].total > by_scn[best].total:
            best = s
    top, top_kb = "", Decimal(-1)
    for ccy, k in by_scn["MED"].kb.items():
        if k > top_kb:
            top, top_kb = ccy, k
    return FrtbResult(len(ws), money(by_scn["LOW"].total), money(by_scn["MED"].total),
                      money(by_scn["HIGH"].total), money(by_scn[best].total), best, top,
                      money(top_kb))


def run(case: Mapping[str, str]) -> dict[str, Any]:
    return asdict(compute(dt.date.fromisoformat(case["as_of"]), case["desk"]))
