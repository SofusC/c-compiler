import assembly_ast as asm_ast
from abc import ABC, abstractmethod
from lexer import TokenType

class ASTNode(ABC):
    @abstractmethod
    def generate(self):
        pass

class Program(ASTNode):
    def __init__(self, tokens):
        self.function = Function(tokens)
        if len(tokens) != 0:
            raise RuntimeError(f"Syntax error, tokens left: {[token for token in tokens]}")

    def generate(self):
        return asm_ast.asm_program(self.function.generate())

    def __str__(self):
        return f"""\
Program(
    {self.function}
)"""

class Function(ASTNode):
    def __init__(self, tokens):
        expect(TokenType.INT, tokens)
        self.name = expect(TokenType.IDENTIFIER,tokens)
        expect(TokenType.OPEN_PAREN, tokens)
        expect(TokenType.VOID, tokens)
        expect(TokenType.CLOSE_PAREN, tokens)
        expect(TokenType.OPEN_BRACE, tokens)
        self.body = Statement(tokens)
        expect(TokenType.CLOSE_BRACE, tokens)

    def generate(self):
        return asm_ast.asm_function(self.name.value, self.body.generate())

    def __str__(self):
        return f"""\
Function(
        name='{self.name.value}',
        body={self.body}
    )"""
    

class Statement(ASTNode):
    def __init__(self, tokens):
        expect(TokenType.RETURN, tokens)
        self.exp = Exp(tokens)
        expect(TokenType.SEMICOLON, tokens)

    def generate(self):
        return [asm_ast.asm_mov(self.exp.generate(), asm_ast.asm_register()), asm_ast.asm_ret()]

    def __str__(self):
        return f"""\
Return(
        {self.exp}
             )"""

class Exp(ASTNode):
    def __init__(self, tokens):
        self.constant = expect(TokenType.CONSTANT, tokens)

    def generate(self):
        return asm_ast.asm_imm(self.constant.value)

    def __str__(self):
        return f"\tConstant({self.constant.value})"

def expect(expected, tokens):
    actual = tokens.pop(0)
    if actual.token_type != expected:
        raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
    return actual
