from abc import ABC
import parser

class TackyNode(ABC):
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


class IRProgram(TackyNode):
    def __init__(self, _function):
        self.function = _function


class IRFunctionDefinition(TackyNode):
    def __init__(self, _name, _body):
        self.name = _name
        self.body = _body
    
    def __str__(self, level=0):
        def indent(text, level):
            prefix = "   "
            return "\n".join(prefix * level + str(line) for line in text)
        return f"IRFunctionDefinition(\n{indent(['name: '+self.name], 1)}\n{indent(['instructions:'], 1)}\n{indent(self.body, 2)}"
        

    

class IRInstruction(TackyNode):
    pass

class IRReturn(IRInstruction):
    def __init__(self, _val):
        self.val = _val

    def __str__(self, level=0):
        return f"IRReturn({self.val})"
    
class IRUnary(IRInstruction):
    def __init__(self, _unary_operator, _src, _dst):
        self.unary_operator = _unary_operator
        self.src = _src
        self.dst = _dst

    def __str__(self):
        return f"Unary({self.unary_operator}, {self.src}, {self.dst})"


class IRVal(TackyNode):
    pass

class IRConstant(IRVal):
    def __init__(self, _int):
        self.int = _int

    def __str__(self, level = 0):
        return f"Constant({self.int})"
    
class IRVar(IRVal):
    def __init__(self, _identifier):
        self.identifier = _identifier

    def __str__(self, level = 0):
        return f"Var('{self.identifier}')"
    

class IRUnaryOperator(TackyNode):
    pass

class IRComplement(IRUnaryOperator):
    def __str__(self, level = 0):
        return "Complement"


class IRNegate(IRUnaryOperator):
    def __str__(self, level = 0):
        return "Negate"
    
class IREmitter:
    register_counter = 0
    def make_temporary(self):
        register_name = "tmp." + str(self.register_counter)
        self.register_counter += 1
        return register_name

    def emit_unary_operator(self, ast_node):
        match ast_node:
            case parser.Complement():
                return IRComplement()
            case parser.Negate():
                return IRNegate()
            
    def emit_exp(self, ast_node, instructions):
        match ast_node:
            case parser.Constant(constant = c):
                return IRConstant(c)
            case parser.Unary(unary_operator = u, exp = e):
                src = self.emit_exp(e, instructions)
                dst_name = self.make_temporary()
                dst = IRVar(dst_name)
                tacky_op = self.emit_unary_operator(u)
                instructions.append(IRUnary(tacky_op,src,dst))
                return dst

    def emit_statement(self, ast_node):
        instructions = []
        ret = self.emit_exp(ast_node.exp, instructions)
        instructions.append(IRReturn(ret))
        return instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_statement(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
