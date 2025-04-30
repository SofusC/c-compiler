import assembly_ast as asm_ast
from abc import ABC, abstractmethod
from lexer import TokenType

class ASTNode(ABC):
    @abstractmethod
    def generate(self):
        pass

class Program(ASTNode):
    def __init__(self,_function):
        self.function = _function

    def generate(self):
        return asm_ast.asm_program(self.function.generate())

    def __str__(self):
        return f"""\
Program(
    {self.function}
)"""

class Function(ASTNode):
    def __init__(self,_name,_body):
        self.name = _name
        self.body = _body

    def generate(self):
        return asm_ast.asm_function(self.name.value, self.body.generate())

    def __str__(self):
        return f"""\
Function(
        name='{self.name.value}',
        body={self.body}
    )"""
    

class Statement(ASTNode):
    def __init__(self,_exp):
        self.exp = _exp

    def generate(self):
        return [asm_ast.asm_mov(self.exp.generate(), asm_ast.asm_register()), asm_ast.asm_ret()]

    def __str__(self):
        return f"""\
Return(
        {self.exp}
             )"""

class Exp(ASTNode):
    def __init__(self,_constant):
        self.constant = _constant

    def generate(self):
        return asm_ast.asm_imm(self.constant.value)

    def __str__(self):
        return f"\tConstant({self.constant.value})"

def parse(tokens):
    ast = Program(parse_function(tokens))
    if len(tokens) != 0:
        raise RuntimeError(f"Syntax error, tokens left: {[token for token in tokens]}")
    return ast

def parse_function(tokens):
    expect(TokenType.INT, tokens)
    identifier = expect(TokenType.IDENTIFIER,tokens)
    expect(TokenType.OPEN_PAREN, tokens)
    expect(TokenType.VOID, tokens)
    expect(TokenType.CLOSE_PAREN, tokens)
    expect(TokenType.OPEN_BRACE, tokens)
    statement = parse_statement(tokens)
    expect(TokenType.CLOSE_BRACE, tokens)
    return Function(identifier, statement)

def parse_statement(tokens):
    expect(TokenType.RETURN, tokens)
    exp = parse_exp(tokens)
    expect(TokenType.SEMICOLON, tokens)
    return Statement(exp)

def parse_exp(tokens):
    constant = expect(TokenType.CONSTANT, tokens)
    return Exp(constant)


def expect(expected, tokens):
    actual = tokens.pop(0)
    if actual.token_type != expected:
        raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
    return actual
