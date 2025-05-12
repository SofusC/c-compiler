from ir_ast import *
from c_ast import *

class IREmitter:
    register_counter = 0
    def make_temporary(self):
        register_name = "tmp." + str(self.register_counter)
        self.register_counter += 1
        return register_name
    
    def emit_binary_operator(self, ast_node):
        match ast_node:
            case BinaryOperator.Add:
                return IRBinaryOperator.Add
            case BinaryOperator.Subtract:
                return IRBinaryOperator.Subtract
            case BinaryOperator.Multiply:
                return IRBinaryOperator.Multiply
            case BinaryOperator.Divide:
                return IRBinaryOperator.Divide
            case BinaryOperator.Remainder:
                return IRBinaryOperator.Remainder

    def emit_unary_operator(self, ast_node):
        match ast_node:
            case UnaryOperator.Complement:
                return IRUnaryOperator.Complement
            case UnaryOperator.Negate:
                return IRUnaryOperator.Negate
            
    def emit_exp(self, ast_node, instructions):
        match ast_node:
            case Constant(constant):
                return IRConstant(constant)
            case Unary(unary_operator, exp):
                src = self.emit_exp(exp, instructions)
                dst_name = self.make_temporary()
                dst = IRVar(dst_name)
                tacky_op = self.emit_unary_operator(unary_operator)
                instructions.append(IRUnary(tacky_op,src,dst))
                return dst
            case Binary(op, e1, e2):
                v1 = self.emit_exp(e1, instructions)
                v2 = self.emit_exp(e2, instructions)
                dst_name = self.make_temporary()
                dst = IRVar(dst_name)
                tacky_op = self.emit_binary_operator(op)
                instructions.append(IRBinary(tacky_op, v1, v2, dst))
                return dst
            case _:
                raise RuntimeError(f"{ast_node} not implemented")

    def emit_statement(self, ast_node):
        instructions = []
        ret = self.emit_exp(ast_node.exp, instructions)
        instructions.append(IRReturn(ret))
        return instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_statement(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
