from c_ast import *

class SharedCounter:
    counter = 0

    @classmethod
    def increment(cls):
        cls.counter += 1
        return cls.counter

    @classmethod
    def get_value(cls):
        return cls.counter
    
class SemanticAnalyser:
    variable_map = {}

    def make_temporary(self, name):
        unique_name = f"{name}.{SharedCounter.get_value()}"
        SharedCounter.increment()
        return unique_name

    def resolve_declaration(self, decl):
        name = decl.name
        if name in self.variable_map:
            raise RuntimeError("Duplicate variable declaration")
        unique_name = self.make_temporary(name)
        self.variable_map[name] = unique_name
        init = decl.init
        if init is not None:
            init = self.resolve_exp(init)
        return Declaration(unique_name, init)

    def resolve_statement(self, statement):
        match statement:
            case Return(exp):
                return Return(self.resolve_exp(exp))
            case Expression(exp):
                return Expression(self.resolve_exp(exp))
            case Null:
                return Null

    def resolve_exp(self, exp):
        match exp:
            case Assignment(left, right):
                if not isinstance(left, Var):
                    raise RuntimeError("Invalid lvalue")
                return Assignment(self.resolve_exp(left), self.resolve_exp(right))
            case Var(v):
                if v not in self.variable_map:
                    raise RuntimeError(f"Undeclared variable {v}")
                return Var(self.variable_map[v])
            case Constant(_):
                return exp
            case Unary(unop, exp):
                return Unary(unop, self.resolve_exp(exp))
            case Binary(binop, left, right):
                return Binary(binop, self.resolve_exp(left), self.resolve_exp(right))

    def validate_program(self, program):
        new_body = []
        for item in program.function.body:
            if isinstance(item, Declaration):
                item = self.resolve_declaration(item)
            elif isinstance(item, Statement):
                item = self.resolve_statement(item)
            else:
                raise RuntimeError(f"Could not validate semantics for item {item}")
            new_body.append(item)
        program.function.body = new_body
        return program