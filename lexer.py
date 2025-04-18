import re

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
        ("MISMATCH",    r"\S+"),
        ]

PATTERN = re.compile("|".join(f"(?P<{name}>{pattern})" for name,pattern in TOKENS))

class Token:
    def __init__(self, _kind, _value = None):
        self.kind = _kind
        self.value = _value

    def __str__(self):
        if self.value:
            return f"Token of type {self.kind} with value {self.value}"
        else:
            return f"Token of type {self.kind}"



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
                    result.append(Token(token,value))
                case _:
                    result.append(Token(token))
    return result
