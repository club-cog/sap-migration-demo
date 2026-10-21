"""Core Quill language semantics: arithmetic, control flow, records, 1-indexed lists."""

from decimal import Decimal

import pytest

from legacy.quill_runtime import QuillError


def test_decimal_arithmetic_is_exact(q):
    assert q("defn main()\n  return 0.1 + 0.2\nenddefn\n") == Decimal("0.3")


def test_operator_precedence(q):
    src = "defn main()\n  return 2 + 3 * 4 ^ 2 - 10 / 4\nenddefn\n"
    assert q(src) == Decimal("47.5")


def test_mod_and_unary_minus(q):
    assert q("defn main()\n  return -7 mod 3\nenddefn\n") == Decimal("-1")


def test_if_elif_else(q):
    src = """
defn main(x)
  if x < 0 then
    return "neg"
  elif x == 0 then
    return "zero"
  else
    return "pos"
  endif
enddefn
"""
    assert [q(src, "main", Decimal(v)) for v in (-1, 0, 5)] == ["neg", "zero", "pos"]


def test_lists_are_one_indexed(q):
    src = "defn main()\n  let xs = [10, 20, 30]\n  return xs[1] + xs[3]\nenddefn\n"
    assert q(src) == Decimal(40)


def test_index_zero_is_an_error(q):
    with pytest.raises(QuillError, match="1-indexed|out of range"):
        q("defn main()\n  let xs = [1]\n  return xs[0]\nenddefn\n")


def test_for_in_and_for_range(q):
    src = """
defn main()
  let t = 0
  for x in [1, 2, 3] do
    set t = t + x
  endfor
  for i = 10 to 1 step -3 do
    set t = t + i
  endfor
  return t
enddefn
"""
    assert q(src) == Decimal(6 + 10 + 7 + 4 + 1)


def test_while_loop(q):
    src = "defn main()\n  let n = 1\n  while n < 100 do\n    set n = n * 2\n  endwhile\n  return n\nenddefn\n"
    assert q(src) == Decimal(128)


def test_records_and_nested_set(q):
    src = """
defn main()
  let r = {a: 1, b: {c: [1, 2]}}
  set r.a = 5
  set r.b.c[2] = 9
  set r["d"] = "x"
  return r
enddefn
"""
    assert q(src) == {"a": Decimal(5), "b": {"c": [Decimal(1), Decimal(9)]}, "d": "x"}


def test_for_over_record_iterates_keys_in_order(q):
    src = 'defn main()\n  let s = ""\n  for k in {z: 1, a: 2} do\n    set s = s & k\n  endfor\n  return s\nenddefn\n'
    assert q(src) == "za"


def test_cells_are_read_only(q):
    with pytest.raises(QuillError):
        q("cell LIMIT = 5\ndefn main()\n  set LIMIT = 6\n  return LIMIT\nenddefn\n")


def test_cells_visible_in_functions(q):
    assert q("cell K = 3\ndefn main()\n  return K * 2\nenddefn\n") == Decimal(6)


def test_and_or_short_circuit(q):
    src = "defn main(xs)\n  return LEN(xs) > 0 and xs[1] == 1\nenddefn\n"
    assert q(src, "main", []) is False


def test_nil_and_isnil(q):
    assert q("defn main()\n  return ISNIL(nil) and not ISNIL(0)\nenddefn\n") is True


def test_string_concat_formats_numbers(q):
    assert q('defn main()\n  return "v=" & 1.50\nenddefn\n') == "v=1.5"


def test_comments_are_ignored(q):
    assert q(";; header\ndefn main() ;; trailing\n  return 1 ;; x\nenddefn\n") == Decimal(1)


def test_undefined_name_reports_line(q):
    with pytest.raises(QuillError, match=r"snippet.quill:2"):
        q("defn main()\n  return nope\nenddefn\n")


def test_parse_error_on_missing_endif(q):
    with pytest.raises(QuillError):
        q("defn main()\n  if true then\n    return 1\nenddefn\n")


def test_recursion(q):
    src = """
defn fact(n)
  if n <= 1 then
    return 1
  endif
  return n * fact(n - 1)
enddefn
"""
    assert q(src, "fact", Decimal(10)) == Decimal(3628800)
