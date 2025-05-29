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

    def make_temporary(self, name):
        unique_name = f"{name}.{SharedCounter.get_value()}"
        SharedCounter.increment()
        return unique_name
    
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
            case Null():
                return Null()

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

    def validate_program(self, program):
        variable_map: dict[str, MapEntry] = {}
        program.function.body = self.resolve_block(program.function.body, variable_map)
        return program