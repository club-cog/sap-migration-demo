"""Tree-walking interpreter for Quill (emulates the legacy RiskDB engine)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, DivisionByZero, InvalidOperation
from pathlib import Path
from typing import Any

from . import ast as A
from .builtins import Namespace, Table, _eq, make_builtins, type_name
from .errors import QuillError
from .parser import parse

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS_DIR = REPO_ROOT / "legacy" / "models"
DEFAULT_DATA_DIR = REPO_ROOT / "legacy" / "data"


class Function:
    def __init__(self, defn: A.Defn, module: "Module"):
        self.defn = defn
        self.module = module

    def __repr__(self) -> str:
        return f"<defn {self.module.name}.{self.defn.name}>"


class Module:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.globals: dict[str, Any] = {}
        self.cells: set[str] = set()

    def get(self, attr: str) -> Any:
        if attr not in self.globals:
            raise QuillError(f"{self.name} has no member {attr!r}", self.path.name)
        return self.globals[attr]


class _Return(Exception):
    def __init__(self, value: Any):
        self.value = value


def format_value(v: Any) -> str:
    """Canonical text form used for STR() and for reference output files."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Decimal):
        if v == 0:
            return "0"
        return format(v.normalize(), "f")
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "[" + ", ".join(format_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {format_value(x)}" for k, x in v.items()) + "}"
    return repr(v)


