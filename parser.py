from __future__ import annotations
from abc import ABC
from lexer import TokenType, Token
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Iterable

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


@dataclass
class Program(ASTNode):
    function: FunctionDefinition



@dataclass
class FunctionDefinition(ASTNode):
    name: str
    body: Statement



class Statement(ASTNode):
    pass

@dataclass
class Return(Statement):
    exp: Exp



class Exp(ASTNode):
    pass

@dataclass
class Constant(Exp):
    constant: int

@dataclass
class Unary(Exp):
    unary_operator: UnaryOperator
    exp: Exp
    
class UnaryOperator(Enum):
    Complement  = auto()
    Negate      = auto()

@dataclass
class Binary(Exp):
    binary_operator: BinaryOperator
    left_exp: Exp
    right_exp: Exp

class BinaryOperator(Enum):
    Add         = auto()
    Subtract    = auto()
    Multiply    = auto()
    Divide      = auto()
    Remainder   = auto()


@dataclass
class Parser:
    tokens: List[Token]
    PRECEDENCE = {
        TokenType.ASTERISK:         50,
        TokenType.FORWARD_SLASH:    50,
        TokenType.PERCENT_SIGN:     50,
        TokenType.PLUS:             45,
        TokenType.HYPHEN:           45,
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

    def parse_factor(self) -> Exp:
        token = self.expect([TokenType.CONSTANT, TokenType.TILDE, TokenType.HYPHEN, TokenType.OPEN_PAREN])
        match token.token_type:
            case TokenType.CONSTANT:
                return Constant(token.value)
            case TokenType.TILDE:
                return Unary(UnaryOperator.Complement, self.parse_factor())
            case TokenType.HYPHEN:
                return Unary(UnaryOperator.Negate, self.parse_factor())
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

