"""Tokenizer for Quill source files.

Comments start with ``;;`` and run to end of line. Statements end at a newline.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import QuillError

KEYWORDS = {
    "defn", "enddefn", "cell", "let", "set", "if", "then", "elif", "else", "endif",
    "for", "in", "to", "step", "do", "endfor", "while", "endwhile", "return",
    "and", "or", "not", "mod", "true", "false", "nil", "use", "as",
}

OPERATORS = ["==", "!=", "<=", ">=", "<", ">", "=", "+", "-", "*", "/", "^", "&",
             "(", ")", "[", "]", "{", "}", ",", ".", ":"]


@dataclass(frozen=True)
class Token:
    kind: str  # NUM STR NAME KW OP NL EOF
    value: str
    line: int


def tokenize(src: str, file: str = "<string>") -> list[Token]:
    tokens: list[Token] = []
    i, line, n = 0, 1, len(src)
    depth = 0  # newlines inside (), [] and {} are ignored
    while i < n:
        c = src[i]
        if c == "\n":
            if depth == 0:
                tokens.append(Token("NL", "\n", line))
            line += 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif src.startswith(";;", i):
            while i < n and src[i] != "\n":
                i += 1
        elif c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j < n and src[j] == "." and j + 1 < n and src[j + 1].isdigit():
                j += 1
                while j < n and src[j].isdigit():
                    j += 1
            tokens.append(Token("NUM", src[i:j], line))
            i = j
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            word = src[i:j]
            tokens.append(Token("KW" if word in KEYWORDS else "NAME", word, line))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\n":
                    raise QuillError("unterminated string", file, line)
                j += 1
            if j >= n:
                raise QuillError("unterminated string", file, line)
            tokens.append(Token("STR", src[i + 1:j], line))
            i = j + 1
        else:
            for op in OPERATORS:
                if src.startswith(op, i):
                    if op in "([{":
                        depth += 1
                    elif op in ")]}":
                        depth = max(0, depth - 1)
                    tokens.append(Token("OP", op, line))
                    i += len(op)
                    break
            else:
                raise QuillError(f"unexpected character {c!r}", file, line)
    tokens.append(Token("NL", "\n", line))
    tokens.append(Token("EOF", "", line))
    return tokens
