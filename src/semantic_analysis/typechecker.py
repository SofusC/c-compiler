from __future__ import annotations
from ..c_ast import *
from ..utils import log

symbol_table: dict[str, SymbolEntry] = {}


@dataclass
class IntInit:
    int: int
@dataclass
class LongInit:
    int: int

StaticInit = IntInit | LongInit

class Tentative:
    pass
@dataclass
class Initial:
    init: StaticInit
class NoInitializer:
    pass

InitialValue = Tentative | Initial | NoInitializer

@dataclass
class FunAttr:
    defined: bool
    global_: bool
@dataclass
class StaticAttr:
    init: InitialValue
    global_: bool
class LocalAttr:
    pass

IdentifierAttr = FunAttr | StaticAttr | LocalAttr

@dataclass
class SymbolEntry:
    type: Type
    defined: bool | None = None
    attrs: IdentifierAttr | None = None

@log
def typecheck_function_declaration(decl: FunctionDeclaration):
    fun_type = decl.fun_type
    has_body = decl.body is not None
    already_defined = False
    global_decl = decl.storage_class != StorageClass.static

    if decl.name in symbol_table:
        old_decl = symbol_table[decl.name]
        if old_decl.type != fun_type:
            raise RuntimeError(f"Incompatible function declarations {fun_type} and {old_decl.type}")
        already_defined = old_decl.defined
        if already_defined and has_body:
            raise RuntimeError(f"Function is defined more than once {decl}")
        if old_decl.attrs.global_ and decl.storage_class == StorageClass.static:
            raise RuntimeError(f"Static function declaration {decl} follows non-static {old_decl}")
        global_decl = old_decl.attrs.global_

    attrs = FunAttr(defined=(already_defined or has_body), global_ = global_decl)
    symbol_table[decl.name] = SymbolEntry(
        type = fun_type, 
        defined = already_defined or has_body,
        attrs = attrs
    )
    if has_body:
        for param, param_type in zip(decl.params, fun_type.params):
            symbol_table[param] = SymbolEntry(param_type)
        typecheck_block(decl.body, fun_type.ret)

@log
def typecheck_file_scope_variable_declaration(var_decl: VariableDeclaration):
    name, init, type_, storage_class = var_decl.name, var_decl.init, var_decl.var_type, var_decl.storage_class
    if isinstance(init, Constant):
        initial_value = resolve_const_init(init)
    elif var_decl.init is None:
        if storage_class == StorageClass.extern:
            initial_value = NoInitializer()
        else:
            initial_value = Tentative()
    else:
        raise RuntimeError(f"Non-constant initializer {init}")
    
    global_ = storage_class != StorageClass.static

    if name in symbol_table:
        old_decl = symbol_table[name]
        if old_decl.type != type_:
            raise RuntimeError(f"Conflicting types of variable {name}: {old_decl.type} and {type_}")
        if storage_class == StorageClass.extern:
            global_ = old_decl.attrs.global_
        elif old_decl.attrs.global_ != global_:
            raise RuntimeError(f"Conflicting variable linkage between {old_decl} and {var_decl}")
        
        if isinstance(old_decl.attrs.init, Initial):
            if isinstance(initial_value, Initial):
                raise RuntimeError(f"Conflicting file scope variable declarations with initializers {old_decl.attrs.init} and {initial_value}")
            else:
                initial_value = old_decl.attrs.init
        elif not isinstance(initial_value, Initial) and isinstance(old_decl.attrs.init, Tentative):
            initial_value = Tentative()
    attrs = StaticAttr(init = initial_value, global_ = global_)
    symbol_table[name] = SymbolEntry(
        type = type_, 
        attrs = attrs)

