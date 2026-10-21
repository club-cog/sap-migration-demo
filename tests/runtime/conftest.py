import pytest

from legacy.quill_runtime import Interpreter
from legacy.quill_runtime.interpreter import DEFAULT_DATA_DIR, DEFAULT_MODELS_DIR


@pytest.fixture
def interp():
    return Interpreter(DEFAULT_MODELS_DIR, DEFAULT_DATA_DIR)


@pytest.fixture
def q(interp):
    """Evaluate a Quill snippet: q(src) loads it, q(src, "fn", args...) calls a defn."""

    def _run(src, fn="main", *args):
        mod = interp.load_string(src, "snippet")
        return interp.run(mod, fn, *args)

    return _run
