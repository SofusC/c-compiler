from ir_ast import *
from c_ast import *
from semantic_analyser import SharedCounter

class IREmitter:
    instructions = []
    label_counter = 0

    unop_map = {
        UnaryOperator.Complement     : IRUnaryOperator.Complement,
        UnaryOperator.Negate         : IRUnaryOperator.Negate,
        UnaryOperator.Not            : IRUnaryOperator.Not,
    }
    binop_map = {
        BinaryOperator.Add           : IRBinaryOperator.Add,
        BinaryOperator.Subtract      : IRBinaryOperator.Subtract,
        BinaryOperator.Multiply      : IRBinaryOperator.Multiply,
        BinaryOperator.Divide        : IRBinaryOperator.Divide,
        BinaryOperator.Remainder     : IRBinaryOperator.Remainder,
        BinaryOperator.Equal         : IRBinaryOperator.Equal,
        BinaryOperator.NotEqual      : IRBinaryOperator.NotEqual,
        BinaryOperator.LessThan      : IRBinaryOperator.LessThan,
        BinaryOperator.LessOrEqual   : IRBinaryOperator.LessOrEqual,
        BinaryOperator.GreaterThan   : IRBinaryOperator.GreaterThan,
        BinaryOperator.GreaterOrEqual: IRBinaryOperator.GreaterOrEqual,
    }

    def make_temporary(self):
        register_name = f"tmp.{SharedCounter.get_value()}"
        SharedCounter.increment()
        return register_name
    
    def make_label(self, label_name):
        label_name += str(self.label_counter)
        self.label_counter += 1
        return label_name

    
    def emit_binary_operator(self, ast_node):
        try:
            return self.binop_map[ast_node]
        except KeyError:
            raise RuntimeError(f"Binary operator {ast_node} not implemented")

    def emit_unary_operator(self, ast_node):
        try:
            return self.unop_map[ast_node]
        except KeyError:
            raise RuntimeError(f"Unary operator {ast_node} not implemented")
    
    def emit_unary_instructions(self, unop, exp):
        src = self.emit_exp(exp)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_unary_operator(unop)
        self.instructions.append(IRUnary(tacky_op,src,dst))
        return dst
    
    def emit_short_circuit_instructions(self, binop, e1, e2):
        if binop == BinaryOperator.And:
            short_circuit_value = 0
            jump_instr = IRJumpIfZero
        elif binop == BinaryOperator.Or:
            short_circuit_value = 1
            jump_instr = IRJumpIfNotZero

        # Evaluate first expression
        val1 = self.emit_exp(e1)
        sc_label = self.make_label(f"sc_{binop.name.lower()}")
        self.instructions.append(jump_instr(val1, sc_label))

        # Evaluate second expression only if needed
        val2 = self.emit_exp(e2)
        self.instructions.append(jump_instr(val2, sc_label))

        # Compute the result
        result = IRVar(self.make_temporary())
        end_label = self.make_label("end_sc")

        self.instructions.extend([
            IRCopy(IRConstant(1 - short_circuit_value), result),
            IRJump(end_label),
            IRLabel(sc_label),
            IRCopy(IRConstant(short_circuit_value), result),
            IRLabel(end_label),
        ])

        return result
      
    def emit_binary_instructions(self, binop, e1, e2):
        v1 = self.emit_exp(e1)
        v2 = self.emit_exp(e2)
        dst = IRVar(self.make_temporary())
        tacky_op = self.emit_binary_operator(binop)
        self.instructions.append(IRBinary(tacky_op, v1, v2, dst))
        return dst
            
    def emit_exp(self, ast_node):
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
                result = self.emit_exp(rhs)
                lhs = IRVar(v)
                self.instructions.append(IRCopy(result, lhs))
                return lhs
            case Conditional(cond, then, else_):
                return self.emit_conditional(cond, then, else_)
            case _:
                raise RuntimeError(f"{ast_node} not implemented")
            
    def emit_conditional(self, cond, then, else_):
        # Evaluate condition
        cond_val = self.emit_exp(cond)
        cond_tmp = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(cond_val, cond_tmp))

        result = IRVar(self.make_temporary())

        else_label = self.make_label("else")
        end_label = self.make_label("end")

        # Conditional jump to else
        self.instructions.append(IRJumpIfZero(cond_tmp, else_label))

        # Then branch
        then_val = self.emit_exp(then)
        then_tmp = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(then_val, then_tmp))
        self.instructions.append(IRCopy(then_tmp, result))
        self.instructions.append(IRJump(end_label))

        # Else branch
        self.instructions.append(IRLabel(else_label))
        else_val = self.emit_exp(else_)
        else_tmp = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(else_val, else_tmp))
        self.instructions.append(IRCopy(else_tmp, result))

        self.instructions.append(IRLabel(end_label))
        return result
    
    def emit_if(self, cond, then, else_):
        # Evaluate condition
        cond_val = self.emit_exp(cond)
        cond_tmp = IRVar(self.make_temporary())
        self.instructions.append(IRCopy(cond_val, cond_tmp))

        end_label = self.make_label("end")

        if else_ is None:
            self.instructions.append(IRJumpIfZero(cond_tmp, end_label))
            self.emit_block_item(then)
        else:
            # With else branch
            else_label = self.make_label("else")
            self.instructions.append(IRJumpIfZero(cond_tmp, else_label))
            self.emit_block_item(then)
            self.instructions.append(IRJump(end_label))
            self.instructions.append(IRLabel(else_label))
            self.emit_block_item(else_)

        self.instructions.append(IRLabel(end_label))     

    def emit_declaration(self, decl):
        match decl:
            case Declaration(_, None):
                pass
            case Declaration(name, rhs):
                result = self.emit_exp(rhs)
                lhs = IRVar(name)
                self.instructions.append(IRCopy(result, lhs))
                return lhs
            case _:
                raise RuntimeError(f"Declaration {decl} not implemented")

    def emit_statement(self, statement):
        match statement:
            case Return(exp):
                ret = self.emit_exp(exp)
                self.instructions.append(IRReturn(ret))
            case Expression(exp):
                self.emit_exp(exp)
            case If(cond, then, else_):
                self.emit_if(cond, then, else_)
            case Null():
                pass
            case _:
                raise RuntimeError(f"Statement {statement} not implemented")

    def emit_block_item(self, item):
        match item:
            case Declaration():
                self.emit_declaration(item)
            case Statement():
                self.emit_statement(item)
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