class Interpreter:
    def __init__(self, models_dir: Path | str = DEFAULT_MODELS_DIR,
                 data_dir: Path | str = DEFAULT_DATA_DIR):
        self.models_dir = Path(models_dir)
        self.data_dir = Path(data_dir)
        self.builtins = make_builtins(self.data_dir)
        self.modules: dict[Path, Module] = {}
        self._loading: set[Path] = set()
        self._file = "<string>"

    # -- loading ---------------------------------------------------------------
    def load(self, path: Path | str, base: Path | None = None) -> Module:
        p = Path(path)
        if not p.is_absolute():
            candidates = ([base / p] if base else []) + [self.models_dir / p]
            p = next((c for c in candidates if c.exists()), candidates[-1])
        p = p.resolve()
        if p in self.modules:
            return self.modules[p]
        if p in self._loading:
            raise QuillError("circular use", p.name)
        if not p.exists():
            raise QuillError(f"cannot find module {str(path)!r}")
        self._loading.add(p)
        try:
            mod = self._load_source(p.read_text(), p.stem, p)
        finally:
            self._loading.discard(p)
        self.modules[p] = mod
        return mod

    def load_string(self, src: str, name: str = "main") -> Module:
        return self._load_source(src, name, self.models_dir / f"{name}.quill")

    def _load_source(self, src: str, name: str, path: Path) -> Module:
        prog = parse(src, path.name)
        mod = Module(name, path)
        for item in prog.items:
            if isinstance(item, A.Defn):
                if item.name in mod.globals:
                    raise QuillError(f"duplicate definition {item.name!r}", path.name, item.line)
                mod.globals[item.name] = Function(item, mod)
        for item in prog.items:
            prev = self._file
            self._file = path.name
            try:
                if isinstance(item, A.Use):
                    mod.globals[item.alias] = self.load(item.path, base=path.parent)
                elif isinstance(item, A.Cell):
                    if item.name in mod.globals:
                        raise QuillError(f"duplicate definition {item.name!r}", path.name,
                                         item.line)
                    mod.globals[item.name] = self.eval(item.expr, {}, mod)
                    mod.cells.add(item.name)
            except QuillError as e:
                if e.file is None:
                    raise QuillError(e.message, path.name, item.line) from None
                raise
            finally:
                self._file = prev
        return mod

    # -- calling ---------------------------------------------------------------
    def call(self, fn: Any, args: list[Any], line: int | None = None) -> Any:
        if isinstance(fn, Function):
            params = fn.defn.params
            if len(args) != len(params):
                raise QuillError(
                    f"{fn.defn.name}() takes {len(params)} argument(s), got {len(args)}",
                    self._file, line)
            local = dict(zip(params, args))
            prev = self._file
            self._file = fn.module.path.name
            try:
                self.exec_block(fn.defn.body, local, fn.module)
            except _Return as r:
                return r.value
            finally:
                self._file = prev
            return None
        if callable(fn):
            try:
                return fn(*args)
            except QuillError as e:
                if e.file is None:
                    raise QuillError(e.message, self._file, line) from None
                raise
            except TypeError as e:
                raise QuillError(f"bad builtin call: {e}", self._file, line) from None
        raise QuillError(f"{type_name(fn)} is not callable", self._file, line)

    def run(self, module: Module, fn_name: str, *args: Any) -> Any:
        return self.call(module.get(fn_name), list(args))

    # -- statements ------------------------------------------------------------
    def exec_block(self, stmts: list[A.Node], env: dict[str, Any], mod: Module) -> None:
        for s in stmts:
            self.exec(s, env, mod)

    def exec(self, s: A.Node, env: dict[str, Any], mod: Module) -> None:
        try:
            self._exec(s, env, mod)
        except QuillError as e:
            if e.line is None:
                raise QuillError(e.message, self._file, s.line) from None
            raise
        except (DivisionByZero, InvalidOperation, ZeroDivisionError):
            raise QuillError("arithmetic error (division by zero?)", self._file, s.line) from None

    def _exec(self, s: A.Node, env: dict[str, Any], mod: Module) -> None:
        if isinstance(s, A.Let):
            env[s.name] = self.eval(s.expr, env, mod)
        elif isinstance(s, A.Set):
            self.assign(s.target, self.eval(s.expr, env, mod), env, mod)
        elif isinstance(s, A.If):
            for cond, body in s.branches:
                if self.truth(self.eval(cond, env, mod)):
                    self.exec_block(body, env, mod)
                    return
            if s.orelse is not None:
                self.exec_block(s.orelse, env, mod)
        elif isinstance(s, A.ForIn):
            seq = self.eval(s.iterable, env, mod)
            if isinstance(seq, dict):
                seq = list(seq.keys())
            if not isinstance(seq, list):
                raise QuillError(f"for..in expects a list, got {type_name(seq)}")
            for item in list(seq):
                env[s.var] = item
                self.exec_block(s.body, env, mod)
        elif isinstance(s, A.ForRange):
            i = self.num(self.eval(s.start, env, mod))
            stop = self.num(self.eval(s.stop, env, mod))
            step = self.num(self.eval(s.step, env, mod)) if s.step else Decimal(1)
            if step == 0:
                raise QuillError("for: step must not be 0")
            while (i <= stop) if step > 0 else (i >= stop):
                env[s.var] = i
                self.exec_block(s.body, env, mod)
                i += step
        elif isinstance(s, A.While):
            guard = 0
            while self.truth(self.eval(s.cond, env, mod)):
                self.exec_block(s.body, env, mod)
                guard += 1
                if guard > 1_000_000:
                    raise QuillError("while: iteration limit exceeded")
        elif isinstance(s, A.Return):
            raise _Return(None if s.expr is None else self.eval(s.expr, env, mod))
        elif isinstance(s, A.ExprStmt):
            self.eval(s.expr, env, mod)
        else:
            raise QuillError(f"unknown statement {type(s).__name__}")

    def assign(self, target: A.Node, value: Any, env: dict[str, Any], mod: Module) -> None:
        if isinstance(target, A.Name):
            if target.ident in env:
                env[target.ident] = value
            elif target.ident in mod.cells:
                raise QuillError(f"cell {target.ident!r} is read-only")
            else:
                raise QuillError(f"set of undeclared name {target.ident!r} (use let)")
        elif isinstance(target, A.Field):
            obj = self.eval(target.target, env, mod)
            if not isinstance(obj, dict):
                raise QuillError(f"cannot set field on {type_name(obj)}")
            obj[target.name] = value
        elif isinstance(target, A.Index):
            obj = self.eval(target.target, env, mod)
            idx = self.eval(target.index, env, mod)
            if isinstance(obj, list):
                obj[self.list_pos(obj, idx)] = value
            elif isinstance(obj, dict):
                obj[self.key(idx)] = value
            else:
                raise QuillError(f"cannot index {type_name(obj)}")

    # -- expressions -----------------------------------------------------------
    def eval(self, e: A.Node, env: dict[str, Any], mod: Module) -> Any:
        if isinstance(e, A.Literal):
            return e.value
        if isinstance(e, A.Name):
            if e.ident in env:
                return env[e.ident]
            if e.ident in mod.globals:
                return mod.globals[e.ident]
            if e.ident in self.builtins:
                return self.builtins[e.ident]
            raise QuillError(f"undefined name {e.ident!r}", self._file, e.line)
        if isinstance(e, A.ListExpr):
            return [self.eval(x, env, mod) for x in e.items]
        if isinstance(e, A.RecordExpr):
            return {k: self.eval(v, env, mod) for k, v in e.fields}
        if isinstance(e, A.Field):
            obj = self.eval(e.target, env, mod)
            if isinstance(obj, (Module, Namespace)):
                return obj.get(e.name)
            if isinstance(obj, dict):
                return obj.get(e.name)
            raise QuillError(f"cannot read field {e.name!r} of {type_name(obj)}", self._file,
                             e.line)
        if isinstance(e, A.Index):
            obj = self.eval(e.target, env, mod)
            idx = self.eval(e.index, env, mod)
            if isinstance(obj, list):
                return obj[self.list_pos(obj, idx)]
            if isinstance(obj, dict):
                return obj.get(self.key(idx))
            raise QuillError(f"cannot index {type_name(obj)}", self._file, e.line)
        if isinstance(e, A.Call):
            fn = self.eval(e.callee, env, mod)
            args = [self.eval(a, env, mod) for a in e.args]
            return self.call(fn, args, e.line)
        if isinstance(e, A.Unary):
            v = self.eval(e.operand, env, mod)
            if e.op == "-":
                return -self.num(v)
            return not self.truth(v)
        if isinstance(e, A.Binary):
            return self.binary(e, env, mod)
        raise QuillError(f"unknown expression {type(e).__name__}", self._file, e.line)

    def binary(self, e: A.Binary, env: dict[str, Any], mod: Module) -> Any:
        op = e.op
        if op == "and":
            return self.truth(self.eval(e.left, env, mod)) and self.truth(
                self.eval(e.right, env, mod))
        if op == "or":
            return self.truth(self.eval(e.left, env, mod)) or self.truth(
                self.eval(e.right, env, mod))
        a = self.eval(e.left, env, mod)
        b = self.eval(e.right, env, mod)
        if op == "==":
            return _eq(a, b)
        if op == "!=":
            return not _eq(a, b)
        if op == "&":
            return format_value(a) + format_value(b)
        if op in ("<", "<=", ">", ">="):
            if type_name(a) != type_name(b) or type_name(a) not in ("number", "date", "string"):
                raise QuillError(f"cannot compare {type_name(a)} and {type_name(b)}")
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        a, b = self.num(a), self.num(b)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise QuillError("division by zero")
            return a / b
        if op == "mod":
            if b == 0:
                raise QuillError("division by zero")
            return a % b
        if op == "^":
            return a ** b
        raise QuillError(f"unknown operator {op}")

    # -- helpers ---------------------------------------------------------------
    @staticmethod
    def num(v: Any) -> Decimal:
        if not isinstance(v, Decimal) or isinstance(v, bool):
            raise QuillError(f"expected number, got {type_name(v)}")
        return v

    @staticmethod
    def truth(v: Any) -> bool:
        if not isinstance(v, bool):
            raise QuillError(f"condition must be true/false, got {type_name(v)}")
        return v

    @staticmethod
    def list_pos(lst: list, idx: Any) -> int:
        if not isinstance(idx, Decimal) or idx != idx.to_integral_value():
            raise QuillError("list index must be a whole number")
        i = int(idx)
        if i < 1 or i > len(lst):
            raise QuillError(f"index {i} out of range 1..{len(lst)} (lists are 1-indexed)")
        return i - 1

    @staticmethod
    def key(idx: Any) -> str:
        if not isinstance(idx, str):
            raise QuillError("record key must be a string")
        return idx


__all__ = ["Interpreter", "Module", "Function", "Table", "format_value"]
