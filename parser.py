class asm_program():
    def __init__(self, _function_definition):
        self.function_definition = _function_definition

    def pretty(self, indent = 0):
        print(" " * indent + "Program(")
        self.function_definition.pretty(indent + 1)
        print(" " * indent + ")")

class asm_function():
    def __init__(self, _name, _instructions):
        self.name = _name
        self.instructions = _instructions

    def pretty(self, indent = 0):
        print(" " * indent + "Function(")
        print(" " * (indent + 1) + f"name={self.name}")
        print(" " * (indent + 1) + f"instructions:")
        for ins in self.instructions:
            ins.pretty(indent+2)
        print(" " * indent + ")")

class asm_mov():
    def __init__(self, _src, _dst):
        self.src = _src
        self.dst = _dst

    def pretty(self, indent = 0):
        print(" " * indent + f"Mov({self.src}, {self.dst})")

class asm_ret():
    def pretty(self, indent = 0):
        print(" " * indent + f"Ret")

class asm_register():
    def __str__(self):
        return f"Register"

class asm_imm():
    def __init__(self, _int):
        self.int = _int

    def __str__(self):
        return f"Imm({self.int})"

class Program_node():
    def __init__(self,_function):
        self.function = _function

    def generate(self):
        return asm_program(self.function.generate())

    def __str__(self):
        return f"""\
Program(
    {self.function}
)"""

class Function_node():
    def __init__(self,_identifier,_statement):
        self.identifier = _identifier
        self.statement = _statement

    def generate(self):
        return asm_function(self.identifier.value, self.statement.generate())

    def __str__(self):
        return f"""\
Function(
    name='{self.identifier.value}',
    body={self.statement}
)"""
    

class Statement_node():
    def __init__(self,_exp):
        self.exp = _exp

    def generate(self):
        return [asm_mov(self.exp.generate(), asm_register()), asm_ret()]

    def __str__(self):
        return f"""\
Return(
    {self.exp}
    )"""

class Int_node():
    def __init__(self,_constant):
        self.constant = _constant

    def generate(self):
        return asm_imm(self.constant.value)

    def __str__(self):
        return f"\tConstant({self.constant.value})"

def parse(tokens):
    ast = Program_node(parse_function(tokens))
    if len(tokens) != 0:
        raise RuntimeError(f"Syntax error, tokens left: {[token for token in tokens]}")
    return ast

def parse_function(tokens):
    expect("INT", tokens)
    identifier = expect("IDENTIFIER",tokens)
    expect("OPEN_PAREN", tokens)
    expect("VOID", tokens)
    expect("CLOSE_PAREN", tokens)
    expect("OPEN_BRACE", tokens)
    statement = parse_statement(tokens)
    expect("CLOSE_BRACE", tokens)
    return Function_node(identifier, statement)

def parse_statement(tokens):
    expect("RETURN", tokens)
    exp = parse_exp(tokens)
    expect("SEMICOLON", tokens)
    return Statement_node(exp)

def parse_exp(tokens):
    constant = expect("CONSTANT", tokens)
    return Int_node(constant)


def expect(expected, tokens):
    actual = tokens.pop(0)
    if actual.kind != expected:
        raise RuntimeError(f"Expected '{expected}' but found '{actual.kind}'")
    return actual
