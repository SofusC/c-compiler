from __future__ import annotations
from ..c_ast import *
from ..utils import log, NameGenerator

@log
def ensure_label(current_label, kind):
    if current_label is None:
        raise RuntimeError(f"{kind} statement outside loop")
    return current_label

@log
def label_loop(loop):
    new_label = NameGenerator.make_label("loop")
    labeled_body = label_statement(loop.body, new_label)
    match loop:
        case While(cond, _):
            return While(cond, labeled_body, new_label)
        case DoWhile(_, cond):
            return DoWhile(labeled_body, cond, new_label)
        case For(init, cond, post, _):
            return For(init, cond, post, labeled_body, new_label)

@log
def label_statement(statement, current_label):
    match statement:
        case Break():
            return Break(ensure_label(current_label, "Break"))
        case Continue():
            return Continue(ensure_label(current_label, "Continue"))
        case If(cond, then, else_):
            return If(cond, 
                        label_statement(then, current_label), 
                        label_statement(else_, current_label) if else_ else None)
        case Compound(block):
            return Compound(label_block(block, current_label))
        case While() | DoWhile() | For() as loop:
            return label_loop(loop)
        case _:
            return statement

@log
def label_block(block, current_label = None):
    return Block([
        S(label_statement(item.statement, current_label))
        if isinstance(item, S) else item
        for item in block.block_items
    ])

@log
def label_function_declaration(fun_decl):
    body = label_block(fun_decl.body) if fun_decl.body else None
    return FunctionDeclaration(fun_decl.name, fun_decl.params, body, fun_decl.storage_class)

@log("Labelling loops:")
def label_program(program):
    new_decls = []
    for decl in program.declarations:
        if isinstance(decl, FunDecl):
            labelled = FunDecl(label_function_declaration(decl.function_declaration))
        else:
            labelled = decl
        new_decls.append(labelled)
    return Program(new_decls)