@log
def typecheck_local_variable_declaration(var_decl: VariableDeclaration):
    name, init, type_, storage_class = var_decl.name, var_decl.init, var_decl.var_type, var_decl.storage_class
    if storage_class == StorageClass.extern:
        if init is not None:
            raise RuntimeError(f"Initializer on local extern variable declaration {var_decl}")
        if name in symbol_table:
            old_decl = symbol_table[name]
            if old_decl.type != type_:
                raise RuntimeError(f"Conflicting types of variable {name}: {old_decl.type} and {type_}")
        else:
            symbol_table[name] = SymbolEntry(
                type = type_,
                attrs = StaticAttr(init = NoInitializer(), global_ = True)
            )
    elif storage_class == StorageClass.static:
        if init is None:
            initial_value = Initial(IntInit(0))
        elif isinstance(init, Constant):
            initial_value = resolve_const_init(init)
        else:
            raise RuntimeError(f"Non-constant initializer on local static variable {var_decl}")
        symbol_table[name] = SymbolEntry(
            type = type_,
            attrs = StaticAttr(init = initial_value, global_ = False)
        )
    else:
        symbol_table[name] = SymbolEntry(
            type = type_,
            attrs = LocalAttr())
        if init is not None:
            typecheck_exp(init)
            set_type(init, type_)
    
@log
def typecheck_for_init_decl(decl: VariableDeclaration):
    if decl.storage_class is not None:
        raise RuntimeError(f"Cannot have storage class specifier in for init {decl}")
    typecheck_local_variable_declaration(decl)

@log
def typecheck_variable(var: Var):
    v_type = symbol_table[var.identifier].type
    if isinstance(v_type, FunType):
        raise RuntimeError(f"Function name {var.identifier} used as variable")
    set_type(var, v_type)

@log
def typecheck_constant(constant: Constant):
    match constant.constant:
        case ConstInt(i):
            set_type(constant, Int())
        case ConstLong(l):
            set_type(constant, Long())

@log
def typecheck_cast(cast: Cast):
    typecheck_exp(cast.exp)
    set_type(cast, cast.target_type)

@log
def typecheck_unary(unary: Unary):
    typecheck_exp(unary.exp)
    if unary.unary_operator.is_logical:
        set_type(unary, Int())
    else:
        set_type(unary, get_type(unary.exp))

@log
def typecheck_binary(binary: Binary):
    typecheck_exp(binary.left_exp)
    typecheck_exp(binary.right_exp)
    if binary.binary_operator.is_logical:
        set_type(binary, Int())
        return
    t1 = get_type(binary.left_exp)
    t2 = get_type(binary.right_exp)
    common_type = get_common_type(t1, t2)
    binary.left_exp = convert_to(binary.left_exp, common_type)
    binary.right_exp = convert_to(binary.right_exp, common_type)
    if binary.binary_operator.is_arithmetic:
        set_type(binary, common_type)
    else:
        set_type(binary, Int())
    
@log
def typecheck_assignment(assignment: Assignment):
    typecheck_exp(assignment.left)
    typecheck_exp(assignment.right)
    left_type = get_type(assignment.left)
    assignment.right = convert_to(assignment.right, left_type)
    set_type(assignment, left_type)

@log
def typecheck_conditional(conditional: Conditional):
    typecheck_exp(conditional.condition)
    typecheck_exp(conditional.then_exp)
    typecheck_exp(conditional.else_exp)
    then_type = get_type(conditional.then_exp)
    else_type = get_type(conditional.else_exp)
    common_type = get_common_type(then_type, else_type)
    conditional.then_exp = convert_to(conditional.then_exp, common_type)
    conditional.else_exp = convert_to(conditional.else_exp, common_type)
    set_type(conditional, common_type)

@log
def typecheck_function_call(func_call: FunctionCall):
    f_type = symbol_table[func_call.identifier].type
    if not isinstance(f_type, FunType):
        raise RuntimeError(f"Variable used as function name {func_call.identifier}")
    if len(f_type.params) != len(func_call.args):
        raise RuntimeError(f"Function {func_call.identifier} called with wrong number of arguments, expected {len(f_type.params)}, found {len(func_call.args)}")
    converted_args = []
    for arg, param_type in zip(func_call.args, f_type.params):
        typecheck_exp(arg)
        converted_args.append(convert_to(arg, param_type))
    func_call.args = converted_args
    set_type(func_call, f_type.ret)

@log
def typecheck_return(return_stmt: Return, fun_ret_type: Type):
    typecheck_exp(return_stmt.exp)
    return_stmt.exp = convert_to(return_stmt.exp, fun_ret_type)
    
