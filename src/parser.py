from lexer import TokenType, Token
from dataclasses import dataclass
from typing import List, Iterable
from c_ast import *

@dataclass
class Parser:
    tokens: List[Token] #TODO: Should probably be a deque
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
        TokenType.QUESTION_MARK:         3,
        TokenType.EQUAL_SIGN:            1,
    }

    def is_binary(self, token) -> bool:
        return token.token_type in self.PRECEDENCE.keys()

    def peek(self) -> Token:
        return self.tokens[0]
    
    def advance(self) -> Token:
        return self.tokens.pop(0)
        
    def expect(self, expected) -> Token:
        if not isinstance(expected, Iterable):
            expected = [expected]
        token = self.advance()
        if token.token_type not in expected:
            raise RuntimeError(f"Expected '{expected}' but found '{token.token_type}' with {len(self.tokens)} tokens left")
        return token
    
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
        token = self.expect([
            TokenType.CONSTANT, 
            TokenType.TILDE, 
            TokenType.HYPHEN, 
            TokenType.EXCLAMATION_POINT, 
            TokenType.OPEN_PAREN, 
            TokenType.IDENTIFIER])
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
            case TokenType.IDENTIFIER:
                return Var(token.value)
            
    def parse_conditional_middle(self):
        self.expect(TokenType.QUESTION_MARK)
        exp = self.parse_exp(0)
        self.expect(TokenType.COLON)
        return exp
           
    def parse_exp(self, min_prec = 0) -> Exp:
        left = self.parse_factor()
        next_token = self.peek()
        while self.is_binary(next_token) and self.PRECEDENCE[next_token.token_type] >= min_prec:
            if next_token.token_type == TokenType.EQUAL_SIGN:
                self.advance()
                right = self.parse_exp(self.PRECEDENCE[next_token.token_type])
                left = Assignment(left, right)
            elif next_token.token_type == TokenType.QUESTION_MARK:
                middle = self.parse_conditional_middle()
                right = self.parse_exp(self.PRECEDENCE[next_token.token_type])
                left = Conditional(left, middle, right)
            else:
                operator = self.parse_binop()
                right = self.parse_exp(self.PRECEDENCE[next_token.token_type] + 1)
                left = Binary(operator, left, right)
            next_token = self.peek()
        return left
    
    def parse_declaration(self) -> Declaration:
        self.expect(TokenType.INT)
        name = self.expect(TokenType.IDENTIFIER).value
        init = None
        if self.peek().token_type == TokenType.EQUAL_SIGN:
            self.advance()
            init = self.parse_exp()
        self.expect(TokenType.SEMICOLON)
        return Declaration(name, init)

    def parse_statement(self) -> Statement:
        match self.peek().token_type:
            case TokenType.RETURN:
                self.advance()
                exp = self.parse_exp()
                self.expect(TokenType.SEMICOLON)
                return Return(exp)
            case TokenType.SEMICOLON:
                self.advance()
                return Null()
            case TokenType.IF:
                self.advance()
                self.expect(TokenType.OPEN_PAREN)
                cond = self.parse_exp()
                self.expect(TokenType.CLOSE_PAREN)
                then = self.parse_statement()
                else_ = None
                if self.peek().token_type == TokenType.ELSE:
                    self.advance()
                    else_ = self.parse_statement()
                return If(cond, then, else_)
            case TokenType.OPEN_BRACE:
                return Compound(self.parse_block())
            case _:
                exp = self.parse_exp()
                self.expect(TokenType.SEMICOLON)
                return Expression(exp)
    
    def parse_block_item(self) -> BlockItem:
        if self.peek().token_type == TokenType.INT:
            return self.parse_declaration()
        else:
            return self.parse_statement()
        
    def parse_block(self) -> Block:
        self.expect(TokenType.OPEN_BRACE)
        block_items = []
        while self.peek().token_type != TokenType.CLOSE_BRACE:
            next_block_item = self.parse_block_item()
            block_items.append(next_block_item)
        self.expect(TokenType.CLOSE_BRACE)
        return Block(block_items)
 
    def parse_function_definition(self) -> FunctionDefinition:
        self.expect(TokenType.INT)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.OPEN_PAREN)
        self.expect(TokenType.VOID)
        self.expect(TokenType.CLOSE_PAREN)
        body = self.parse_block()
        return FunctionDefinition(name, body)

    def parse_program(self) -> Program:
        function = self.parse_function_definition()
        program = Program(function)
        if len(self.tokens) != 0:
            raise RuntimeError(f"Syntax error, tokens left: {[token for token in self.tokens]}")
        return program

