"""AST node types for Quill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    line: int


# ---- expressions -------------------------------------------------------------
@dataclass
class Literal(Node):
    value: Any


@dataclass
class Name(Node):
    ident: str


@dataclass
class ListExpr(Node):
    items: list[Node]


@dataclass
class RecordExpr(Node):
    fields: list[tuple[str, Node]]


@dataclass
class Unary(Node):
    op: str
    operand: Node


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Field(Node):
    target: Node
    name: str


@dataclass
class Index(Node):
    target: Node
    index: Node


@dataclass
class Call(Node):
    callee: Node
    args: list[Node]


# ---- statements --------------------------------------------------------------
@dataclass
class Let(Node):
    name: str
    expr: Node


@dataclass
class Set(Node):
    target: Node
    expr: Node


@dataclass
class If(Node):
    branches: list[tuple[Node, list[Node]]]
    orelse: list[Node] | None


@dataclass
class ForIn(Node):
    var: str
    iterable: Node
    body: list[Node]


@dataclass
class ForRange(Node):
    var: str
    start: Node
    stop: Node
    step: Node | None
    body: list[Node]


@dataclass
class While(Node):
    cond: Node
    body: list[Node]


@dataclass
class Return(Node):
    expr: Node | None


@dataclass
class ExprStmt(Node):
    expr: Node


# ---- top level ---------------------------------------------------------------
@dataclass
class Use(Node):
    path: str
    alias: str


@dataclass
class Cell(Node):
    name: str
    expr: Node


@dataclass
class Defn(Node):
    name: str
    params: list[str]
    body: list[Node]


@dataclass
class Program(Node):
    items: list[Node] = field(default_factory=list)
