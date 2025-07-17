from .ir_ast import *
from .c_ast import *
from .utils import NameGenerator
from copy import deepcopy
from typing import Any, List, Optional
from .semantic_analysis.typechecker import symbol_table, StaticAttr, Initial, Tentative, NoInitializer

_UNOP_MAP = {
    UnaryOperator.Complement     : IRUnaryOperator.Complement,
    UnaryOperator.Negate         : IRUnaryOperator.Negate,
    UnaryOperator.Not            : IRUnaryOperator.Not,
}
_BINOP_MAP = {
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

def emit_binary_operator(ast_node: BinaryOperator) -> IRBinaryOperator:
    try:
        return _BINOP_MAP[ast_node]
    except KeyError:
        raise RuntimeError(f"Binary operator {ast_node} not implemented")

def emit_unary_operator(ast_node: UnaryOperator) -> IRUnaryOperator:
    try:
        return _UNOP_MAP[ast_node]
    except KeyError:
        raise RuntimeError(f"Unary operator {ast_node} not implemented")

def emit_unary_instructions(instructions: List[IRInstruction], unop: UnaryOperator, exp: Exp) -> IRVar:
    src = emit_exp(instructions, exp)
    dst = IRVar(NameGenerator.make_temporary())
    tacky_op = emit_unary_operator(unop)
    instructions.append(IRUnary(tacky_op,src,dst))
    return dst

def emit_short_circuit_instructions(instructions: List[IRInstruction], binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
    if binop == BinaryOperator.And:
        short_circuit_value = 0
        jump_instr = IRJumpIfZero
    elif binop == BinaryOperator.Or:
        short_circuit_value = 1
        jump_instr = IRJumpIfNotZero

    # Evaluate first expression
    val1 = emit_exp(instructions, e1)
    sc_label = NameGenerator.make_label(f"sc_{binop.name.lower()}")
    instructions.append(jump_instr(val1, sc_label))

    # Evaluate second expression only if needed
    val2 = emit_exp(instructions, e2)
    instructions.append(jump_instr(val2, sc_label))

    # Compute the result
    result = IRVar(NameGenerator.make_temporary())
    end_label = NameGenerator.make_label("end_sc")

    instructions.extend([
        IRCopy(IRConstant(1 - short_circuit_value), result),
        IRJump(end_label),
        IRLabel(sc_label),
        IRCopy(IRConstant(short_circuit_value), result),
        IRLabel(end_label),
    ])

    return result
    
def emit_binary_instructions(instructions: List[IRInstruction], binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
    v1 = emit_exp(instructions, e1)
    v2 = emit_exp(instructions, e2)
    dst = IRVar(NameGenerator.make_temporary())
    tacky_op = emit_binary_operator(binop)
    instructions.append(IRBinary(tacky_op, v1, v2, dst))
    return dst

def emit_function_call(instructions: List[IRInstruction], identifier: str, args: List[Exp]) -> IRVar:
    new_args = [emit_exp(instructions, arg) for arg in args]
    result = IRVar(NameGenerator.make_temporary())
    instructions.append(IRFunCall(identifier, new_args, result))
    return result
        
def emit_exp(instructions: List[IRInstruction], ast_node: Exp) -> IRVal:
    match ast_node:
        case Constant(constant):
            return IRConstant(constant)
        case Unary(unop, exp):
            return emit_unary_instructions(instructions, unop, exp)
        case Binary(BinaryOperator.And | BinaryOperator.Or as binop, e1, e2):
            return emit_short_circuit_instructions(instructions, binop, e1, e2)
        case Binary(binop, e1, e2):
            return emit_binary_instructions(instructions, binop, e1, e2)
        case Var(v):
            return IRVar(v)
        case Assignment(Var(v), rhs):
            result = emit_exp(instructions, rhs)
            lhs = IRVar(v)
            instructions.append(IRCopy(result, lhs))
            return lhs
        case Conditional(cond, then, else_):
            return emit_conditional(instructions, cond, then, else_)
        case FunctionCall(identifier, args):
            return emit_function_call(instructions, identifier, args)
        case _:
            raise RuntimeError(f"Expression {ast_node} not implemented")
        
def emit_conditional(instructions: List[IRInstruction], cond: Exp, then: Exp, else_: Exp) -> IRVar:
    # Evaluate condition
    cond_val = emit_exp(instructions, cond)
    cond_tmp = IRVar(NameGenerator.make_temporary())
    instructions.append(IRCopy(cond_val, cond_tmp))

    result = IRVar(NameGenerator.make_temporary())

    else_label = NameGenerator.make_label("else")
    end_label = NameGenerator.make_label("end")

    # Conditional jump to else
    instructions.append(IRJumpIfZero(cond_tmp, else_label))

    # Then branch
    then_val = emit_exp(instructions, then)
    then_tmp = IRVar(NameGenerator.make_temporary())
    instructions.append(IRCopy(then_val, then_tmp))
    instructions.append(IRCopy(then_tmp, result))
    instructions.append(IRJump(end_label))

    # Else branch
    instructions.append(IRLabel(else_label))
    else_val = emit_exp(instructions, else_)
    else_tmp = IRVar(NameGenerator.make_temporary())
    instructions.append(IRCopy(else_val, else_tmp))
    instructions.append(IRCopy(else_tmp, result))

    instructions.append(IRLabel(end_label))
    return result

def emit_if(instructions: List[IRInstruction], cond: Exp, then: Statement, else_: Optional[Statement]) -> None:
    # Evaluate condition
    cond_val = emit_exp(instructions, cond)
    cond_tmp = IRVar(NameGenerator.make_temporary())
    instructions.append(IRCopy(cond_val, cond_tmp))

    end_label = NameGenerator.make_label("end")

    if else_ is None:
        instructions.append(IRJumpIfZero(cond_tmp, end_label))
        emit_statement(instructions, then)
    else:
        # With else branch
        else_label = NameGenerator.make_label("else")
        instructions.append(IRJumpIfZero(cond_tmp, else_label))
        emit_statement(instructions, then)
        instructions.append(IRJump(end_label))
        instructions.append(IRLabel(else_label))
        emit_statement(instructions, else_)

    instructions.append(IRLabel(end_label))  

def emit_for_init(instructions: List[IRInstruction], for_init: ForInit) -> Optional[Any]: # TODO: return none?
    match for_init:
        case InitDecl(decl):
            return emit_variable_declaration(instructions, decl)
        case InitExp(None):
            pass
        case InitExp(exp):
            return emit_exp(instructions, exp)
        case _:
            raise RuntimeError(f"ForInit {for_init} not implemented")

def emit_conditional_jump(instructions: List[IRInstruction], cond: Exp, jump_label: str, invert: bool = False) -> None:
    result = emit_exp(instructions, cond)
    v = IRVar(NameGenerator.make_temporary())
    instructions.append(IRCopy(result, v))
    if invert:
        instructions.append(IRJumpIfNotZero(v, jump_label))
    else:
        instructions.append(IRJumpIfZero(v, jump_label))

def make_loop_labels(label: str) -> tuple[IRLabel, IRLabel, IRLabel]:
    return (
        IRLabel(f"start_{label}"),
        IRLabel(f"continue_{label}"),
        IRLabel(f"break_{label}")
    )

def emit_loop(instructions: List[IRInstruction], loop: While | DoWhile | For) -> None:
    match loop:
        case While(cond, body, label):
            _, continue_, break_ = make_loop_labels(label)
            instructions.append(continue_)
            emit_conditional_jump(instructions, cond, f"break_{label}")
            emit_statement(instructions, body)
            instructions.append(IRJump(f"continue_{label}"))
            instructions.append(break_)
        case DoWhile(body, cond, label):
            start, continue_, break_ = make_loop_labels(label)
            instructions.append(start)
            emit_statement(instructions, body)
            instructions.append(continue_)
            emit_conditional_jump(instructions, cond, f"start_{label}", True)
            instructions.append(break_)
        case For(init, cond, post, body, label):
            start, continue_, break_ = make_loop_labels(label)
            emit_for_init(instructions, init)
            instructions.append(start)
            if cond is not None:
                emit_conditional_jump(instructions, cond, f"break_{label}")
            emit_statement(instructions, body)
            instructions.append(continue_)
            if post is not None:
                emit_exp(instructions, post)
            instructions.append(IRJump(f"start_{label}"))
            instructions.append(break_)

def emit_variable_declaration(instructions: List[IRInstruction], decl: VariableDeclaration) -> Optional[IRVar]:
    if decl.storage_class is not None:
        return None
    if decl.init is None:
        return None
    result = emit_exp(instructions, decl.init)
    lhs = IRVar(decl.name)
    instructions.append(IRCopy(result, lhs))
    return lhs

def emit_statement(instructions: List[IRInstruction], statement: Statement) -> None:
    match statement:
        case Return(exp):
            ret = emit_exp(instructions, exp)
            instructions.append(IRReturn(ret))
        case Expression(exp):
            emit_exp(instructions, exp)
        case If(cond, then, else_):
            emit_if(instructions, cond, then, else_)
        case Compound(block):
            emit_block(instructions, block)
        case Break(label):
            instructions.append(IRJump(f"break_{label}"))
        case Continue(label):
            instructions.append(IRJump(f"continue_{label}"))
        case While() | DoWhile() | For():
            emit_loop(instructions, statement)
        case Null():
            pass
        case _:
            raise RuntimeError(f"Statement {statement} not implemented")

def emit_declaration(instructions: List[IRInstruction], decl: Declaration) -> None:
    match decl:
        case FunDecl(fun_decl):
            emit_function_declaration(fun_decl)
        case VarDecl(var_decl):
            emit_variable_declaration(instructions, var_decl)
        case _:
            raise RuntimeError(f"Declaration {decl} not implemented")

def emit_block_item(instructions: List[IRInstruction], item: BlockItem) -> None:
    match item:
        case D(declaration):
            emit_declaration(instructions, declaration)
        case S(statement):
            emit_statement(instructions, statement)
        case _:
            raise RuntimeError(f"BlockItem {item} not implemented")

def emit_block(instructions: List[IRInstruction], block: Block) -> None:
    for block_item in block.block_items:
        emit_block_item(instructions, block_item)

def emit_function_declaration(fun_decl: FunctionDeclaration) -> Optional[IRFunctionDefinition]:
    if fun_decl.body is None:
        return
    instructions = []
    emit_block(instructions, fun_decl.body)
    instructions.append(IRReturn(IRConstant(0)))
    global_ = symbol_table[fun_decl.name].attrs.global_
    return IRFunctionDefinition(fun_decl.name, global_, fun_decl.params, deepcopy(instructions))

def emit_toplevel(decl: Declaration) -> Optional[IRFunctionDefinition]:
    match decl:
        case FunDecl(fun_decl):
            return emit_function_declaration(fun_decl)
        case VarDecl():
            return None
        case _:
            raise RuntimeError(f"Declaration {decl} not implemented")
        
def convert_symbols_to_tacky():
    tacky_defs = []
    for name, entry in symbol_table.items():
        attrs = entry.attrs
        if not isinstance(attrs, StaticAttr):
            continue

        init, is_global = attrs.init, attrs.global_

        match init:
            case Initial(value):
                value = value
            case Tentative():
                value = 0
            case NoInitializer():
                continue

        tacky_defs.append(IRStaticVariable(name, is_global, value))
    return tacky_defs

#TODO: Move this method to top of file, and so on with the other methods
#TODO: Add logging?
def emit_program(program: Program) -> IRProgram:
    toplevels = [toplevel for decl in program.declarations if (toplevel := emit_toplevel(decl)) is not None]
    toplevels.extend(convert_symbols_to_tacky())
    return IRProgram(toplevels)
