"""Regenerate (or check) the reference outputs by running every Quill model.

    python -m legacy.quill_runtime.run_all             # rewrite legacy/reference_outputs/*.csv
    python -m legacy.quill_runtime.run_all --check     # exit 1 if any committed file differs
    python -m legacy.quill_runtime.run_all --model hqla_haircut

Each model ``legacy/models/<model>.quill`` exposes ``defn run(case)``. Cases come from
``legacy/data/cases/<model>.csv``; every case column is passed as a string. The output file
has the case columns followed by the fields of the record returned by ``run``.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from .errors import QuillError
from .interpreter import DEFAULT_DATA_DIR, DEFAULT_MODELS_DIR, REPO_ROOT, Interpreter, format_value

CASES_DIR = DEFAULT_DATA_DIR / "cases"
REFERENCE_DIR = REPO_ROOT / "legacy" / "reference_outputs"


def model_names() -> list[str]:
    return sorted(p.stem for p in CASES_DIR.glob("*.csv"))


def read_cases(model: str) -> tuple[list[str], list[dict[str, str]]]:
    with (CASES_DIR / f"{model}.csv").open(newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), [dict(r) for r in reader]


def render(model: str, interp: Interpreter | None = None) -> str:
    interp = interp or Interpreter(DEFAULT_MODELS_DIR, DEFAULT_DATA_DIR)
    mod = interp.load(DEFAULT_MODELS_DIR / f"{model}.quill")
    case_cols, cases = read_cases(model)
    out_cols: list[str] | None = None
    rows: list[list[str]] = []
    for case in cases:
        result = interp.run(mod, "run", dict(case))
        if not isinstance(result, dict):
            raise QuillError(f"{model}: run() must return a record (case {case.get('case_id')})")
        if out_cols is None:
            out_cols = list(result.keys())
        elif list(result.keys()) != out_cols:
            raise QuillError(f"{model}: inconsistent output fields in case {case.get('case_id')}")
        rows.append([case[c] for c in case_cols] + [format_value(result[c]) for c in out_cols])
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(case_cols + (out_cols or []))
    w.writerows(rows)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="compare with committed files only")
    ap.add_argument("--model", action="append", help="run only this model (repeatable)")
    args = ap.parse_args(argv)
    models = args.model or model_names()
    interp = Interpreter(DEFAULT_MODELS_DIR, DEFAULT_DATA_DIR)
    failed = False
    for m in models:
        text = render(m, interp)
        target = REFERENCE_DIR / f"{m}.csv"
        n = text.count("\n") - 1
        if args.check:
            same = target.exists() and target.read_text() == text
            print(f"{'OK  ' if same else 'DIFF'} {m:<26} {n} cases")
            failed |= not same
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            print(f"wrote {target.relative_to(REPO_ROOT)} ({n} cases)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
