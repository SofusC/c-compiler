import re
from enum import Enum, auto
from dataclasses import dataclass

TOKENS = [
        ("RETURN",      r"return\b"),
        ("VOID",        r"void\b"),
        ("INT",         r"int\b"),
        ("CONSTANT",    r"[0-9]+\b"),
        ("IDENTIFIER",  r"[a-zA-Z_]\w*\b"),
        ("OPEN_PAREN",  r"\("),
        ("CLOSE_PAREN", r"\)"),
        ("OPEN_BRACE",  r"{"),
        ("CLOSE_BRACE", r"}"),
        ("SEMICOLON",   r";"),

        ("TILDE",       r"~"),
        ("NEGATION",    r"-"),
        ("DECREMENT",   r"--"),

        ("MISMATCH",    r"\S+"),
        ]

PATTERN = re.compile("|".join(f"(?P<{name}>{pattern})" for name,pattern in TOKENS))

class TokenType(Enum):
    RETURN = auto()
    VOID = auto()
    INT = auto()
    CONSTANT = auto()
    IDENTIFIER = auto()
    OPEN_PAREN = auto()
    CLOSE_PAREN = auto()
    OPEN_BRACE = auto()
    CLOSE_BRACE = auto()
    SEMICOLON = auto()

    TILDE = auto()
    NEGATION = auto()
    DECREMENT = auto()

    MISMATCH = auto()

@dataclass
class Token:
    token_type: TokenType
    value: any = None

    def __str__(self):
        if self.value:
            return f"Token of type {self.token_type} with value {self.value}"
        else:
            return f"Token of type {self.token_type}"


def lex(file):
    result = []
    with open(file, "r") as f:
        code = f.read()
        for mo in re.finditer(PATTERN, code):
            token = mo.lastgroup
            match token:
                case "MISMATCH":
                    raise RuntimeError(f"Unexpected token {mo.group()}")
                case "IDENTIFIER" | "CONSTANT":
                    value = mo.group()
                    result.append(Token(TokenType[token],value))
                case _:
                    result.append(Token(TokenType[token]))
    return result
