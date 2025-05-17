from lexer import TokenType, Token
from dataclasses import dataclass
from typing import List, Iterable
from c_ast import *

@dataclass
class Parser:
    tokens: List[Token]
    PRECEDENCE = {
        TokenType.ASTERISK:             50,
        TokenType.FORWARD_SLASH:        50,
        TokenType.PERCENT_SIGN:         50,
        TokenType.PLUS:                 45,
        TokenType.HYPHEN:               45,
        TokenType.LESS_THAN:            35,
        TokenType.LESS_THAN_OR_EQ:      35,
        TokenType.GREATER_THAN:         35,
        TokenType.GREATER_THAN_OR_EQ:   35,
        TokenType.TWO_EQUAL_SIGNS:      30,
        TokenType.EXCLAM_POINT_EQUAL:   30,
        TokenType.TWO_AMPERSANDS:       10,
        TokenType.TWO_VERT_BARS:         5,
    }

    def is_binary(self, token) -> bool:
        return token.token_type in self.PRECEDENCE.keys()

    def peek(self) -> Token:
        return self.tokens[0]
        
    def expect(self, expected) -> Token:
        if not isinstance(expected, Iterable):
            expected = [expected]
        actual = self.tokens.pop(0)
        if actual.token_type not in expected:
            raise RuntimeError(f"Expected '{expected}' but found '{actual.token_type}'")
        return actual
    
    def parse_binop(self) -> BinaryOperator:
        token = self.expect(self.PRECEDENCE.keys())
        match token.token_type:
            case TokenType.ASTERISK:
                return BinaryOperator.Multiply
            case TokenType.FORWARD_SLASH:
                return BinaryOperator.Divide
            case TokenType.PERCENT_SIGN:
                return BinaryOperator.Remainder
            case TokenType.PLUS:
                return BinaryOperator.Add
            case TokenType.HYPHEN:
                return BinaryOperator.Subtract
            case TokenType.TWO_AMPERSANDS:
                return BinaryOperator.And
            case TokenType.TWO_VERT_BARS:
                return BinaryOperator.Or
            case TokenType.TWO_EQUAL_SIGNS:
                return BinaryOperator.Equal
            case TokenType.EXCLAM_POINT_EQUAL:
                return BinaryOperator.NotEqual
            case TokenType.LESS_THAN:
                return BinaryOperator.LessThan
            case TokenType.LESS_THAN_OR_EQ:
                return BinaryOperator.LessOrEqual
            case TokenType.GREATER_THAN:
                return BinaryOperator.GreaterThan
            case TokenType.GREATER_THAN_OR_EQ:
                return BinaryOperator.GreaterOrEqual
            

    def parse_factor(self) -> Exp:
        token = self.expect([TokenType.CONSTANT, TokenType.TILDE, TokenType.HYPHEN, TokenType.EXCLAMATION_POINT, TokenType.OPEN_PAREN])
        match token.token_type:
            case TokenType.CONSTANT:
                return Constant(token.value)
            case TokenType.TILDE:
                return Unary(UnaryOperator.Complement, self.parse_factor())
            case TokenType.HYPHEN:
                return Unary(UnaryOperator.Negate, self.parse_factor())
            case TokenType.EXCLAMATION_POINT:
                return Unary(UnaryOperator.Not, self.parse_factor())
            case TokenType.OPEN_PAREN:
                exp = self.parse_exp()
                self.expect(TokenType.CLOSE_PAREN)
                return exp
            
    def parse_exp(self, min_prec = 0) -> Exp:
        left = self.parse_factor()
        next_token = self.peek()
        while self.is_binary(next_token) and self.PRECEDENCE[next_token.token_type] >= min_prec:
            operator = self.parse_binop()
            right = self.parse_exp(self.PRECEDENCE[next_token.token_type] + 1)
            left = Binary(operator, left, right)
            next_token = self.peek()
        return left

    def parse_statement(self) -> Statement:
        self.expect(TokenType.RETURN)
        exp = self.parse_exp()
        self.expect(TokenType.SEMICOLON)
        return Return(exp)

    
    def parse_function_definition(self) -> FunctionDefinition:
        self.expect(TokenType.INT)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.OPEN_PAREN)
        self.expect(TokenType.VOID)
        self.expect(TokenType.CLOSE_PAREN)
        self.expect(TokenType.OPEN_BRACE)
        body = self.parse_statement()
        self.expect(TokenType.CLOSE_BRACE)
        return FunctionDefinition(name, body)
        

    def parse_program(self) -> Program:
        function = self.parse_function_definition()
        program = Program(function)
        if len(self.tokens) != 0:
            raise RuntimeError(f"Syntax error, tokens left: {[token for token in self.tokens]}")
        return program

