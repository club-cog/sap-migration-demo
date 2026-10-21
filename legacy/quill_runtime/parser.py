"""Recursive-descent parser for Quill.

Grammar (informal)::

    program  := { use | cell | defn }
    use      := 'use' STR 'as' NAME
    cell     := 'cell' NAME '=' expr
    defn     := 'defn' NAME '(' [NAME {',' NAME}] ')' block 'enddefn'
    stmt     := 'let' NAME '=' expr
              | 'set' target '=' expr
              | 'if' expr 'then' block {'elif' expr 'then' block} ['else' block] 'endif'
              | 'for' NAME 'in' expr 'do' block 'endfor'
              | 'for' NAME '=' expr 'to' expr ['step' expr] 'do' block 'endfor'
              | 'while' expr 'do' block 'endwhile'
              | 'return' [expr]
              | expr

Operator precedence, lowest first: or, and, not, comparison, &, + -, * / mod,
unary -, ^, postfix (call, index, field).
"""

from __future__ import annotations

from decimal import Decimal

from . import ast as A
from .errors import QuillError
from .lexer import Token, tokenize

COMPARISON = {"==", "!=", "<", "<=", ">", ">="}


class Parser:
    def __init__(self, tokens: list[Token], file: str):
        self.toks = tokens
        self.pos = 0
        self.file = file

    # -- helpers ---------------------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.toks[self.pos]

    def error(self, msg: str, tok: Token | None = None) -> QuillError:
        t = tok or self.tok
        return QuillError(msg, self.file, t.line)

    def at(self, kind: str, value: str | None = None) -> bool:
        t = self.tok
        return t.kind == kind and (value is None or t.value == value)

    def at_kw(self, *words: str) -> bool:
        return self.tok.kind == "KW" and self.tok.value in words

    def accept(self, kind: str, value: str | None = None) -> Token | None:
        if self.at(kind, value):
            t = self.tok
            self.pos += 1
            return t
        return None

    def expect(self, kind: str, value: str | None = None) -> Token:
        t = self.accept(kind, value)
        if t is None:
            want = value or kind
            got = self.tok.value if self.tok.kind != "NL" else "end of line"
            raise self.error(f"expected {want!r}, got {got!r}")
        return t

    def skip_newlines(self) -> None:
        while self.accept("NL"):
            pass

    def end_statement(self) -> None:
        if not self.at("EOF"):
            self.expect("NL")

    # -- top level -------------------------------------------------------------
    def parse_program(self) -> A.Program:
        prog = A.Program(line=1)
        self.skip_newlines()
        while not self.at("EOF"):
            t = self.tok
            if self.accept("KW", "use"):
                path = self.expect("STR").value
                self.expect("KW", "as")
                alias = self.expect("NAME").value
                prog.items.append(A.Use(t.line, path, alias))
            elif self.accept("KW", "cell"):
                name = self.expect("NAME").value
                self.expect("OP", "=")
                prog.items.append(A.Cell(t.line, name, self.expr()))
            elif self.accept("KW", "defn"):
                prog.items.append(self.defn(t))
                continue
            else:
                raise self.error("only 'use', 'cell' and 'defn' are allowed at top level")
            self.end_statement()
            self.skip_newlines()
        return prog

    def defn(self, start: Token) -> A.Defn:
        name = self.expect("NAME").value
        self.expect("OP", "(")
        params: list[str] = []
        if not self.at("OP", ")"):
            params.append(self.expect("NAME").value)
            while self.accept("OP", ","):
                params.append(self.expect("NAME").value)
        self.expect("OP", ")")
        body = self.block("enddefn")
        self.expect("KW", "enddefn")
        self.end_statement()
        self.skip_newlines()
        return A.Defn(start.line, name, params, body)

    def block(self, *terminators: str) -> list[A.Node]:
        self.expect("NL")
        stmts: list[A.Node] = []
        self.skip_newlines()
        while not self.at_kw(*terminators):
            if self.at("EOF"):
                raise self.error(f"missing {' / '.join(terminators)}")
            stmts.append(self.statement())
            self.skip_newlines()
        return stmts

    # -- statements ------------------------------------------------------------
    def statement(self) -> A.Node:
        t = self.tok
        if self.accept("KW", "let"):
            name = self.expect("NAME").value
            self.expect("OP", "=")
            node: A.Node = A.Let(t.line, name, self.expr())
        elif self.accept("KW", "set"):
            target = self.postfix()
            if not isinstance(target, (A.Name, A.Field, A.Index)):
                raise self.error("invalid set target", t)
            self.expect("OP", "=")
            node = A.Set(t.line, target, self.expr())
        elif self.accept("KW", "if"):
            branches = []
            cond = self.expr()
            self.expect("KW", "then")
            branches.append((cond, self.block("elif", "else", "endif")))
            orelse = None
            while self.accept("KW", "elif"):
                cond = self.expr()
                self.expect("KW", "then")
                branches.append((cond, self.block("elif", "else", "endif")))
            if self.accept("KW", "else"):
                orelse = self.block("endif")
            self.expect("KW", "endif")
            node = A.If(t.line, branches, orelse)
        elif self.accept("KW", "for"):
            var = self.expect("NAME").value
            if self.accept("KW", "in"):
                iterable = self.expr()
                self.expect("KW", "do")
                body = self.block("endfor")
                self.expect("KW", "endfor")
                node = A.ForIn(t.line, var, iterable, body)
            else:
                self.expect("OP", "=")
                start = self.expr()
                self.expect("KW", "to")
                stop = self.expr()
                step = self.expr() if self.accept("KW", "step") else None
                self.expect("KW", "do")
                body = self.block("endfor")
                self.expect("KW", "endfor")
                node = A.ForRange(t.line, var, start, stop, step, body)
        elif self.accept("KW", "while"):
            cond = self.expr()
            self.expect("KW", "do")
            body = self.block("endwhile")
            self.expect("KW", "endwhile")
            node = A.While(t.line, cond, body)
        elif self.accept("KW", "return"):
            expr = None if self.at("NL") else self.expr()
            node = A.Return(t.line, expr)
        else:
            node = A.ExprStmt(t.line, self.expr())
        self.end_statement()
        return node

    # -- expressions -----------------------------------------------------------
    def expr(self) -> A.Node:
        return self.or_expr()

    def or_expr(self) -> A.Node:
        left = self.and_expr()
        while (t := self.accept("KW", "or")):
            left = A.Binary(t.line, "or", left, self.and_expr())
        return left

    def and_expr(self) -> A.Node:
        left = self.not_expr()
        while (t := self.accept("KW", "and")):
            left = A.Binary(t.line, "and", left, self.not_expr())
        return left

    def not_expr(self) -> A.Node:
        if (t := self.accept("KW", "not")):
            return A.Unary(t.line, "not", self.not_expr())
        return self.comparison()

    def comparison(self) -> A.Node:
        left = self.concat()
        if self.tok.kind == "OP" and self.tok.value in COMPARISON:
            t = self.tok
            self.pos += 1
            left = A.Binary(t.line, t.value, left, self.concat())
            if self.tok.kind == "OP" and self.tok.value in COMPARISON:
                raise self.error("chained comparisons are not supported")
        return left

    def concat(self) -> A.Node:
        left = self.additive()
        while (t := self.accept("OP", "&")):
            left = A.Binary(t.line, "&", left, self.additive())
        return left

    def additive(self) -> A.Node:
        left = self.term()
        while self.tok.kind == "OP" and self.tok.value in ("+", "-"):
            t = self.tok
            self.pos += 1
            left = A.Binary(t.line, t.value, left, self.term())
        return left

    def term(self) -> A.Node:
        left = self.unary()
        while (self.tok.kind == "OP" and self.tok.value in ("*", "/")) or self.at("KW", "mod"):
            t = self.tok
            self.pos += 1
            left = A.Binary(t.line, t.value, left, self.unary())
        return left

    def unary(self) -> A.Node:
        if (t := self.accept("OP", "-")):
            return A.Unary(t.line, "-", self.unary())
        return self.power()

    def power(self) -> A.Node:
        base = self.postfix()
        if (t := self.accept("OP", "^")):
            return A.Binary(t.line, "^", base, self.unary())
        return base

    def postfix(self) -> A.Node:
        node = self.primary()
        while True:
            t = self.tok
            if self.accept("OP", "("):
                args: list[A.Node] = []
                if not self.at("OP", ")"):
                    args.append(self.expr())
                    while self.accept("OP", ","):
                        args.append(self.expr())
                self.expect("OP", ")")
                node = A.Call(t.line, node, args)
            elif self.accept("OP", "["):
                idx = self.expr()
                self.expect("OP", "]")
                node = A.Index(t.line, node, idx)
            elif self.accept("OP", "."):
                name = self.tok
                if name.kind not in ("NAME", "KW"):
                    raise self.error("expected field name after '.'")
                self.pos += 1
                node = A.Field(t.line, node, name.value)
            else:
                return node

    def primary(self) -> A.Node:
        t = self.tok
        if self.accept("NUM"):
            return A.Literal(t.line, Decimal(t.value))
        if self.accept("STR"):
            return A.Literal(t.line, t.value)
        if self.accept("KW", "true"):
            return A.Literal(t.line, True)
        if self.accept("KW", "false"):
            return A.Literal(t.line, False)
        if self.accept("KW", "nil"):
            return A.Literal(t.line, None)
        if self.accept("NAME"):
            return A.Name(t.line, t.value)
        if self.accept("OP", "("):
            e = self.expr()
            self.expect("OP", ")")
            return e
        if self.accept("OP", "["):
            items: list[A.Node] = []
            if not self.at("OP", "]"):
                items.append(self.expr())
                while self.accept("OP", ","):
                    items.append(self.expr())
            self.expect("OP", "]")
            return A.ListExpr(t.line, items)
        if self.accept("OP", "{"):
            fields: list[tuple[str, A.Node]] = []
            if not self.at("OP", "}"):
                fields.append(self.record_field())
                while self.accept("OP", ","):
                    fields.append(self.record_field())
            self.expect("OP", "}")
            return A.RecordExpr(t.line, fields)
        got = t.value if t.kind != "NL" else "end of line"
        raise self.error(f"unexpected {got!r}")

    def record_field(self) -> tuple[str, A.Node]:
        key = self.tok
        if key.kind not in ("NAME", "STR"):
            raise self.error("expected record key")
        self.pos += 1
        self.expect("OP", ":")
        return key.value, self.expr()


def parse(src: str, file: str = "<string>") -> A.Program:
    return Parser(tokenize(src, file), file).parse_program()
