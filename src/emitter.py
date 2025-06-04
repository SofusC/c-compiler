from ir_ast import *
from c_ast import *
from semantic_analyser import NameGenerator

class IREmitter:
    instructions = []

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
        dst = IRVar(NameGenerator.make_temporary())
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
        sc_label = NameGenerator.make_label(f"sc_{binop.name.lower()}")
        self.instructions.append(jump_instr(val1, sc_label))

        # Evaluate second expression only if needed
        val2 = self.emit_exp(e2)
        self.instructions.append(jump_instr(val2, sc_label))

        # Compute the result
        result = IRVar(NameGenerator.make_temporary())
        end_label = NameGenerator.make_label("end_sc")

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
        dst = IRVar(NameGenerator.make_temporary())
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
        cond_tmp = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(cond_val, cond_tmp))

        result = IRVar(NameGenerator.make_temporary())

        else_label = NameGenerator.make_label("else")
        end_label = NameGenerator.make_label("end")

        # Conditional jump to else
        self.instructions.append(IRJumpIfZero(cond_tmp, else_label))

        # Then branch
        then_val = self.emit_exp(then)
        then_tmp = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(then_val, then_tmp))
        self.instructions.append(IRCopy(then_tmp, result))
        self.instructions.append(IRJump(end_label))

        # Else branch
        self.instructions.append(IRLabel(else_label))
        else_val = self.emit_exp(else_)
        else_tmp = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(else_val, else_tmp))
        self.instructions.append(IRCopy(else_tmp, result))

        self.instructions.append(IRLabel(end_label))
        return result
    
    def emit_if(self, cond, then, else_):
        # Evaluate condition
        cond_val = self.emit_exp(cond)
        cond_tmp = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(cond_val, cond_tmp))

        end_label = NameGenerator.make_label("end")

        if else_ is None:
            self.instructions.append(IRJumpIfZero(cond_tmp, end_label))
            self.emit_block_item(then)
        else:
            # With else branch
            else_label = NameGenerator.make_label("else")
            self.instructions.append(IRJumpIfZero(cond_tmp, else_label))
            self.emit_block_item(then)
            self.instructions.append(IRJump(end_label))
            self.instructions.append(IRLabel(else_label))
            self.emit_block_item(else_)

        self.instructions.append(IRLabel(end_label))  

    def emit_for_init(self, for_init):
        match for_init:
            case InitDecl(decl):
                return self.emit_declaration(decl)
            case InitExp(None):
                pass
            case InitExp(exp):
                return self.emit_exp(exp)
            case _:
                raise RuntimeError(f"ForInit {for_init} not implemented")
    
    def emit_conditional_jump(self, cond, jump_label, invert=False):
        result = self.emit_exp(cond)
        v = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(result, v))
        if invert:
            self.instructions.append(IRJumpIfNotZero(v, jump_label))
        else:
            self.instructions.append(IRJumpIfZero(v, jump_label))

    def make_loop_labels(self, label):
        return (
            IRLabel(f"start_{label}"),
            IRLabel(f"continue_{label}"),
            IRLabel(f"break_{label}")
        )

    def emit_loop(self, loop):
        match loop:
            case While(cond, body, label):
                _, continue_, break_ = self.make_loop_labels(label)
                self.instructions.append(continue_)
                self.emit_conditional_jump(cond, f"break_{label}")
                self.emit_statement(body)
                self.instructions.append(IRJump(f"continue_{label}"))
                self.instructions.append(break_)
            case DoWhile(body, cond, label):
                start, continue_, break_ = self.make_loop_labels(label)
                self.instructions.append(start)
                self.emit_statement(body)
                self.instructions.append(continue_)
                self.emit_conditional_jump(cond, f"start_{label}", True)
                self.instructions.append(break_)
            case For(init, cond, post, body, label):
                start, continue_, break_ = self.make_loop_labels(label)
                self.emit_for_init(init)
                self.instructions.append(start)
                if cond is not None:
                    self.emit_conditional_jump(cond, f"break_{label}")
                self.emit_statement(body)
                self.instructions.append(continue_)
                if post is not None:
                    self.emit_exp(post)
                self.instructions.append(IRJump(f"start_{label}"))
                self.instructions.append(break_)

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
            case Compound(block):
                self.emit_block(block)
            case Break(label):
                self.instructions.append(IRJump(f"break_{label}"))
            case Continue(label):
                self.instructions.append(IRJump(f"continue_{label}"))
            case While() | DoWhile() | For():
                self.emit_loop(statement)
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

    def emit_block(self, block):
        for block_item in block.block_items:
            self.emit_block_item(block_item)
        return self.instructions
    
    def emit_function(self, ast_node):
        instructions = self.emit_block(ast_node.body)
        instructions.append(IRReturn(IRConstant(0)))
        return IRFunctionDefinition(ast_node.name, instructions)
    
    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
