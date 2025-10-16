import re
from enum import Enum
from dataclasses import dataclass

class TokenType(Enum):
    RETURN                  = r"return\b"
    IF                      = r"if\b"
    ELSE                    = r"else\b"
    DO                      = r"do\b"
    WHILE                   = r"while\b"
    FOR                     = r"for\b"
    BREAK                   = r"break\b"
    CONTINUE                = r"continue\b"

    STATIC                  = r"static\b"
    EXTERN                  = r"extern\b"

    VOID                    = r"void\b"
    INT                     = r"int\b"
    LONG                    = r"long\b"
    SIGNED                  = r"signed\b"
    UNSIGNED                = r"unsigned\b"

    CONSTANT                = r"[0-9]+\b"
    LONG_CONSTANT           = r"[0-9]+[lL]\b"
    UNSIGNED_INT_CONSTANT   = r"[0-9]+[uU]\b"
    UNSIGNED_LONG_CONSTANT  = r"[0-9]+([uU][lL]|[lL][uU])\b"

    IDENTIFIER              = r"[a-zA-Z_]\w*\b"

    OPEN_PAREN              = r"\("
    CLOSE_PAREN             = r"\)"
    OPEN_BRACE              = r"{"
    CLOSE_BRACE             = r"}"
    SEMICOLON               = r";"

    TILDE                   = r"~"
    DECREMENT               = r"--"
    HYPHEN                  = r"-"

    PLUS                    = r"\+"
    ASTERISK                = r"\*"
    FORWARD_SLASH           = r"/"
    PERCENT_SIGN            = r"%"

    TWO_EQUAL_SIGNS         = r"=="
    EXCLAM_POINT_EQUAL      = r"!="
    EXCLAMATION_POINT       = r"!"
    TWO_AMPERSANDS          = r"&&"
    TWO_VERT_BARS           = r"\|\|"
    LESS_THAN_OR_EQ         = r"<="
    LESS_THAN               = r"<"
    GREATER_THAN_OR_EQ      = r">="
    GREATER_THAN            = r">"

    EQUAL_SIGN              = r"="

    QUESTION_MARK           = r"\?"
    COLON                   = r":"

    COMMA                   = r","

    MISMATCH                = r"\S+"


PATTERN = re.compile("|".join(f"(?P<{tt.name}>{tt.value})" for tt in list(TokenType)))

@dataclass
class Token:
    token_type: TokenType
    value: str | int | None = None

    def __str__(self):
        if self.value:
            return f"Token of type {self.token_type.name} with value {self.value}"
        else:
            return f"Token of type {self.token_type.name}"


def lex(file):
    result = []
    with open(file, "r") as f:
        code = f.read()
        for mo in re.finditer(PATTERN, code):
            token = mo.lastgroup
            match token:
                case TokenType.MISMATCH.name:
                    raise RuntimeError(f"Unexpected token {mo.group()}")
                case TokenType.IDENTIFIER.name | TokenType.CONSTANT.name:
                    value = mo.group()
                    result.append(Token(TokenType[token], value))
                case TokenType.LONG_CONSTANT.name:
                    value = mo.group()[:-1]
                    result.append(Token(TokenType[token], value))
                case _:
                    result.append(Token(TokenType[token]))
    return result
