"""Parity: every Python port vs the legacy reference outputs, case by case.

Comparison rule (stated once, applied to every field):

* numeric fields: ``Decimal`` comparison with absolute tolerance ``1e-9``
  (all legacy outputs are rounded to <= 6 dp, so in practice this is an exact match);
* text, dates, booleans, empty (nil) fields: exact match of the canonical text form.

A model whose ``risk_models/<model>.py`` does not exist yet is SKIPPED (not migrated).
Cases listed in ``known_deviations.py`` run as strict xfail with the recorded reason.
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib
import importlib.util
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pytest

from .known_deviations import KNOWN_DEVIATIONS

ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / "legacy" / "reference_outputs"
CASES_DIR = ROOT / "legacy" / "data" / "cases"
ABS_TOL = Decimal("1e-9")
MODELS = sorted(p.stem for p in REF_DIR.glob("*.csv"))


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as fh:
        r = csv.DictReader(fh)
        return list(r.fieldnames or []), list(r)


def migrated(model: str) -> bool:
    return importlib.util.find_spec(f"risk_models.{model}") is not None


def canonical(v: Any) -> str:
    """Same text form the Quill runtime writes to reference outputs."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, Decimal)):
        d = Decimal(v)
        return "0" if d == 0 else format(d.normalize(), "f")
    if isinstance(v, float):
        raise TypeError("ports must return Decimal, not float")
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v)


def _as_decimal(s: str) -> Decimal | None:
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def diff_fields(expected: dict[str, str], actual: dict[str, Any]) -> list[str]:
    out = []
    for col, want in expected.items():
        if col not in actual:
            out.append(f"{col}: missing (expected {want!r})")
            continue
        got = canonical(actual[col])
        a, b = _as_decimal(want), _as_decimal(got)
        same = abs(a - b) <= ABS_TOL if a is not None and b is not None else got == want
        if not same:
            out.append(f"{col}: expected {want!r}, got {got!r}")
    return out


def _params():
    params = []
    for model in MODELS:
        if not migrated(model):
            params.append(pytest.param(model, None, id=f"{model}-not-migrated",
                                       marks=pytest.mark.skip(
                                           reason=f"risk_models/{model}.py not migrated yet")))
            continue
        _, refs = _read(REF_DIR / f"{model}.csv")
        deviations = KNOWN_DEVIATIONS.get(model, {})
        for ref in refs:
            cid = ref["case_id"]
            marks = ([pytest.mark.xfail(reason=deviations[cid], strict=True)]
                     if cid in deviations else [])
            params.append(pytest.param(model, cid, id=f"{model}-{cid}", marks=marks))
    return params


@pytest.mark.parametrize("model,case_id", _params())
def test_parity(model: str, case_id: str) -> None:
    case_cols, cases = _read(CASES_DIR / f"{model}.csv")
    ref_cols, refs = _read(REF_DIR / f"{model}.csv")
    case = next(c for c in cases if c["case_id"] == case_id)
    ref = next(r for r in refs if r["case_id"] == case_id)
    out_cols = [c for c in ref_cols if c not in case_cols]
    port = importlib.import_module(f"risk_models.{model}")
    actual = port.run(dict(case))
    problems = diff_fields({c: ref[c] for c in out_cols}, actual)
    assert not problems, f"{model} {case_id} differs from legacy:\n  " + "\n  ".join(problems)


def test_known_deviations_refer_to_real_cases():
    for model, cases in KNOWN_DEVIATIONS.items():
        assert model in MODELS, model
        _, refs = _read(REF_DIR / f"{model}.csv")
        ids = {r["case_id"] for r in refs}
        for cid, reason in cases.items():
            assert cid in ids, f"{model}: unknown case {cid}"
            assert reason.strip(), f"{model} {cid}: xfail needs a reason"
