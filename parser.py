import assembly_ast as asm_ast
from abc import ABC, abstractmethod
from lexer import TokenType

class ASTNode(ABC):
    @abstractmethod
    def generate(self):
        pass

class Program(ASTNode):
    def __init__(self, _function):
        self.function = _function

    def generate(self):
        return asm_ast.asm_program(self.function.generate())

    def __str__(self):
        return f"""\
Program(
    {self.function}
)"""

class FunctionDefinition(ASTNode):
    def __init__(self, _name, _body):
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
    pass

class Return(Statement):
    def __init__(self, _exp):
        self.exp = _exp

    def generate(self):
        return [asm_ast.asm_mov(self.exp.generate(), asm_ast.asm_register()), asm_ast.asm_ret()]

    def __str__(self):
        return f"""\
Return(
        {self.exp}
             )"""


class Exp(ASTNode):
    pass

class Constant(Exp):
    def __init__(self, _constant):
        self.constant = _constant

    def generate(self):
        return asm_ast.asm_imm(self.constant)

    def __str__(self):
        return f"\tConstant({self.constant})"
    
class Unary(Exp):
    def __init__(self, _unary_operator, _exp):
        self.unary_operator = _unary_operator
        self.exp = _exp

    def generate(self):
        pass
    
    def __str__(self):
        return f"""\
Unary(
        {self.unary_operator}
        {self.exp}
             )"""

class UnaryOperator(ASTNode):
    pass

class Complement(UnaryOperator):
    pass

class Negate(UnaryOperator):
    pass


class Parser:
    def __init__(self, _tokens):
        self.tokens = _tokens

    def expect_list(self, expected):
        actual = self.tokens.pop(0)
        if actual.token_type not in expected:
            raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
        return actual

    def expect(self, expected):
        actual = self.tokens.pop(0)
        if actual.token_type != expected:
            raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
        return actual

    def parse_exp(self):
        token = self.expect_list([TokenType.CONSTANT, TokenType.TILDE, TokenType.NEGATION, TokenType.OPEN_PAREN])
        match token.token_type:
            case TokenType.CONSTANT:
                return Constant(token.value)
            case TokenType.TILDE:
                return Unary(Complement, self.parse_exp())
            case TokenType.NEGATION:
                return Unary(Negate, self.parse_exp())
            case TokenType.OPEN_PAREN:
                exp = self.parse_exp()
                self.expect(TokenType.CLOSE_PAREN)
                return exp

    def parse_statement(self):
        self.expect(TokenType.RETURN)
        exp = self.parse_exp()
        self.expect(TokenType.SEMICOLON)
        return Return(exp)

    
    def parse_function_definition(self):
        self.expect(TokenType.INT)
        name = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.OPEN_PAREN)
        self.expect(TokenType.VOID)
        self.expect(TokenType.CLOSE_PAREN)
        self.expect(TokenType.OPEN_BRACE)
        body = self.parse_statement()
        self.expect(TokenType.CLOSE_BRACE)
        return FunctionDefinition(name, body)
        

    def parse_program(self):
        function = self.parse_function_definition()
        program = Program(function)
        if len(self.tokens) != 0:
            raise RuntimeError(f"Syntax error, tokens left: {[token for token in self.tokens]}")
        return program

