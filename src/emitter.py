from .ir_ast import *
from .c_ast import *
from .utils import NameGenerator, log
from copy import deepcopy
from typing import Any, List, Optional
from .semantic_analysis.typechecker import symbol_table, StaticAttr, Initial, Tentative, NoInitializer, get_type, SymbolEntry, LocalAttr


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

@log
def make_tacky_variable(var_type: Type) -> IRVar:
    var_name = NameGenerator.make_temporary()
    symbol_table[var_name] = SymbolEntry(type = var_type, attrs = LocalAttr())
    return IRVar(var_name)

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

@log
def emit_unary_instructions(instructions: List[IRInstruction], result_type: Type, unop: UnaryOperator, exp: Exp) -> IRVar:
    src = emit_exp(instructions, exp)
    dst = make_tacky_variable(result_type)
    tacky_op = emit_unary_operator(unop)
    instructions.append(IRUnary(tacky_op,src,dst))
    return dst

@log
def emit_short_circuit_instructions(instructions: List[IRInstruction], result_type: Type, binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
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
    result = make_tacky_variable(result_type)
    end_label = NameGenerator.make_label("end_sc")

    instructions.extend([
        IRCopy(IRConstant(ConstInt(1 - short_circuit_value)), result),
        IRJump(end_label),
        IRLabel(sc_label),
        IRCopy(IRConstant(ConstInt(short_circuit_value)), result),
        IRLabel(end_label),
    ])

    return result
    
@log
def emit_binary_instructions(instructions: List[IRInstruction], result_type: Type, binop: BinaryOperator, e1: Exp, e2: Exp) -> IRVar:
    v1 = emit_exp(instructions, e1)
    v2 = emit_exp(instructions, e2)
    dst = make_tacky_variable(result_type)
    tacky_op = emit_binary_operator(binop)
    instructions.append(IRBinary(tacky_op, v1, v2, dst))
    return dst

@log
def emit_function_call(instructions: List[IRInstruction], result_type: Type, identifier: str, args: List[Exp]) -> IRVar:
    new_args = [emit_exp(instructions, arg) for arg in args]
    result = make_tacky_variable(result_type)
    instructions.append(IRFunCall(identifier, new_args, result))
    return result

@log
def emit_cast(instructions: List[IRInstruction], target_type: Type, inner_exp: Exp) -> IRVar:
    result = emit_exp(instructions, inner_exp)
    if target_type == get_type(inner_exp):
        return result
    dst = make_tacky_variable(target_type)
    if target_type == Long():
        instructions.append(IRSignExtend(result, dst))
    elif target_type == Int():
        instructions.append(IRTruncate(result, dst))
    else:
        raise RuntimeError(f"Compiler error, cant emit for cast to type {target_type}")
    return dst
        
@log
def emit_exp(instructions: List[IRInstruction], ast_node: Exp) -> IRVal:
    match ast_node:
        case Constant(constant):
            return IRConstant(constant)
        case Unary(unop, exp):
            return emit_unary_instructions(instructions, get_type(ast_node), unop, exp)
        case Binary(BinaryOperator.And | BinaryOperator.Or as binop, e1, e2):
            return emit_short_circuit_instructions(instructions, get_type(ast_node), binop, e1, e2)
        case Binary(binop, e1, e2):
            return emit_binary_instructions(instructions, get_type(ast_node), binop, e1, e2)
        case Var(v):
            return IRVar(v)
        case Assignment(Var(v), rhs):
            result = emit_exp(instructions, rhs)
            lhs = IRVar(v)
            instructions.append(IRCopy(result, lhs))
            return lhs
        case Conditional(cond, then, else_):
            return emit_conditional(instructions, get_type(ast_node), cond, then, else_)
        case FunctionCall(identifier, args):
            return emit_function_call(instructions, get_type(ast_node), identifier, args)
        case Cast(target_type, inner):
            return emit_cast(instructions, target_type, inner)
        case _:
            raise RuntimeError(f"Expression {ast_node} not implemented")

@log      
def emit_conditional(instructions: List[IRInstruction], result_type: Type, cond: Exp, then: Exp, else_: Exp) -> IRVar:
    # Evaluate condition
    cond_tmp = emit_exp_to_temp(instructions, cond)

    result = make_tacky_variable(result_type)

    else_label = NameGenerator.make_label("else")
    end_label = NameGenerator.make_label("end")

    # Conditional jump to else
    instructions.append(IRJumpIfZero(cond_tmp, else_label))

    # Then branch
    then_tmp = emit_exp_to_temp(instructions, then)
    instructions.append(IRCopy(then_tmp, result))
    instructions.append(IRJump(end_label))

    # Else branch
    instructions.append(IRLabel(else_label))
    else_tmp = emit_exp_to_temp(instructions, else_)
    instructions.append(IRCopy(else_tmp, result))

    instructions.append(IRLabel(end_label))
    return result

@log
def emit_exp_to_temp(instructions: List[IRInstruction], exp: Exp) -> IRVar:
    exp_val = emit_exp(instructions, exp)
    exp_tmp = make_tacky_variable(get_type(exp))
    instructions.append(IRCopy(exp_val, exp_tmp))
    return exp_tmp

@log
def emit_if(instructions: List[IRInstruction], cond: Exp, then: Statement, else_: Optional[Statement]) -> None:
    # Evaluate condition
    cond_tmp = emit_exp_to_temp(instructions, cond)

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

@log
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

@log
def emit_conditional_jump(instructions: List[IRInstruction], cond: Exp, jump_label: str, invert: bool = False) -> None:
    v = emit_exp_to_temp(instructions, cond)
    if invert:
        instructions.append(IRJumpIfNotZero(v, jump_label))
    else:
        instructions.append(IRJumpIfZero(v, jump_label))

@log
def make_loop_labels(label: str) -> tuple[IRLabel, IRLabel, IRLabel]:
    return (
        IRLabel(f"start_{label}"),
        IRLabel(f"continue_{label}"),
        IRLabel(f"break_{label}")
    )

@log
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

@log
def emit_variable_declaration(instructions: List[IRInstruction], decl: VariableDeclaration) -> Optional[IRVar]:
    if decl.storage_class is not None:
        return None
    if decl.init is None:
        return None
    result = emit_exp(instructions, decl.init)
    lhs = IRVar(decl.name)
    instructions.append(IRCopy(result, lhs))
    return lhs

@log
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

@log
def emit_declaration(instructions: List[IRInstruction], decl: Declaration) -> None:
    match decl:
        case FunDecl(fun_decl):
            emit_function_declaration(fun_decl)
        case VarDecl(var_decl):
            emit_variable_declaration(instructions, var_decl)
        case _:
            raise RuntimeError(f"Declaration {decl} not implemented")

@log
def emit_block_item(instructions: List[IRInstruction], item: BlockItem) -> None:
    match item:
        case D(declaration):
            emit_declaration(instructions, declaration)
        case S(statement):
            emit_statement(instructions, statement)
        case _:
            raise RuntimeError(f"BlockItem {item} not implemented")

@log
def emit_block(instructions: List[IRInstruction], block: Block) -> None:
    for block_item in block.block_items:
        emit_block_item(instructions, block_item)

@log
def emit_function_declaration(fun_decl: FunctionDeclaration) -> Optional[IRFunctionDefinition]:
    if fun_decl.body is None:
        return
    instructions = []
    emit_block(instructions, fun_decl.body)
    instructions.append(IRReturn(IRConstant(ConstInt(0))))
    global_ = symbol_table[fun_decl.name].attrs.global_
    return IRFunctionDefinition(fun_decl.name, global_, fun_decl.params, deepcopy(instructions))

@log
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
        type_, attrs = entry.type, entry.attrs
        if not isinstance(attrs, StaticAttr):
            continue

        init, is_global = attrs.init, attrs.global_

        match init:
            case Initial(value):
                value = value
            case Tentative():
                if type_ == Int():
                    value = ConstInt(0) 
                elif type_ == Long(): 
                    value = ConstLong(0)
                else:
                    raise RuntimeError(f"Compiler error, cant convert to tacky symbol for {type_}")
            case NoInitializer():
                continue

        tacky_defs.append(IRStaticVariable(name, is_global, type_, value))
    return tacky_defs

#TODO: Move this method to top of file, and so on with the other methods
#TODO: Add logging?
@log("Emitting TACKY:")
def emit_program(program: Program) -> IRProgram:
    toplevels = [toplevel for decl in program.declarations if (toplevel := emit_toplevel(decl)) is not None]
    toplevels.extend(convert_symbols_to_tacky())
    return IRProgram(toplevels)
