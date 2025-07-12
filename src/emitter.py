from .ir_ast import *
from .c_ast import *
from .utils import NameGenerator
from copy import deepcopy
from typing import Any, List, Optional
from .semantic_analysis.typechecker import symbol_table, StaticAttr, Initial, Tentative, NoInitializer

class IREmitter:
    instructions = [] # TODO: Remove?

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
    
    def emit_binary_operator(self, ast_node: BinaryOperator) -> IRBinaryOperator:
        try:
            return self.binop_map[ast_node]
        except KeyError:
            raise RuntimeError(f"Binary operator {ast_node} not implemented")

    def emit_unary_operator(self, ast_node: UnaryOperator) -> IRUnaryOperator:
        try:
            return self.unop_map[ast_node]
        except KeyError:
            raise RuntimeError(f"Unary operator {ast_node} not implemented")
    
    def emit_unary_instructions(self, unop: UnaryOperator, exp: Exp) -> IRVar:
        src = self.emit_exp(exp)
        dst = IRVar(NameGenerator.make_temporary())
        tacky_op = self.emit_unary_operator(unop)
        self.instructions.append(IRUnary(tacky_op,src,dst))
        return dst
    
    def emit_short_circuit_instructions(self, binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
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
      
    def emit_binary_instructions(self, binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
        v1 = self.emit_exp(e1)
        v2 = self.emit_exp(e2)
        dst = IRVar(NameGenerator.make_temporary())
        tacky_op = self.emit_binary_operator(binop)
        self.instructions.append(IRBinary(tacky_op, v1, v2, dst))
        return dst
    
    def emit_function_call(self, identifier: str, args: List[Exp]) -> IRVar:
        new_args = [self.emit_exp(arg) for arg in args]
        result = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRFunCall(identifier, new_args, result))
        return result
            
    def emit_exp(self, ast_node: Exp) -> IRVal:
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
            case FunctionCall(identifier, args):
                return self.emit_function_call(identifier, args)
            case _:
                raise RuntimeError(f"Expression {ast_node} not implemented")
            
    def emit_conditional(self, cond: Exp, then: Exp, else_: Exp) -> IRVar:
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
    
    def emit_if(self, cond: Exp, then: Statement, else_: Optional[Statement]) -> None:
        # Evaluate condition
        cond_val = self.emit_exp(cond)
        cond_tmp = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(cond_val, cond_tmp))

        end_label = NameGenerator.make_label("end")

        if else_ is None:
            self.instructions.append(IRJumpIfZero(cond_tmp, end_label))
            self.emit_statement(then)
        else:
            # With else branch
            else_label = NameGenerator.make_label("else")
            self.instructions.append(IRJumpIfZero(cond_tmp, else_label))
            self.emit_statement(then)
            self.instructions.append(IRJump(end_label))
            self.instructions.append(IRLabel(else_label))
            self.emit_statement(else_)

        self.instructions.append(IRLabel(end_label))  

    def emit_for_init(self, for_init: ForInit) -> Optional[Any]: # TODO: return none?
        match for_init:
            case InitDecl(decl):
                return self.emit_variable_declaration(decl)
            case InitExp(None):
                pass
            case InitExp(exp):
                return self.emit_exp(exp)
            case _:
                raise RuntimeError(f"ForInit {for_init} not implemented")
    
    def emit_conditional_jump(self, cond: Exp, jump_label: str, invert: bool = False) -> None:
        result = self.emit_exp(cond)
        v = IRVar(NameGenerator.make_temporary())
        self.instructions.append(IRCopy(result, v))
        if invert:
            self.instructions.append(IRJumpIfNotZero(v, jump_label))
        else:
            self.instructions.append(IRJumpIfZero(v, jump_label))

    def make_loop_labels(self, label: str) -> tuple[IRLabel, IRLabel, IRLabel]:
        return (
            IRLabel(f"start_{label}"),
            IRLabel(f"continue_{label}"),
            IRLabel(f"break_{label}")
        )

    def emit_loop(self, loop: While | DoWhile | For) -> None:
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

    def emit_variable_declaration(self, decl: VariableDeclaration) -> Optional[IRVar]:
        if decl.storage_class is not None:
            return None
        if decl.init is None:
            return None
        result = self.emit_exp(decl.init)
        lhs = IRVar(decl.name)
        self.instructions.append(IRCopy(result, lhs))
        return lhs
            
    def emit_statement(self, statement: Statement) -> None:
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
    
    def emit_declaration(self, decl: Declaration) -> None:
        match decl:
            case FunDecl(fun_decl):
                self.emit_function_declaration(fun_decl)
            case VarDecl(var_decl):
                self.emit_variable_declaration(var_decl)
            case _:
                raise RuntimeError(f"Declaration {decl} not implemented")

    def emit_block_item(self, item: BlockItem) -> None:
        match item:
            case D(declaration):
                self.emit_declaration(declaration)
            case S(statement):
                self.emit_statement(statement)
            case _:
                raise RuntimeError(f"BlockItem {item} not implemented")

    def emit_block(self, block: Block):# -> List[IRInstruction]:
        for block_item in block.block_items:
            self.emit_block_item(block_item)
        #return self.instructions
    
    def emit_function_declaration(self, fun_decl: FunctionDeclaration) -> Optional[IRFunctionDefinition]:
        if fun_decl.body is None:
            return
        self.instructions = [] #TODO: Unclass, and use global variable?
        self.emit_block(fun_decl.body)
        self.instructions.append(IRReturn(IRConstant(0)))
        global_ = symbol_table[fun_decl.name].attrs.global_
        return IRFunctionDefinition(fun_decl.name, global_, fun_decl.params, deepcopy(self.instructions))

    def emit_toplevel(self, decl: Declaration) -> Optional[IRFunctionDefinition]:
        match decl:
            case FunDecl(fun_decl):
                return self.emit_function_declaration(fun_decl)
            case VarDecl():
                return None
            case _:
                raise RuntimeError(f"Declaration {decl} not implemented")
            
    def convert_symbols_to_tacky(self): #TODO: refactor
        tacky_defs = []
        for name, entry in symbol_table.items():
            match entry.attrs:
                case StaticAttr(init, global_):
                    match init:
                        case Initial(value):
                            tacky_defs.append(StaticVariable(name, global_, value))
                        case Tentative():
                            tacky_defs.append(StaticVariable(name, global_, 0))
                        case NoInitializer():
                            continue
                case _:
                    continue
        return tacky_defs

    def emit_program(self, program: Program) -> IRProgram:
        toplevels = [toplevel for decl in program.declarations if (toplevel := self.emit_toplevel(decl)) is not None]
        toplevels.extend(self.convert_symbols_to_tacky())
        return IRProgram(toplevels)
