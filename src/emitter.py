from ir_ast import *
from c_ast import *
from semantic_analyser import SharedCounter

class IREmitter:
    instructions = []
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
    
    def emit_unary_instructions(self, unop, exp):
        src = self.emit_instructions(exp)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_unary_operator(unop)
        self.instructions.append(IRUnary(tacky_op,src,dst))
        return dst
        
    def emit_short_circuit_instructions(self, binop, e1, e2):
        short_circuit_result = 0 if binop == BinaryOperator.And else 1
        jump_if = IRJumpIfZero if binop == BinaryOperator.And else IRJumpIfNotZero
        v1 = self.emit_instructions(e1)
        label = self.make_label(binop)
        self.instructions.append(jump_if(v1, label))
        v2 = self.emit_instructions(e2)
        self.instructions.append(jump_if(v2, label))
        dst = IRVar(self.make_temporary())
        end_label = self.make_label()
        self.instructions.extend([IRCopy(IRConstant(1 - short_circuit_result), dst),
                            IRJump(end_label),
                            IRLabel(label),
                            IRCopy(IRConstant(short_circuit_result), dst),
                            IRLabel(end_label)])
        return dst

    def emit_binary_instructions(self, binop, e1, e2):
        v1 = self.emit_instructions(e1)
        v2 = self.emit_instructions(e2)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_binary_operator(binop)
        self.instructions.append(IRBinary(tacky_op, v1, v2, dst))
        return dst
            
    def emit_instructions(self, ast_node): #TODO: make this handle just exp
        match ast_node:
            case Constant(constant):
                return IRConstant(constant)
            case Unary(unop, exp):
                return self.emit_unary_instructions(unop, exp)
            case Binary(BinaryOperator.And | BinaryOperator.Or as binop, e1, e2):
                return self.emit_short_circuit_instructions(binop, e1, e2)
            case Binary(binop, e1, e2):
                return self.emit_binary_instructions(binop, e1, e2)
            case Var(v):
                return IRVar(v)
            case Assignment(Var(v), rhs):
                result = self.emit_instructions(rhs)
                lhs = IRVar(v)
                self.instructions.append(IRCopy(result, lhs))
                return lhs
            case Declaration(name, rhs):
                result = self.emit_instructions(rhs)
                lhs = IRVar(name)
                self.instructions.append(IRCopy(result, lhs))
                return lhs
            case Conditional(cond, then, else_):
                return self.emit_conditional(cond, then, else_)
            case _:
                raise RuntimeError(f"{ast_node} not implemented")
    
    def emit_conditional(self, cond, then, else_):
        dst = self.emit_instructions(cond)
        c = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(dst, c))
        e2_label = self.make_label("e2")
        self.instructions.append(IRJumpIfZero(c, e2_label))
        then_dst = self.emit_instructions(then)
        v1 = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(then_dst, v1))
        result = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(v1, result))
        end = self.make_label("end")
        self.instructions.append(IRJump(end))
        self.instructions.append(IRLabel(e2_label))
        else_dst = self.emit_instructions(else_)
        v2 = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(else_dst, v2))
        self.instructions.append(IRCopy(v2, result))
        self.instructions.append(IRLabel(end))
        return result

            
    def emit_if(self, cond, then, else_): #TODO: This is awful
        dst = self.emit_instructions(cond)
        c = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(dst, c))
        end = self.make_label("end")
        if else_ is None:
            self.instructions.append(IRJumpIfZero(c, end))
            self.emit_block_item(then)
        else:
            else_label = self.make_label("else")
            self.instructions.append(IRJumpIfZero(c, else_label))
            self.emit_block_item(then)
            self.instructions.append(IRJump(end))
            self.instructions.append(IRLabel(else_label))
            self.emit_block_item(else_)
        
        self.instructions.append(IRLabel(end))

            
    def emit_block_item(self, item): #TODO: Split this into decl and statement
        match item:
            case Declaration(_, None):
                pass
            case Declaration(_, Exp()):
                self.emit_instructions(item)
            case Return(exp):
                ret = self.emit_instructions(exp)
                self.instructions.append(IRReturn(ret))
            case Expression(exp):
                self.emit_instructions(exp)
            case If(cond, then, else_):
                self.emit_if(cond, then, else_)
            case Null():
                pass
            case _:
                raise RuntimeError(f"BlockItem {item} not implemented")

    def emit_blocks(self, blocks):
        for block in blocks:
            self.emit_block_item(block)
        self.instructions.append(IRReturn(IRConstant(0)))
        return self.instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_blocks(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
