"""Typed CSV access to ``legacy/data`` with the same cell typing as Quill ``TABLE.LOAD``.

* integers / decimals -> ``Decimal``; ``YYYY-MM-DD`` -> ``datetime.date``; empty -> ``None``;
  anything else -> ``str``.
* :func:`lookup` mirrors ``TABLE.LOOKUP``: keys match the leading columns in order, a ``*``
  cell is a wildcard, first match wins, a miss returns ``None``.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

DATA_DIR = Path(__file__).resolve().parents[2] / "legacy" / "data"

_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

Row = Mapping[str, Any]


def parse_cell(raw: str) -> Decimal | dt.date | str | None:
    s = raw.strip()
    if s == "":
        return None
    if _NUM.match(s):
        return Decimal(s)
    if _DATE.match(s):
        return dt.date.fromisoformat(s)
    return s


@lru_cache(maxsize=None)
def _load(name: str) -> tuple[tuple[str, ...], tuple[dict[str, Any], ...]]:
    with (DATA_DIR / name).open(newline="") as fh:
        reader = csv.reader(fh)
        header = tuple(h.strip() for h in next(reader))
        rows = tuple(
            {c: parse_cell(v) for c, v in zip(header, raw)}
            for raw in reader
            if raw and any(v.strip() for v in raw)
        )
    return header, rows


def columns(name: str) -> tuple[str, ...]:
    return _load(name)[0]


def rows(name: str) -> list[dict[str, Any]]:
    """All rows of ``legacy/data/<name>`` (copies, safe to mutate)."""
    return [dict(r) for r in _load(name)[1]]


def where(name: str, **conds: Any) -> list[dict[str, Any]]:
    """Rows where every ``column == value`` (``TABLE.WHERE``)."""
    return [r for r in rows(name) if all(r[c] == v for c, v in conds.items())]


def lookup(name: str, col: str, *keys: Any) -> Any:
    """``TABLE.LOOKUP(name, col, keys...)``: first row whose leading columns match ``keys``."""
    header, data = _load(name)
    key_cols: Sequence[str] = header[: len(keys)]
    for r in data:
        if all(r[c] == "*" or r[c] == k for c, k in zip(key_cols, keys)):
            return r[col]
    return None
