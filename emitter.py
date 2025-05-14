from ir_ast import *
from c_ast import *

class IREmitter:
    register_counter = 0
    label_counter = 0
    def make_temporary(self):
        register_name = "tmp." + str(self.register_counter)
        self.register_counter += 1
        return register_name
    
    def make_label(self, binop = None):
        match binop:
            case BinaryOperator.And:
                label_name = "and_false"
            case BinaryOperator.Or:
                label_name = "or_true"
            case _:
                label_name = "end"
        label_name += str(self.label_counter)
        self.label_counter += 1
        return label_name

    
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
            case BinaryOperator.Equal:
                return IRBinaryOperator.Equal
            case BinaryOperator.NotEqual:
                return IRBinaryOperator.NotEqual
            case BinaryOperator.LessThan:
                return IRBinaryOperator.LessThan
            case BinaryOperator.LessOrEqual:
                return IRBinaryOperator.LessOrEqual
            case BinaryOperator.GreaterThan:
                return IRBinaryOperator.GreaterThan
            case BinaryOperator.GreaterOrEqual:
                return IRBinaryOperator.GreaterOrEqual
            case _:
                raise RuntimeError(f"{ast_node} not implemented")

    def emit_unary_operator(self, ast_node):
        match ast_node:
            case UnaryOperator.Complement:
                return IRUnaryOperator.Complement
            case UnaryOperator.Negate:
                return IRUnaryOperator.Negate
            case UnaryOperator.Not:
                return IRUnaryOperator.Not
            case _:
                raise RuntimeError(f"{ast_node} not implemented")
            
    def emit_instructions(self, ast_node, instructions):
        match ast_node:
            case Constant(constant):
                return IRConstant(constant)
            case Unary(unop, exp):
                src = self.emit_instructions(exp, instructions)
                dst = IRVar(self.make_temporary())
                tacky_op = self.emit_unary_operator(unop)
                instructions.append(IRUnary(tacky_op,src,dst))
                return dst
            case Binary(BinaryOperator.And | BinaryOperator.Or as binop, e1, e2):
                short_circuit_result = 0 if binop == BinaryOperator.And else 1
                jump_if = IRJumpIfZero if binop == BinaryOperator.And else IRJumpIfNotZero
                v1 = self.emit_instructions(e1, instructions)
                label = IRLabel(self.make_label(binop))
                instructions.append(jump_if(v1, label))
                v2 = self.emit_instructions(e2, instructions)
                instructions.append(jump_if(v2, label))
                dst = IRVar(self.make_temporary())
                end_label = IRLabel(self.make_label())
                instructions.extend([IRCopy(IRConstant(1 - short_circuit_result), dst),
                                    IRJump(end_label),
                                    label,
                                    IRCopy(IRConstant(short_circuit_result), dst),
                                    end_label])
                return dst
            case Binary(binop, e1, e2):
                v1 = self.emit_instructions(e1, instructions)
                v2 = self.emit_instructions(e2, instructions)
                dst = IRVar(self.make_temporary())
                tacky_op = self.emit_binary_operator(binop)
                instructions.append(IRBinary(tacky_op, v1, v2, dst))
                return dst
            case _:
                raise RuntimeError(f"{ast_node} not implemented")

    def emit_statement(self, ast_node):
        instructions = []
        ret = self.emit_instructions(ast_node.exp, instructions) # Assumes ast_node is a Return-node
        instructions.append(IRReturn(ret))
        return instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_statement(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
