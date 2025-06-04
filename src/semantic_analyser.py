from c_ast import *
from typing import NamedTuple
import copy

class SharedCounter:
    counter = 0

    @classmethod
    def increment(cls):
        cls.counter += 1
        return cls.counter

    @classmethod
    def get_value(cls):
        return cls.counter
    

class MapEntry(NamedTuple):
    name: str
    from_current_block: bool

class SemanticAnalyser:
    label_counter = 0

    def make_temporary(self, name):
        unique_name = f"{name}.{SharedCounter.get_value()}"
        SharedCounter.increment()
        return unique_name
    
    def make_label(self, label_name): #TODO: this is identical to method in emitter, shared util class instead of counter?
        label_name += str(self.label_counter)
        self.label_counter += 1
        return label_name
    
    def copy_variable_map(self, variable_map):
        result = copy.deepcopy(variable_map)
        result = {k: MapEntry(v.name, False) for k, v in result.items()}
        return result

    def resolve_declaration(self, decl, variable_map):
        name = decl.name
        if name in variable_map and variable_map[name].from_current_block:
            raise RuntimeError("Duplicate variable declaration")
        unique_name = self.make_temporary(name)
        variable_map[name] = MapEntry(unique_name, True)
        init = decl.init
        if init is not None:
            init = self.resolve_exp(init, variable_map)
        return Declaration(unique_name, init)
    
    def resolve_for_init(self, init, variable_map):
        match init:
            case InitExp(exp):
                return InitExp(self.resolve_exp(exp, variable_map))
            case InitDecl(decl):
                return InitDecl(self.resolve_declaration(decl, variable_map))

    def resolve_statement(self, statement, variable_map):
        match statement:
            case Return(exp):
                return Return(self.resolve_exp(exp, variable_map))
            case Expression(exp):
                return Expression(self.resolve_exp(exp, variable_map))
            case If(cond, then, else_):
                return If(self.resolve_exp(cond, variable_map), self.resolve_statement(then, variable_map), self.resolve_statement(else_, variable_map) if else_ else None)
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
                cond = self.resolve_exp(cond, new_variable_map)
                post = self.resolve_exp(post, new_variable_map)
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
                return Conditional(self.resolve_exp(cond, variable_map), self.resolve_exp(then, variable_map), self.resolve_exp(else_, variable_map))
            case None:
                return None
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
    
    def label_statement(self, statement, current_label = None):
        match statement:
            case Break():
                if current_label is None:
                    raise RuntimeError("Break statement outside loop")
                return Break(current_label)
            case Continue():
                if current_label is None:
                    raise RuntimeError("Continue statement outside loop")
                return Continue(current_label)
            case If(cond, then, else_):
                return If(cond, self.label_statement(then, current_label), self.label_statement(else_, current_label) if else_ else None)
            case Compound(block):
                return Compound(self.label_block(block, current_label))
            case While(cond, body):
                new_label = self.make_label("loop")
                labeled_body = self.label_statement(body, new_label)
                return While(cond, labeled_body, new_label)
            case DoWhile(body, cond):
                new_label = self.make_label("loop")
                labeled_body = self.label_statement(body, new_label)
                return DoWhile(labeled_body, cond, new_label)
            case For(init, cond, post, body):
                new_label = self.make_label("loop")
                labeled_body = self.label_statement(body, new_label)
                return For(init, cond, post, labeled_body, new_label)
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