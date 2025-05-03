import assembly_ast as asm_ast
from abc import ABC, abstractmethod
from lexer import TokenType
import emitter

class ASTNode(ABC):
    @abstractmethod
    def generate(self):
        pass
    
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

    def emit(self):
        return emitter.IRProgram(self.function.emit())

    def generate(self):
        return asm_ast.asm_program(self.function.generate())



class FunctionDefinition(ASTNode):
    def __init__(self, _name, _body):
        self.name = _name
        self.body = _body

    def emit(self, instructions):
        self.body.emit(instructions)
        return emitter.IRFunctionDefinition(self.name, instructions)

    def generate(self):
        return asm_ast.asm_function(self.name, self.body.generate())

    

class Statement(ASTNode):
    pass

class Return(Statement):
    def __init__(self, _exp):
        self.exp = _exp

    def emit(self, instructions):
        self.exp.emit(instructions)
        instructions.append(emitter.IRReturn(instructions[-1].dst))
        return

    def generate(self):
        return [asm_ast.asm_mov(self.exp.generate(), asm_ast.asm_register()), asm_ast.asm_ret()]



class Exp(ASTNode):
    pass

class Constant(Exp):
    def __init__(self, _constant):
        self.constant = _constant

    def emit(self, instructions):
        return emitter.IRConstant(self.constant)

    def generate(self):
        return asm_ast.asm_imm(self.constant)
    
    def __str__(self, level = 0):
        return f"Constant({self.constant})"

    
class Unary(Exp):
    def __init__(self, _unary_operator, _exp):
        self.unary_operator = _unary_operator
        self.exp = _exp

    def emit(self, instructions):
        src = self.exp.emit(instructions)
        dst_name = "change_me.0"
        dst = emitter.IRVar(dst_name)
        tacky_op = self.unary_operator.emit()
        instructions.append(emitter.IRUnary(tacky_op,src,dst))
        return dst

    def generate(self):
        pass
    

class UnaryOperator(ASTNode):
    pass

class Complement(UnaryOperator):
    def emit(self):
        return emitter.IRComplement()

    def generate(self):
        pass

    def __str__(self, level = 0):
        return "Complement"


class Negate(UnaryOperator):
    def emit(self):
        return emitter.IRNegate()

    def generate(self):
        pass

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

