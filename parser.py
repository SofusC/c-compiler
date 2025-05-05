from abc import ABC
from lexer import TokenType

class ASTNode(ABC):
    def __str__(self, level = 0):
        def indent(text, level):
            prefix = "   "
            return "\n".join(prefix * level + line for line in text.splitlines())
        
        class_name = self.__class__.__name__
        fields = self.__dict__.items()
        field_strings = []
        for _, value in fields:
            field_strings.append(f"{value}")
        body = "\n".join(field_strings)
        return f"{indent(class_name + '(', level)}\n{indent(body, level + 1)}\n{indent(')', level)}"


class Program(ASTNode):
    def __init__(self, _function):
        self.function = _function



class FunctionDefinition(ASTNode):
    def __init__(self, _name, _body):
        self.name = _name
        self.body = _body
    

class Statement(ASTNode):
    pass

class Return(Statement):
    def __init__(self, _exp):
        self.exp = _exp



class Exp(ASTNode):
    pass

class Constant(Exp):
    def __init__(self, _constant):
        self.constant = _constant
    
    def __str__(self, level = 0):
        return f"Constant({self.constant})"

    
class Unary(Exp):
    def __init__(self, _unary_operator, _exp):
        self.unary_operator = _unary_operator
        self.exp = _exp


class UnaryOperator(ASTNode):
    pass

class Complement(UnaryOperator):
    def __str__(self, level = 0):
        return "Complement"


class Negate(UnaryOperator):
    def __str__(self, level = 0):
        return "Negate"
    

class Parser:
    def __init__(self, _tokens):
        self.tokens = _tokens
        
    def expect(self, expected):
        if not isinstance(expected, list):
            expected = [expected]
        actual = self.tokens.pop(0)
        if actual.token_type not in expected:
            raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
        return actual

    def parse_exp(self):
        token = self.expect([TokenType.CONSTANT, TokenType.TILDE, TokenType.NEGATION, TokenType.OPEN_PAREN])
        match token.token_type:
            case TokenType.CONSTANT:
                return Constant(token.value)
            case TokenType.TILDE:
                return Unary(Complement(), self.parse_exp())
            case TokenType.NEGATION:
                return Unary(Negate(), self.parse_exp())
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
        name = self.expect(TokenType.IDENTIFIER).value
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

