from __future__ import annotations
from ..c_ast import *
from typing import NamedTuple
import copy
from ..utils import log, NameGenerator

class MapEntry(NamedTuple):
    name: str
    from_current_scope: bool
    has_linkage: bool

@log
def copy_identifier_map(identifier_map):
    result = copy.deepcopy(identifier_map)
    result = {k: MapEntry(v.name, False, v.has_linkage) for k, v in result.items()}
    return result

@log
def resolve_for_init(init, identifier_map):
    match init:
        case InitDecl(decl):
            return InitDecl(resolve_local_variable_declaration(decl, identifier_map))
        case InitExp(None):
            return InitExp(None)
        case InitExp(exp):
            return InitExp(resolve_exp(exp, identifier_map))

@log
def resolve_statement(statement, identifier_map):
    match statement:
        case Return(exp):
            return Return(resolve_exp(exp, identifier_map))
        case Expression(exp):
            return Expression(resolve_exp(exp, identifier_map))
        case If(cond, then, else_):
            return If(resolve_exp(cond, identifier_map), 
                        resolve_statement(then, identifier_map), 
                        resolve_statement(else_, identifier_map) if else_ else None)
        case Compound(block):
            new_identifier_map = copy_identifier_map(identifier_map)
            return Compound(resolve_block(block, new_identifier_map))
        case Break():
            return Break()
        case Continue():
            return Continue()
        case While(cond, body):
            return While(resolve_exp(cond, identifier_map), resolve_statement(body, identifier_map))
        case DoWhile(body, cond):
            return DoWhile(resolve_statement(body, identifier_map), resolve_exp(cond, identifier_map))
        case For(init, cond, post, body):
            new_identifier_map = copy_identifier_map(identifier_map)
            init = resolve_for_init(init, new_identifier_map)
            cond = resolve_exp(cond, new_identifier_map) if cond else None
            post = resolve_exp(post, new_identifier_map) if post else None
            body = resolve_statement(body, new_identifier_map)
            return For(init, cond, post, body)
        case Null():
            return Null()
        case _:
            raise RuntimeError(f"Could not validate semantics for statement {statement}")

@log
def resolve_exp(exp, identifier_map):
    match exp:
        case Assignment(left, right):
            if not isinstance(left, Var):
                raise RuntimeError("Invalid lvalue")
            return Assignment(resolve_exp(left, identifier_map), resolve_exp(right, identifier_map))
        case Var(v):
            if v not in identifier_map:
                raise RuntimeError(f"Undeclared variable {v}")
            return Var(identifier_map[v].name)
        case Constant(_):
            return exp
        case Unary(unop, exp):
            return Unary(unop, resolve_exp(exp, identifier_map))
        case Binary(binop, left, right):
            return Binary(binop, resolve_exp(left, identifier_map), resolve_exp(right, identifier_map))
        case Conditional(cond, then, else_):
            return Conditional(resolve_exp(cond, identifier_map), 
                                resolve_exp(then, identifier_map), 
                                resolve_exp(else_, identifier_map))
        case FunctionCall(fun_name, args):
            if fun_name not in identifier_map:
                raise RuntimeError(f"Undeclared function {fun_name}")
            new_fun_name = identifier_map[fun_name].name
            new_args = [resolve_exp(arg, identifier_map) for arg in args]
            return FunctionCall(new_fun_name, new_args)
        case _:
            raise RuntimeError(f"Could not validate semantics for expression {exp}")

@log
def resolve_block(block, identifier_map):
    new_block_items = []
    for blockitem in block.block_items:
        match blockitem:
            case D(declaration):
                resolved = D(resolve_local_declaration(declaration, identifier_map))
            case S(statement):
                resolved = S(resolve_statement(statement, identifier_map))
            case _:
                raise RuntimeError(f"Could not validate semantics for blockitem {blockitem}")
        new_block_items.append(resolved)
    return Block(new_block_items)

