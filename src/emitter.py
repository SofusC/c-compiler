from ir_ast import *
from c_ast import *
from semantic_analyser import SharedCounter

class IREmitter:
    label_counter = 0
    def make_temporary(self):
        register_name = f"tmp.{SharedCounter.get_value()}"
        SharedCounter.increment()
        return register_name
    
    def make_label(self, binop = None):
        match binop:
            case BinaryOperator.And:
                label_name = "and_false"
            case BinaryOperator.Or:
                label_name = "or_true"
            case str():
                label_name = binop
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
                raise RuntimeError(f"Binary {ast_node} not implemented")

    def emit_unary_operator(self, ast_node):
        match ast_node:
            case UnaryOperator.Complement:
                return IRUnaryOperator.Complement
            case UnaryOperator.Negate:
                return IRUnaryOperator.Negate
            case UnaryOperator.Not:
                return IRUnaryOperator.Not
            case _:
                raise RuntimeError(f"Unary {ast_node} not implemented")
    
    def emit_unary_instructions(self, unop, exp, instructions):
        src = self.emit_instructions(exp, instructions)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_unary_operator(unop)
        instructions.append(IRUnary(tacky_op,src,dst))
        return dst
        
    def emit_short_circuit_instructions(self, binop, e1, e2, instructions):
        short_circuit_result = 0 if binop == BinaryOperator.And else 1
        jump_if = IRJumpIfZero if binop == BinaryOperator.And else IRJumpIfNotZero
        v1 = self.emit_instructions(e1, instructions)
        label = self.make_label(binop)
        instructions.append(jump_if(v1, label))
        v2 = self.emit_instructions(e2, instructions)
        instructions.append(jump_if(v2, label))
        dst = IRVar(self.make_temporary())
        end_label = self.make_label()
        instructions.extend([IRCopy(IRConstant(1 - short_circuit_result), dst),
                            IRJump(end_label),
                            IRLabel(label),
                            IRCopy(IRConstant(short_circuit_result), dst),
                            IRLabel(end_label)])
        return dst

    def emit_binary_instructions(self, binop, e1, e2, instructions):
        v1 = self.emit_instructions(e1, instructions)
        v2 = self.emit_instructions(e2, instructions)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_binary_operator(binop)
        instructions.append(IRBinary(tacky_op, v1, v2, dst))
        return dst
            
    def emit_instructions(self, ast_node, instructions): #TODO: make this handle just exp
        match ast_node:
            case Constant(constant):
                return IRConstant(constant)
            case Unary(unop, exp):
                return self.emit_unary_instructions(unop, exp, instructions)
            case Binary(BinaryOperator.And | BinaryOperator.Or as binop, e1, e2):
                return self.emit_short_circuit_instructions(binop, e1, e2, instructions)
            case Binary(binop, e1, e2):
                return self.emit_binary_instructions(binop, e1, e2, instructions)
            case Var(v):
                return IRVar(v)
            case Assignment(Var(v), rhs):
                result = self.emit_instructions(rhs, instructions)
                lhs = IRVar(v)
                instructions.append(IRCopy(result, lhs))
                return lhs
            case Declaration(name, rhs):
                result = self.emit_instructions(rhs, instructions)
                lhs = IRVar(name)
                instructions.append(IRCopy(result, lhs))
                return lhs
            case Conditional(cond, then, else_):
                return self.emit_conditional(cond, then, else_, instructions)
            case _:
                raise RuntimeError(f"{ast_node} not implemented")
    
    def emit_conditional(self, cond, then, else_, instructions):
        dst = self.emit_instructions(cond, instructions)
        c = IRVar(self.make_temporary())
        instructions.append(IRCopy(dst, c))
        e2_label = self.make_label("e2")
        instructions.append(IRJumpIfZero(c, e2_label))
        then_dst = self.emit_instructions(then, instructions)
        v1 = IRVar(self.make_temporary())
        instructions.append(IRCopy(then_dst, v1))
        result = IRVar(self.make_temporary())
        instructions.append(IRCopy(v1, result))
        end = self.make_label("end")
        instructions.append(IRJump(end))
        instructions.append(IRLabel(e2_label))
        else_dst = self.emit_instructions(else_, instructions)
        v2 = IRVar(self.make_temporary())
        instructions.append(IRCopy(else_dst, v2))
        instructions.append(IRCopy(v2, result))
        instructions.append(IRLabel(end))
        return result

            
    def emit_if(self, cond, then, else_, instructions): #TODO: This is awful
        dst = self.emit_instructions(cond, instructions)
        c = IRVar(self.make_temporary())
        instructions.append(IRCopy(dst, c))
        end = self.make_label("end")
        if else_ is None:
            instructions.append(IRJumpIfZero(c, end))
            self.emit_block_item(then, instructions)
        else:
            else_label = self.make_label("else")
            instructions.append(IRJumpIfZero(c, else_label))
            self.emit_block_item(then, instructions)
            instructions.append(IRJump(end))
            instructions.append(IRLabel(else_label))
            self.emit_block_item(else_, instructions)
        
        instructions.append(IRLabel(end))

            
    def emit_block_item(self, item, instructions): #TODO: Split this into decl and statement
        match item:
            case Declaration(_, None):
                pass
            case Declaration(_, Exp()):
                self.emit_instructions(item, instructions)
            case Return(exp):
                ret = self.emit_instructions(exp, instructions)
                instructions.append(IRReturn(ret))
            case Expression(exp):
                self.emit_instructions(exp, instructions)
            case If(cond, then, else_):
                self.emit_if(cond, then, else_, instructions)
            case Null():
                pass
            case _:
                raise RuntimeError(f"BlockItem {item} not implemented")

    def emit_blocks(self, blocks):
        instructions = [] #TODO: Cant instructions be an object variable
        for block in blocks:
            self.emit_block_item(block, instructions)
        instructions.append(IRReturn(IRConstant(0)))
        return instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_blocks(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
