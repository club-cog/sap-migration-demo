"""Quill builtin functions and the DATE / TABLE namespaces.

Semantics that matter for parity with any port:

* Numbers are ``decimal.Decimal`` (default context, 28 significant digits).
* ``ROUND(x, n)`` is half-up (ties away from zero); ``TRUNC(x, n)`` drops digits toward zero.
* Lists are 1-indexed.
* Calendar: weekends only (the RiskDB holiday calendar is not emulated).
* ``TABLE.LOAD`` types each CSV cell: integers/decimals -> number, ``YYYY-MM-DD`` -> date,
  empty -> nil, anything else -> string.
* ``TABLE.LOOKUP(tbl, col, k1, k2, ...)`` matches k1.. against the table's leading key
  columns in file order; a table cell of ``*`` matches any key. First match wins.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import re
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Callable

from .errors import QuillError

NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Namespace:
    """A dotted builtin namespace such as ``DATE`` or ``TABLE``."""

    def __init__(self, name: str, members: dict[str, Callable[..., Any]]):
        self.name = name
        self.members = members

    def get(self, attr: str) -> Any:
        if attr not in self.members:
            raise QuillError(f"{self.name}.{attr} is not defined")
        return self.members[attr]


class Table:
    def __init__(self, name: str, columns: list[str], rows: list[dict[str, Any]]):
        self.name = name
        self.columns = columns
        self.rows = rows

    def __repr__(self) -> str:
        return f"<table {self.name} {len(self.rows)} rows>"


def type_name(v: Any) -> str:
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, Decimal):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, dt.date):
        return "date"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "record"
    if isinstance(v, Table):
        return "table"
    return type(v).__name__


def want(v: Any, kind: str, fn: str) -> Any:
    if type_name(v) != kind:
        raise QuillError(f"{fn}: expected {kind}, got {type_name(v)}")
    return v


def parse_cell(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return None
    if NUM_RE.match(s):
        return Decimal(s)
    if DATE_RE.match(s):
        return dt.date.fromisoformat(s)
    return s


# ---- general builtins --------------------------------------------------------
def b_len(x: Any) -> Decimal:
    if isinstance(x, (list, str, dict)):
        return Decimal(len(x))
    if isinstance(x, Table):
        return Decimal(len(x.rows))
    raise QuillError(f"LEN: unsupported type {type_name(x)}")


def b_append(lst: Any, x: Any) -> list:
    want(lst, "list", "APPEND").append(x)
    return lst


def _nums(fn: str, args: tuple) -> list[Decimal]:
    vals = list(args[0]) if len(args) == 1 and isinstance(args[0], list) else list(args)
    if not vals:
        raise QuillError(f"{fn}: no values")
    return [want(v, "number", fn) for v in vals]


def b_min(*args: Any) -> Decimal:
    return min(_nums("MIN", args))


def b_max(*args: Any) -> Decimal:
    return max(_nums("MAX", args))


def b_sum(lst: Any) -> Decimal:
    total = Decimal(0)
    for v in want(lst, "list", "SUM"):
        total += want(v, "number", "SUM")
    return total


def b_abs(x: Any) -> Decimal:
    return abs(want(x, "number", "ABS"))


def b_sqrt(x: Any) -> Decimal:
    x = want(x, "number", "SQRT")
    if x < 0:
        raise QuillError("SQRT: negative argument")
    return x.sqrt()


def b_exp(x: Any) -> Decimal:
    return want(x, "number", "EXP").exp()


def b_ln(x: Any) -> Decimal:
    x = want(x, "number", "LN")
    if x <= 0:
        raise QuillError("LN: argument must be positive")
    return x.ln()


def _quantum(n: Any, fn: str) -> Decimal:
    n = want(n, "number", fn)
    return Decimal(1).scaleb(-int(n))


def b_round(x: Any, n: Any = Decimal(0)) -> Decimal:
    return want(x, "number", "ROUND").quantize(_quantum(n, "ROUND"), rounding=ROUND_HALF_UP)


def b_trunc(x: Any, n: Any = Decimal(0)) -> Decimal:
    return want(x, "number", "TRUNC").quantize(_quantum(n, "TRUNC"), rounding=ROUND_DOWN)


def b_floor(x: Any) -> Decimal:
    return want(x, "number", "FLOOR").to_integral_value(rounding=ROUND_FLOOR)


def b_ceil(x: Any) -> Decimal:
    return want(x, "number", "CEIL").to_integral_value(rounding=ROUND_CEILING)


def b_sort(lst: Any, order: Any = "ASC") -> list:
    items = list(want(lst, "list", "SORT"))
    if order not in ("ASC", "DESC"):
        raise QuillError("SORT: order must be \"ASC\" or \"DESC\"")
    return sorted(items, reverse=(order == "DESC"))


def b_num(x: Any) -> Decimal | None:
    if x is None or isinstance(x, Decimal):
        return x
    s = want(x, "string", "NUM").strip()
    if s == "":
        return None
    if not NUM_RE.match(s):
        raise QuillError(f"NUM: not a number: {s!r}")
    return Decimal(s)


def b_str(x: Any) -> str:
    from .interpreter import format_value

    return format_value(x)


def b_keys(rec: Any) -> list:
    return list(want(rec, "record", "KEYS").keys())


def b_has(rec: Any, key: Any) -> bool:
    return want(key, "string", "HAS") in want(rec, "record", "HAS")


def b_get(rec: Any, key: Any, default: Any = None) -> Any:
    return want(rec, "record", "GET").get(want(key, "string", "GET"), default)


def b_isnil(x: Any) -> bool:
    return x is None


def b_range(a: Any, b: Any) -> list:
    a, b = int(want(a, "number", "RANGE")), int(want(b, "number", "RANGE"))
    return [Decimal(i) for i in range(a, b + 1)]


def b_error(msg: Any) -> None:
    raise QuillError(f"ERROR: {msg}")


# ---- DATE --------------------------------------------------------------------
def d_parse(s: Any) -> dt.date:
    if isinstance(s, dt.date):
        return s
    s = want(s, "string", "DATE.PARSE").strip()
    if not DATE_RE.match(s):
        raise QuillError(f"DATE.PARSE: bad date {s!r}")
    return dt.date.fromisoformat(s)


def d_make(y: Any, m: Any, d: Any) -> dt.date:
    return dt.date(int(y), int(m), int(d))


def _add_months(d: dt.date, months: int) -> dt.date:
    total = d.year * 12 + (d.month - 1) + months
    y, m = divmod(total, 12)
    m += 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def d_add(d: Any, n: Any, unit: Any = "D") -> dt.date:
    d = want(d, "date", "DATE.ADD")
    k = int(want(n, "number", "DATE.ADD"))
    if unit == "D":
        return d + dt.timedelta(days=k)
    if unit == "M":
        return _add_months(d, k)
    if unit == "Y":
        return _add_months(d, 12 * k)
    raise QuillError(f"DATE.ADD: unknown unit {unit!r}")


def is_bus(d: dt.date) -> bool:
    return d.weekday() < 5


def d_roll(d: Any, conv: Any = "F") -> dt.date:
    d = want(d, "date", "DATE.ROLL")
    if conv not in ("F", "P", "MF", "MP"):
        raise QuillError(f"DATE.ROLL: unknown convention {conv!r}")
    step = 1 if conv in ("F", "MF") else -1
    r = d
    while not is_bus(r):
        r += dt.timedelta(days=step)
    if conv in ("MF", "MP") and r.month != d.month:
        r = d
        while not is_bus(r):
            r -= dt.timedelta(days=step)
    return r


def d_dow(d: Any) -> Decimal:
    return Decimal(want(d, "date", "DATE.DOW").isoweekday())


def d_diff(d1: Any, d2: Any) -> Decimal:
    return Decimal((want(d2, "date", "DATE.DIFF") - want(d1, "date", "DATE.DIFF")).days)


def d_eom(d: Any) -> dt.date:
    d = want(d, "date", "DATE.EOM")
    return dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def d_isbus(d: Any) -> bool:
    return is_bus(want(d, "date", "DATE.ISBUS"))


def b_busdays(d1: Any, d2: Any) -> Decimal:
    """Business days in (d1, d2]. Negative if d2 < d1."""
    a, b = want(d1, "date", "BUSDAYS"), want(d2, "date", "BUSDAYS")
    sign = 1
    if b < a:
        a, b, sign = b, a, -1
    count = 0
    cur = a
    while cur < b:
        cur += dt.timedelta(days=1)
        if is_bus(cur):
            count += 1
    return Decimal(sign * count)


DATE_NS = Namespace("DATE", {
    "PARSE": d_parse,
    "MAKE": d_make,
    "ADD": d_add,
    "ROLL": d_roll,
    "DOW": d_dow,
    "YEAR": lambda d: Decimal(want(d, "date", "DATE.YEAR").year),
    "MONTH": lambda d: Decimal(want(d, "date", "DATE.MONTH").month),
    "DAY": lambda d: Decimal(want(d, "date", "DATE.DAY").day),
    "DIFF": d_diff,
    "EOM": d_eom,
    "ISBUS": d_isbus,
})


# ---- TABLE -------------------------------------------------------------------
def make_table_ns(data_dir: Path) -> Namespace:
    cache: dict[str, Table] = {}

    def t_load(name: Any) -> Table:
        name = want(name, "string", "TABLE.LOAD")
        if name not in cache:
            path = data_dir / name
            if not path.exists():
                raise QuillError(f"TABLE.LOAD: no such table {name!r}")
            with path.open(newline="") as fh:
                reader = csv.reader(fh)
                header = [h.strip() for h in next(reader)]
                rows = [
                    {col: parse_cell(val) for col, val in zip(header, raw)}
                    for raw in reader
                    if raw and any(v.strip() for v in raw)
                ]
            cache[name] = Table(name, header, rows)
        return cache[name]

    def t_lookup(tbl: Any, col: Any, *keys: Any) -> Any:
        tbl = want(tbl, "table", "TABLE.LOOKUP")
        if col not in tbl.columns:
            raise QuillError(f"TABLE.LOOKUP: {tbl.name} has no column {col!r}")
        key_cols = tbl.columns[: len(keys)]
        for row in tbl.rows:
            if all(row[c] == "*" or _eq(row[c], k) for c, k in zip(key_cols, keys)):
                return row[col]
        return None

    def t_rows(tbl: Any) -> list:
        return [dict(r) for r in want(tbl, "table", "TABLE.ROWS").rows]

    def t_where(tbl: Any, *pairs: Any) -> list:
        tbl = want(tbl, "table", "TABLE.WHERE")
        if len(pairs) % 2:
            raise QuillError("TABLE.WHERE: expects column/value pairs")
        conds = list(zip(pairs[0::2], pairs[1::2]))
        for c, _ in conds:
            if c not in tbl.columns:
                raise QuillError(f"TABLE.WHERE: {tbl.name} has no column {c!r}")
        return [dict(r) for r in tbl.rows if all(_eq(r[c], v) for c, v in conds)]

    return Namespace("TABLE", {"LOAD": t_load, "LOOKUP": t_lookup, "ROWS": t_rows,
                               "WHERE": t_where})


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        return a == b
    if type_name(a) != type_name(b):
        return False
    return a == b


def make_builtins(data_dir: Path) -> dict[str, Any]:
    return {
        "LEN": b_len, "APPEND": b_append, "MIN": b_min, "MAX": b_max, "SUM": b_sum,
        "ABS": b_abs, "SQRT": b_sqrt, "EXP": b_exp, "LN": b_ln, "ROUND": b_round,
        "TRUNC": b_trunc, "FLOOR": b_floor, "CEIL": b_ceil, "SORT": b_sort, "NUM": b_num,
        "STR": b_str, "KEYS": b_keys, "HAS": b_has, "GET": b_get, "ISNIL": b_isnil,
        "RANGE": b_range, "ERROR": b_error, "BUSDAYS": b_busdays,
        "DATE": DATE_NS, "TABLE": make_table_ns(data_dir),
    }
