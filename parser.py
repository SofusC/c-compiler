import assembly_ast as asm_ast
from abc import ABC, abstractmethod

class AST(ABC):
    @abstractmethod
    def generate(self):
        pass

class ProgramNode(AST):
    def __init__(self,_function):
        self.function = _function

    def generate(self):
        return asm_ast.asm_program(self.function.generate())

    def __str__(self):
        return f"""\
Program(
    {self.function}
)"""

class FunctionNode(AST):
    def __init__(self,_identifier,_statement):
        self.identifier = _identifier
        self.statement = _statement

    def generate(self):
        return asm_ast.asm_function(self.identifier.value, self.statement.generate())

    def __str__(self):
        return f"""\
Function(
    name='{self.identifier.value}',
    body={self.statement}
)"""
    

class StatementNode(AST):
    def __init__(self,_exp):
        self.exp = _exp

    def generate(self):
        return [asm_ast.asm_mov(self.exp.generate(), asm_ast.asm_register()), asm_ast.asm_ret()]

    def __str__(self):
        return f"""\
Return(
    {self.exp}
    )"""

class IntNode(AST):
    def __init__(self,_constant):
        self.constant = _constant

    def generate(self):
        return asm_ast.asm_imm(self.constant.value)

    def __str__(self):
        return f"\tConstant({self.constant.value})"

def parse(tokens):
    ast = ProgramNode(parse_function(tokens))
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
    return FunctionNode(identifier, statement)

def parse_statement(tokens):
    expect("RETURN", tokens)
    exp = parse_exp(tokens)
    expect("SEMICOLON", tokens)
    return StatementNode(exp)

def parse_exp(tokens):
    constant = expect("CONSTANT", tokens)
    return IntNode(constant)


def expect(expected, tokens):
    actual = tokens.pop(0)
    if actual.kind != expected:
        raise RuntimeError(f"Expected '{expected}' but found '{actual.kind}'")
    return actual