@log
def set_type(exp: Exp, type: Type):
    exp.type = type

@log
def get_type(exp: Exp):
    return exp.type

@log
def get_common_type(type1: Type, type2: Type):
    if type1 == type2:
        return type1
    else:
        return Long()
    
@log
def convert_to(exp: Exp, type: Type):
    if get_type(exp) == type:
        return exp
    cast_exp = Cast(type, exp)
    set_type(cast_exp, type)
    return cast_exp

@log 
def static_type_conversion(value: int, to_type):
    if not isinstance(to_type, Int):
        raise RuntimeError(f"Compiler error: cannot statically convert to type {to_type}")

    return ((value + 2**31) % 2**32) - 2**31

@log
def resolve_const_init(constant: Constant):
    match constant.constant:
        case ConstInt(i):
            initial_value = Initial(IntInit(static_type_conversion(i, Int())))
        case ConstLong(l):
            initial_value = Initial(LongInit(l))
        case _:
            raise RuntimeError(f"Compiler error, cant typecheck {constant}")
    return initial_value


@log("Typechecking:")
def typecheck_program(program: Program):
    for decl in program.declarations:
        typecheck_file_scope_declaration(decl)

@log
def typecheck_file_scope_declaration(decl: Declaration):
    typecheck_declaration(decl, False)

@log
def typecheck_local_declaration(decl: Declaration):
    typecheck_declaration(decl, True)
        
@log
def typecheck_declaration(decl: Declaration, is_local: bool):
    match decl:
        case FunDecl(fun_decl):
            typecheck_function_declaration(fun_decl)
        case VarDecl(var_decl):
            if is_local:
                typecheck_local_variable_declaration(var_decl)
            else:
                typecheck_file_scope_variable_declaration(var_decl)
        case _:
            raise RuntimeError(f"Cannot typecheck declaration {decl}")

@log
def typecheck_block(block: Block, fun_ret_type: Type):
    for block_item in block.block_items:
        typecheck_block_item(block_item, fun_ret_type)

@log
def typecheck_block_item(item: BlockItem, fun_ret_type: Type):
    match item:
        case D(decl):
            typecheck_local_declaration(decl)
        case S(stmt):
            typecheck_statement(stmt, fun_ret_type)
        case _:
            raise RuntimeError(f"Cannot typecheck block item {item}")
        
@log
def typecheck_statement(stmt: Statement, fun_ret_type: Type):
    match stmt:
        case Return():
            typecheck_return(stmt, fun_ret_type)
        case Expression(exp):
            typecheck_exp(exp)
        case If(cond, then, else_):
            typecheck_exp(cond)
            typecheck_statement(then, fun_ret_type)
            if else_:
                typecheck_statement(else_, fun_ret_type)
        case Compound(block):
            typecheck_block(block, fun_ret_type)
        case Break() | Continue() | Null():
            pass
        case While(cond, body, _) | DoWhile(body, cond, _):
            typecheck_exp(cond)
            typecheck_statement(body, fun_ret_type)
        case For(init, cond, post, body, _):
            typecheck_for_init(init)
            if cond:
                typecheck_exp(cond)
            if post:
                typecheck_exp(post)
            typecheck_statement(body, fun_ret_type)
        case _:
            raise RuntimeError(f"Cannot typecheck statement {stmt}")

@log
def typecheck_for_init(init: ForInit):
    match init:
        case InitDecl(decl):
            typecheck_for_init_decl(decl)
        case InitExp(None):
            pass
        case InitExp(exp):
            typecheck_exp(exp)
        case _:
            raise RuntimeError(f"Cannot typecheck for init {init}")

@log
def typecheck_exp(exp: Exp):
    match exp:
        case Constant():
            typecheck_constant(exp)
        case Unary():
            typecheck_unary(exp)
        case Binary():
            typecheck_binary(exp)
        case Assignment():
            typecheck_assignment(exp)
        case Conditional():
            typecheck_conditional(exp)
        case FunctionCall():
            typecheck_function_call(exp)
        case Var():
            typecheck_variable(exp)
        case Cast():
            typecheck_cast(exp)
        case _:
            raise RuntimeError(f"Cannot typecheck exp {exp}")
