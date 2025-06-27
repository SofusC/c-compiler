from .lexer import TokenType, Token
from dataclasses import dataclass
from typing import List, Iterable
from .c_ast import *

@dataclass
class Parser:
    tokens: List[Token] #TODO: Should probably be a deque
    specifiers = [TokenType.INT, TokenType.EXTERN, TokenType.STATIC]
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
    binop_map = {
        TokenType.ASTERISK:           BinaryOperator.Multiply,
        TokenType.FORWARD_SLASH:      BinaryOperator.Divide,
        TokenType.PERCENT_SIGN:       BinaryOperator.Remainder,
        TokenType.PLUS:               BinaryOperator.Add,
        TokenType.HYPHEN:             BinaryOperator.Subtract,
        TokenType.TWO_AMPERSANDS:     BinaryOperator.And,
        TokenType.TWO_VERT_BARS:      BinaryOperator.Or,
        TokenType.TWO_EQUAL_SIGNS:    BinaryOperator.Equal,
        TokenType.EXCLAM_POINT_EQUAL: BinaryOperator.NotEqual,
        TokenType.LESS_THAN:          BinaryOperator.LessThan,
        TokenType.LESS_THAN_OR_EQ:    BinaryOperator.LessOrEqual,
        TokenType.GREATER_THAN:       BinaryOperator.GreaterThan,
        TokenType.GREATER_THAN_OR_EQ: BinaryOperator.GreaterOrEqual,
    }
    unop_map = {
        TokenType.TILDE:             UnaryOperator.Complement,
        TokenType.HYPHEN:            UnaryOperator.Negate,
        TokenType.EXCLAMATION_POINT: UnaryOperator.Not,
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
        token = self.peek()
        if token.token_type not in expected:
            raise RuntimeError(f"Expected '{expected}' but found '{token.token_type}' with {len(self.tokens)} tokens left")
        token = self.advance()
        return token
    
    def parse_binop(self) -> BinaryOperator:
        token = self.expect(self.binop_map.keys())
        return self.binop_map[token.token_type]
    
    def parse_argument_list(self) -> List[Exp]:
        args = []
        if self.peek().token_type != TokenType.CLOSE_PAREN:
            while True:
                args.append(self.parse_exp())
                if self.peek().token_type != TokenType.COMMA:
                    break
                self.expect(TokenType.COMMA)
        return args
            
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
            case TokenType.TILDE | TokenType.HYPHEN | TokenType.EXCLAMATION_POINT as unop:
                return Unary(self.unop_map[unop], self.parse_factor())
            case TokenType.OPEN_PAREN:
                exp = self.parse_exp()
                self.expect(TokenType.CLOSE_PAREN)
                return exp
            case TokenType.IDENTIFIER if self.peek().token_type == TokenType.OPEN_PAREN:
                self.advance()
                args = self.parse_argument_list()
                self.expect(TokenType.CLOSE_PAREN)
                return FunctionCall(token.value, args)
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
    
    def parse_optional_exp(self, end_symbol) -> Exp | None:
        if self.peek().token_type != end_symbol:
            exp = self.parse_exp()
            return exp
        return None
    
    def parse_for_init(self):
        if self.peek().token_type in self.specifiers:
            decl = self.parse_declaration()
            if isinstance(decl, FunDecl):
                raise RuntimeError(f"Cannot have function declaration {decl} in for init")
            return InitDecl(decl.variable_declaration)
        else:
            exp = self.parse_optional_exp(TokenType.SEMICOLON)
            self.expect(TokenType.SEMICOLON)
            return InitExp(exp)
    
    def parse_while(self):
        self.expect(TokenType.WHILE)
        self.expect(TokenType.OPEN_PAREN)
        cond = self.parse_exp()
        self.expect(TokenType.CLOSE_PAREN)
        body = self.parse_statement()
        return While(cond, body)
    
    def parse_dowhile(self):
        self.expect(TokenType.DO)
        body = self.parse_statement()
        self.expect(TokenType.WHILE)
        self.expect(TokenType.OPEN_PAREN)
        cond = self.parse_exp()
        self.expect(TokenType.CLOSE_PAREN)
        self.expect(TokenType.SEMICOLON)
        return DoWhile(body, cond)
    
    def parse_for(self):
        self.expect(TokenType.FOR)
        self.expect(TokenType.OPEN_PAREN)
        for_init = self.parse_for_init()
        cond = self.parse_optional_exp(TokenType.SEMICOLON)
        self.expect(TokenType.SEMICOLON)
        post = self.parse_optional_exp(TokenType.CLOSE_PAREN)
        self.expect(TokenType.CLOSE_PAREN)
        body = self.parse_statement()
        return For(for_init, cond, post, body)
    
    def parse_if(self):
        self.expect(TokenType.IF)
        self.expect(TokenType.OPEN_PAREN)
        cond = self.parse_exp()
        self.expect(TokenType.CLOSE_PAREN)
        then = self.parse_statement()
        else_ = None
        if self.peek().token_type == TokenType.ELSE:
            self.advance()
            else_ = self.parse_statement()
        return If(cond, then, else_)

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
                return self.parse_if()
            case TokenType.OPEN_BRACE:
                return Compound(self.parse_block())
            case TokenType.BREAK:
                self.advance()
                self.expect(TokenType.SEMICOLON)
                return Break()
            case TokenType.CONTINUE:
                self.advance()
                self.expect(TokenType.SEMICOLON)
                return Continue()
            case TokenType.WHILE:
                return self.parse_while()
            case TokenType.DO:
                return self.parse_dowhile()
            case TokenType.FOR:
                return self.parse_for()
            case _:
                exp = self.parse_exp()
                self.expect(TokenType.SEMICOLON)
                return Expression(exp)
    
    def parse_block_item(self) -> BlockItem:
        if self.peek().token_type in self.specifiers:
            return D(self.parse_declaration())
        else:
            return S(self.parse_statement())
        
    def parse_block(self) -> Block:
        self.expect(TokenType.OPEN_BRACE)
        block_items = []
        while self.peek().token_type != TokenType.CLOSE_BRACE:
            next_block_item = self.parse_block_item()
            block_items.append(next_block_item)
        self.expect(TokenType.CLOSE_BRACE)
        return Block(block_items)
    
    def parse_param_list(self) -> List[str]:
        params = []
        if self.peek().token_type == TokenType.VOID:
            self.advance()
            return params
        self.expect(TokenType.INT)
        params.append(self.expect(TokenType.IDENTIFIER).value)
        while self.peek().token_type != TokenType.CLOSE_PAREN:
            self.expect(TokenType.COMMA)
            self.expect(TokenType.INT)
            params.append(self.expect(TokenType.IDENTIFIER).value)
        return params
    
    def parse_variable_declaration(self, type, storage_class) -> VariableDeclaration:
        name = self.expect(TokenType.IDENTIFIER).value
        init = None
        if self.peek().token_type == TokenType.EQUAL_SIGN:
            self.advance()
            init = self.parse_exp()
        self.expect(TokenType.SEMICOLON)
        return VariableDeclaration(name, init, storage_class)
 
    def parse_function_declaration(self, type, storage_class) -> FunctionDeclaration:
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.OPEN_PAREN)
        params = self.parse_param_list()
        self.expect(TokenType.CLOSE_PAREN)
        body = None
        if self.peek().token_type == TokenType.OPEN_BRACE:
            body = self.parse_block()
        else:
            self.expect(TokenType.SEMICOLON)
        return FunctionDeclaration(name, params, body, storage_class)
    
    def parse_type_and_storage_class(self):
        types = []
        storage_classes = []
        while self.peek().token_type in self.specifiers:
            token = self.expect(self.specifiers)
            if token.token_type == TokenType.INT:
                types.append(token)
            else:
                storage_classes.append(token)

        if len(types) != 1:
            raise RuntimeError(f"Invalid type specifier(s) {types}")
        if len(storage_classes) > 1:
            raise RuntimeError("Invalid storage class")
        
        type = Type.Int

        if len(storage_classes) == 1:
            token_type = storage_classes[0].token_type
            if token_type == TokenType.EXTERN:
                storage_class = StorageClass.extern
            if token_type == TokenType.STATIC:
                storage_class = StorageClass.static
        else:
            storage_class = None

        return type, storage_class
    
    def parse_declaration(self) -> Declaration:
        type, storage_class = self.parse_type_and_storage_class()
        if self.tokens[1].token_type == TokenType.OPEN_PAREN:
            return FunDecl(self.parse_function_declaration(type, storage_class))
        else:
            return VarDecl(self.parse_variable_declaration(type, storage_class))

    def parse_program(self) -> Program:
        declarations = []
        while len(self.tokens) != 0:
            declarations.append(self.parse_declaration())
        return Program(declarations)

