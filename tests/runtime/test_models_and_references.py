"""Every legacy model loads, its libs resolve, and run_all reproduces the committed references."""

import pytest

from legacy.quill_runtime.interpreter import DEFAULT_MODELS_DIR
from legacy.quill_runtime.run_all import REFERENCE_DIR, model_names, read_cases, render

MODELS = model_names()


def test_ten_models():
    assert len(MODELS) == 10
    for m in MODELS:
        assert (DEFAULT_MODELS_DIR / f"{m}.quill").exists()


def test_lcr_uses_hqla_module(interp):
    lcr = interp.load(DEFAULT_MODELS_DIR / "lcr_outflows.quill")
    assert lcr.globals["hq"].name == "hqla_haircut"
    assert lcr.globals["rnd"].name == "rounding"


@pytest.mark.parametrize("model", MODELS)
def test_case_counts(model):
    _, cases = read_cases(model)
    assert 15 <= len(cases) <= 40
    assert len({c["as_of"] for c in cases}) >= 3


@pytest.mark.parametrize("model", MODELS)
def test_reference_output_is_reproducible(model, interp):
    committed = (REFERENCE_DIR / f"{model}.csv").read_text()
    assert render(model, interp) == committed, (
        f"{model}: regenerated output differs from legacy/reference_outputs/{model}.csv")


def test_margin_call_has_three_weekend_cases():
    import datetime as dt

    _, cases = read_cases("collateral_margin_call")
    weekend = [c["case_id"] for c in cases if dt.date.fromisoformat(c["as_of"]).weekday() >= 5]
    assert len(weekend) == 3


def test_single_case_cli(capsys):
    from legacy.quill_runtime.__main__ import main

    assert main(["lcr_outflows", "LCR-002"]) == 0
    assert "lcr" in capsys.readouterr().out
