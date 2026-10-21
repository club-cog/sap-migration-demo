"""Port of ``legacy/models/lib/stats.quill`` (losses are positive numbers).

| Python           | Quill (lib/stats.quill) | Rule                                              |
|------------------|-------------------------|---------------------------------------------------|
| ``losses_desc``  | L8-14                   | negate P&L, sort worst first                      |
| ``quantile_loss``| L17-24                  | k-th worst loss, k = ceil(n*(1-conf)), min 1; no interpolation |
| ``tail_mean``    | L27-38                  | mean of worst k, k = floor(n*(1-conf)), min 1     |

Quill lists are 1-indexed: ``ls[k]`` in Quill is ``ls[k - 1]`` here.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Iterable


def losses_desc(pnl: Iterable[Decimal]) -> list[Decimal]:
    return sorted((-p for p in pnl), reverse=True)


def quantile_loss(pnl: Iterable[Decimal], conf: Decimal) -> Decimal:
    ls = losses_desc(pnl)
    k = max(math.ceil(len(ls) * (1 - conf)), 1)
    return ls[k - 1]


def tail_mean(pnl: Iterable[Decimal], conf: Decimal) -> Decimal:
    ls = losses_desc(pnl)
    k = max(math.floor(len(ls) * (1 - conf)), 1)
    return sum(ls[:k], Decimal(0)) / k