@log
def resolve_param(param, identifier_map):
    if param in identifier_map and identifier_map[param].from_current_scope:
        raise RuntimeError("Duplicate variable declaration")
    unique_name = NameGenerator.make_temporary(param)
    identifier_map[param] = MapEntry(
        name = unique_name, 
        from_current_scope = True, 
        has_linkage = False)
    return unique_name

@log
def resolve_local_function_declaration(func_decl, identifier_map):
    if func_decl.storage_class == StorageClass.static:
        raise RuntimeError(f"Block scope function declaration {func_decl} cannot include static specifier")
    return resolve_file_scope_function_declaration(func_decl, identifier_map)

@log
def resolve_local_variable_declaration(var_decl: VariableDeclaration, identifier_map):
    if var_decl.name in identifier_map:
        prev_entry = identifier_map[var_decl.name]
        if prev_entry.from_current_scope:
            if not (prev_entry.has_linkage and var_decl.storage_class == StorageClass.extern):
                raise RuntimeError(f"Conflicting local declarations {var_decl} and {prev_entry}")
    
    if var_decl.storage_class == StorageClass.extern:
        identifier_map[var_decl.name] = MapEntry(
            name = var_decl.name,
            from_current_scope = True,
            has_linkage = True
        )
        return var_decl
    unique_name = NameGenerator.make_temporary(var_decl.name)
    identifier_map[var_decl.name] = MapEntry(
        name = unique_name,
        from_current_scope = True,
        has_linkage = False
    )
    init = var_decl.init
    if init is not None:
        init = resolve_exp(init, identifier_map)
    return VariableDeclaration(unique_name, init, var_decl.storage_class)        

#TODO: Refactor with resolve_file_scope_declaration
@log
def resolve_local_declaration(decl, identifier_map):
    match decl:
        case FunDecl(function_declaration):
            if function_declaration.body is not None:
                raise RuntimeError(f"Local function definition {function_declaration}")
            return FunDecl(resolve_local_function_declaration(function_declaration, identifier_map))
        case VarDecl(variable_declaration):
            return VarDecl(resolve_local_variable_declaration(variable_declaration, identifier_map))
        case _:
            raise RuntimeError(f"Could not validate semantics for declaration {decl}")

@log
def resolve_file_scope_function_declaration(func_decl, identifier_map):
    if func_decl.name in identifier_map:
        prev_entry = identifier_map[func_decl.name]
        if prev_entry.from_current_scope and not prev_entry.has_linkage:
            raise RuntimeError("Duplicate declaration")

    identifier_map[func_decl.name] = MapEntry(
        name = func_decl.name,
        from_current_scope = True,
        has_linkage = True
    )

    inner_map = copy_identifier_map(identifier_map)
    new_params = [resolve_param(param, inner_map) for param in func_decl.params]
    
    new_body = None
    if func_decl.body is not None:
        new_body = resolve_block(func_decl.body, inner_map)
    return FunctionDeclaration(func_decl.name, new_params, new_body, func_decl.storage_class)
        
@log
def resolve_file_scope_variable_declaration(var_decl, identifier_map):
    identifier_map[var_decl.name] = MapEntry(
        name = var_decl.name,
        from_current_scope = True,
        has_linkage = True
    )
    return var_decl
        
@log
def resolve_file_scope_declaration(decl, identifier_map):
    match decl:
        case FunDecl(function_declaration):
            return FunDecl(resolve_file_scope_function_declaration(function_declaration, identifier_map))
        case VarDecl(variable_declaration):
            return VarDecl(resolve_file_scope_variable_declaration(variable_declaration, identifier_map))
        case _:
            raise RuntimeError(f"Could not validate semantics for declaration {decl}")
        
@log("Resolving variables:")
def resolve_program(program):
    identifier_map: dict[str, MapEntry] = {}
    new_decls = []
    for decl in program.declarations:
        resolved = resolve_file_scope_declaration(decl, identifier_map)
        new_decls.append(resolved)
    return Program(new_decls)
