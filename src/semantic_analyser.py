from c_ast import *
from typing import NamedTuple
import copy
class NameGenerator:
    _counter = 0

    @classmethod
    def _next_id(cls):
        val = cls._counter
        cls._counter += 1
        return val
    
    @classmethod
    def make_temporary(cls, name = "tmp"):
        unique_name = f"{name}.{cls._next_id()}"
        return unique_name
    
    @classmethod
    def make_label(cls, label_name):
        return f"{label_name}{cls._next_id()}"

class MapEntry(NamedTuple):
    name: str
    from_current_block: bool

class SemanticAnalyser:
    def copy_variable_map(self, variable_map):
        result = copy.deepcopy(variable_map)
        result = {k: MapEntry(v.name, False) for k, v in result.items()}
        return result

    def resolve_declaration(self, decl, variable_map):
        name = decl.name
        if name in variable_map and variable_map[name].from_current_block:
            raise RuntimeError("Duplicate variable declaration")
        unique_name = NameGenerator.make_temporary(name)
        variable_map[name] = MapEntry(unique_name, True)
        init = decl.init
        if init is not None:
            init = self.resolve_exp(init, variable_map)
        return Declaration(unique_name, init)
    
    def resolve_for_init(self, init, variable_map):
        match init:
            case InitDecl(decl):
                return InitDecl(self.resolve_declaration(decl, variable_map))
            case InitExp(None):
                return InitExp(None)
            case InitExp(exp):
                return InitExp(self.resolve_exp(exp, variable_map))

    def resolve_statement(self, statement, variable_map):
        match statement:
            case Return(exp):
                return Return(self.resolve_exp(exp, variable_map))
            case Expression(exp):
                return Expression(self.resolve_exp(exp, variable_map))
            case If(cond, then, else_):
                return If(self.resolve_exp(cond, variable_map), 
                          self.resolve_statement(then, variable_map), 
                          self.resolve_statement(else_, variable_map) if else_ else None)
            case Compound(block):
                new_variable_map = self.copy_variable_map(variable_map)
                return Compound(self.resolve_block(block, new_variable_map))
            case Break():
                return Break()
            case Continue():
                return Continue()
            case While(cond, body):
                return While(self.resolve_exp(cond, variable_map), self.resolve_statement(body, variable_map))
            case DoWhile(body, cond):
                return DoWhile(self.resolve_statement(body, variable_map), self.resolve_exp(cond, variable_map))
            case For(init, cond, post, body):
                new_variable_map = self.copy_variable_map(variable_map)
                init = self.resolve_for_init(init, new_variable_map)
                cond = self.resolve_exp(cond, new_variable_map) if cond else None
                post = self.resolve_exp(post, new_variable_map) if post else None
                body = self.resolve_statement(body, new_variable_map)
                return For(init, cond, post, body)
            case Null():
                return Null()
            case _:
                raise RuntimeError(f"Could not validate semantics for statement {statement}")

    def resolve_exp(self, exp, variable_map):
        match exp:
            case Assignment(left, right):
                if not isinstance(left, Var):
                    raise RuntimeError("Invalid lvalue")
                return Assignment(self.resolve_exp(left, variable_map), self.resolve_exp(right, variable_map))
            case Var(v):
                if v not in variable_map:
                    raise RuntimeError(f"Undeclared variable {v}")
                return Var(variable_map[v].name)
            case Constant(_):
                return exp
            case Unary(unop, exp):
                return Unary(unop, self.resolve_exp(exp, variable_map))
            case Binary(binop, left, right):
                return Binary(binop, self.resolve_exp(left, variable_map), self.resolve_exp(right, variable_map))
            case Conditional(cond, then, else_):
                return Conditional(self.resolve_exp(cond, variable_map), 
                                   self.resolve_exp(then, variable_map), 
                                   self.resolve_exp(else_, variable_map))
            case _:
                raise RuntimeError(f"Could not validate semantics for expression {exp}")
    
    def resolve_block(self, block, variable_map):
        new_block_items = []
        for item in block.block_items:
            if isinstance(item, Declaration):
                item = self.resolve_declaration(item, variable_map)
            elif isinstance(item, Statement):
                item = self.resolve_statement(item, variable_map)
            else:
                raise RuntimeError(f"Could not validate semantics for item {item}")
            new_block_items.append(item)
        return Block(new_block_items)
    
    def ensure_label(self, current_label, kind):
        if current_label is None:
            raise RuntimeError(f"{kind} statement outside loop")
        return current_label
    
    def label_loop(self, loop):
        new_label = NameGenerator.make_label("loop")
        labeled_body = self.label_statement(loop.body, new_label)
        match loop:
            case While(cond, _):
                return While(cond, labeled_body, new_label)
            case DoWhile(_, cond):
                return DoWhile(labeled_body, cond, new_label)
            case For(init, cond, post, _):
                return For(init, cond, post, labeled_body, new_label)
    
    def label_statement(self, statement, current_label = None):
        match statement:
            case Break():
                return Break(self.ensure_label(current_label, "Break"))
            case Continue():
                return Continue(self.ensure_label(current_label, "Continue"))
            case If(cond, then, else_):
                return If(cond, 
                          self.label_statement(then, current_label), 
                          self.label_statement(else_, current_label) if else_ else None)
            case Compound(block):
                return Compound(self.label_block(block, current_label))
            case While() | DoWhile() | For() as loop:
                return self.label_loop(loop)
            case _:
                return statement
    
    def label_block(self, block, current_label = None):
        new_block_items = []
        for item in block.block_items:
            if isinstance(item, Statement):
                item = self.label_statement(item, current_label)
            new_block_items.append(item)
        return Block(new_block_items)

    def validate_program(self, program):
        variable_map: dict[str, MapEntry] = {}
        program.function.body = self.resolve_block(program.function.body, variable_map)
        program.function.body = self.label_block(program.function.body)
        return program