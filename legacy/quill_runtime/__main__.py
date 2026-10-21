"""Run one Quill model for one case and print the result.

    python -m legacy.quill_runtime lcr_outflows LCR-007
"""

from __future__ import annotations

import sys

from .interpreter import DEFAULT_MODELS_DIR, Interpreter, format_value
from .run_all import read_cases


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    model, case_id = argv
    _, cases = read_cases(model)
    case = next((c for c in cases if c["case_id"] == case_id), None)
    if case is None:
        print(f"no case {case_id} for {model}")
        return 2
    interp = Interpreter()
    result = interp.run(interp.load(DEFAULT_MODELS_DIR / f"{model}.quill"), "run", dict(case))
    for k, v in result.items():
        print(f"{k:<24} {format_value(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
