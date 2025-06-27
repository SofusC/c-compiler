from __future__ import annotations
from ..c_ast import *
from ..utils import log

symbol_table: dict[str, SymbolEntry] = {}

class Int:
    pass

@dataclass
class FunType:
    param_count: int

Types = Int | FunType

class Tentative:
    pass
@dataclass
class Initial:
    int: int
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
    type: Types
    defined: bool | None = None
    attrs: IdentifierAttr | None = None

@log("Typechecking:")
def typecheck_program(program):
    for decl in program.declarations:
        typecheck_file_scope_declaration(decl)

@log
def typecheck_file_scope_declaration(decl):
    match decl:
        case FunDecl(fun_decl):
            typecheck_function_declaration(fun_decl)
        case VarDecl(var_decl):
            typecheck_file_scope_variable_declaration(var_decl)
        case _:
            raise RuntimeError(f"Cannot typecheck declaration {decl}")

@log
def typecheck_function_declaration(decl: FunctionDeclaration):
    fun_type = FunType(len(decl.params))
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
        for param in decl.params:
            symbol_table[param] = SymbolEntry(Int())
        typecheck_block(decl.body)

@log
def typecheck_file_scope_variable_declaration(var_decl: VariableDeclaration):
    if isinstance(var_decl.init, Constant):
        initial_value = Initial(var_decl.init)
    elif var_decl.init is None:
        if var_decl.storage_class == StorageClass.extern:
            initial_value = NoInitializer()
        else:
            initial_value = Tentative()
    else:
        raise RuntimeError(f"Non-constant initializer {var_decl.init}")
    
    global_ = var_decl.storage_class != StorageClass.static

    if var_decl.name in symbol_table:
        old_decl = symbol_table[var_decl.name]
        if not isinstance(old_decl.type, Int):
            raise RuntimeError(f"Function redeclared as variable {var_decl}")
        if var_decl.storage_class == StorageClass.extern:
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
    symbol_table[var_decl.name] = SymbolEntry(
        type = Int(), 
        attrs = attrs)

@log
def typecheck_block(block):
    for block_item in block.block_items:
        typecheck_block_item(block_item)

@log
def typecheck_block_item(item):
    match item:
        case D(decl):
            typecheck_local_declaration(decl)
        case S(stmt):
            typecheck_statement(stmt)
        case _:
            raise RuntimeError(f"Cannot typecheck block item {item}")
        
@log
def typecheck_local_declaration(decl):
    match decl:
        case FunDecl(fun_decl):
            typecheck_function_declaration(fun_decl)
        case VarDecl(var_decl):
            typecheck_local_variable_declaration(var_decl)
        case _:
            raise RuntimeError(f"Cannot typecheck declaration {decl}")

@log
def typecheck_local_variable_declaration(var_decl: VariableDeclaration):
    if var_decl.storage_class == StorageClass.extern:
        if var_decl.init is not None:
            raise RuntimeError(f"Initializer on local extern variable declaration {var_decl}")
        if var_decl.name in symbol_table:
            old_decl = symbol_table[var_decl.name]
            if not isinstance(old_decl.type, Int):
                raise RuntimeError(f"Function redeclared as variable {var_decl}")
        else:
            symbol_table[var_decl.name] = SymbolEntry(
                type = Int(),
                attrs = StaticAttr(init = NoInitializer(), global_ = True)
            )
    elif var_decl.storage_class == StorageClass.static:
        if isinstance(var_decl.init, Constant):
            initial_value = var_decl.init
        elif var_decl.init is None:
            initial_value = Initial(0)
        else:
            raise RuntimeError(f"Non-constant initializer on local static variable {var_decl}")
        symbol_table[var_decl.name] = SymbolEntry(
            type = Int(),
            attrs = StaticAttr(init = initial_value, global_ = False)
        )
    else:
        symbol_table[var_decl.name] = SymbolEntry(
            type = Int(),
            attrs = LocalAttr())
    if var_decl.init is not None:
        typecheck_exp(var_decl.init)

@log
def typecheck_statement(stmt):
    match stmt:
        case Return(exp) | Expression(exp):
            typecheck_exp(exp)
        case If(cond, then, else_):
            typecheck_exp(cond)
            typecheck_statement(then)
            if else_:
                typecheck_statement(else_)
        case Compound(block):
            typecheck_block(block)
        case Break() | Continue() | Null():
            pass
        case While(cond, body, _) | DoWhile(body, cond, _):
            typecheck_exp(cond)
            typecheck_statement(body)
        case For(init, cond, post, body, _):
            typecheck_for_init(init)
            if cond:
                typecheck_exp(cond)
            if post:
                typecheck_exp(post)
            typecheck_statement(body)
        case _:
            raise RuntimeError(f"Cannot typecheck statement {stmt}")

@log
def typecheck_for_init(init):
    match init:
        case InitDecl(decl):
            if decl.storage_class is not None:
                raise RuntimeError(f"Cannot have storage class specifier in for init {decl}")
            typecheck_local_variable_declaration(decl)
        case InitExp(None):
            pass
        case InitExp(exp):
            typecheck_exp(exp)
        case _:
            raise RuntimeError(f"Cannot typecheck for init {init}")

@log
def typecheck_exp(exp):
    match exp:
        case Constant():
            pass
        case Unary(_, exp):
            typecheck_exp(exp)
        case Binary(_, left, right) | Assignment(left, right):
            typecheck_exp(left)
            typecheck_exp(right)
        case Conditional(cond, then, else_):
            typecheck_exp(cond)
            typecheck_exp(then)
            typecheck_exp(else_)
        case FunctionCall(identifier, args):
            f_type = symbol_table[identifier].type
            if isinstance(f_type, Int):
                raise RuntimeError(f"Variable used as function name {identifier}")
            if f_type.param_count != len(args):
                raise RuntimeError(f"Function {identifier} called with wrong number of arguments, expected {f_type.param_count}, found {len(args)}")
            for arg in args:
                typecheck_exp(arg)
        case Var(v):
            if not isinstance(symbol_table[v].type, Int):
                raise RuntimeError(f"Function name {v} used as variable")
        case _:
            raise RuntimeError(f"Cannot typecheck exp {exp}")