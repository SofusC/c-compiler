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
    from_current_scope: bool
    has_linkage: bool

class SemanticAnalyser:
    def copy_identifier_map(self, identifier_map):
        result = copy.deepcopy(identifier_map)
        result = {k: MapEntry(v.name, False, v.has_linkage) for k, v in result.items()}
        return result
    
    def resolve_for_init(self, init, identifier_map):
        match init:
            case InitDecl(decl):
                return InitDecl(self.resolve_variable_declaration(decl, identifier_map))
            case InitExp(None):
                return InitExp(None)
            case InitExp(exp):
                return InitExp(self.resolve_exp(exp, identifier_map))

    def resolve_statement(self, statement, identifier_map):
        match statement:
            case Return(exp):
                return Return(self.resolve_exp(exp, identifier_map))
            case Expression(exp):
                return Expression(self.resolve_exp(exp, identifier_map))
            case If(cond, then, else_):
                return If(self.resolve_exp(cond, identifier_map), 
                          self.resolve_statement(then, identifier_map), 
                          self.resolve_statement(else_, identifier_map) if else_ else None)
            case Compound(block):
                new_identifier_map = self.copy_identifier_map(identifier_map)
                return Compound(self.resolve_block(block, new_identifier_map))
            case Break():
                return Break()
            case Continue():
                return Continue()
            case While(cond, body):
                return While(self.resolve_exp(cond, identifier_map), self.resolve_statement(body, identifier_map))
            case DoWhile(body, cond):
                return DoWhile(self.resolve_statement(body, identifier_map), self.resolve_exp(cond, identifier_map))
            case For(init, cond, post, body):
                new_identifier_map = self.copy_identifier_map(identifier_map)
                init = self.resolve_for_init(init, new_identifier_map)
                cond = self.resolve_exp(cond, new_identifier_map) if cond else None
                post = self.resolve_exp(post, new_identifier_map) if post else None
                body = self.resolve_statement(body, new_identifier_map)
                return For(init, cond, post, body)
            case Null():
                return Null()
            case _:
                raise RuntimeError(f"Could not validate semantics for statement {statement}")

    def resolve_exp(self, exp, identifier_map):
        match exp:
            case Assignment(left, right):
                if not isinstance(left, Var):
                    raise RuntimeError("Invalid lvalue")
                return Assignment(self.resolve_exp(left, identifier_map), self.resolve_exp(right, identifier_map))
            case Var(v):
                if v not in identifier_map:
                    raise RuntimeError(f"Undeclared variable {v}")
                return Var(identifier_map[v].name)
            case Constant(_):
                return exp
            case Unary(unop, exp):
                return Unary(unop, self.resolve_exp(exp, identifier_map))
            case Binary(binop, left, right):
                return Binary(binop, self.resolve_exp(left, identifier_map), self.resolve_exp(right, identifier_map))
            case Conditional(cond, then, else_):
                return Conditional(self.resolve_exp(cond, identifier_map), 
                                   self.resolve_exp(then, identifier_map), 
                                   self.resolve_exp(else_, identifier_map))
            case FunctionCall(fun_name, args):
                if fun_name not in identifier_map:
                    raise RuntimeError(f"Undeclared function {fun_name}")
                new_fun_name = identifier_map[fun_name].name
                new_args = [self.resolve_exp(arg, identifier_map) for arg in args]
                return FunctionCall(new_fun_name, new_args)
            case _:
                raise RuntimeError(f"Could not validate semantics for expression {exp}")
    
    def resolve_block(self, block, identifier_map):
        new_block_items = []
        for blockitem in block.block_items:
            match blockitem:
                case D(declaration):
                    resolved = D(self.resolve_declaration(declaration, identifier_map))
                case S(statement):
                    resolved = S(self.resolve_statement(statement, identifier_map))
                case _:
                    raise RuntimeError(f"Could not validate semantics for blockitem {blockitem}")
            new_block_items.append(resolved)
        return Block(new_block_items)
    
    def register_identifier(self, name, identifier_map):
        if name in identifier_map and identifier_map[name].from_current_scope:
            raise RuntimeError("Duplicate variable declaration")
        unique_name = NameGenerator.make_temporary(name)
        identifier_map[name] = MapEntry(
            name = unique_name, 
            from_current_scope = True, 
            has_linkage = False)
        return unique_name

    def resolve_variable_declaration(self, var_decl, identifier_map):
        name = var_decl.name
        unique_name = self.register_identifier(name, identifier_map)
        init = var_decl.init
        if init is not None:
            init = self.resolve_exp(init, identifier_map)
        return VariableDeclaration(unique_name, init)

    def resolve_param(self, param, identifier_map):
        return self.register_identifier(param, identifier_map)

    def resolve_function_declaration(self, func_decl, identifier_map):
        if func_decl.name in identifier_map:
            prev_entry = identifier_map[func_decl.name]
            if prev_entry.from_current_scope and not prev_entry.has_linkage:
                raise RuntimeError("Duplicate declaration")

        identifier_map[func_decl.name] = MapEntry(
            name = func_decl.name,
            from_current_scope = True,
            has_linkage = True
        )

        inner_map = self.copy_identifier_map(identifier_map)
        new_params = [self.resolve_param(param, inner_map) for param in func_decl.params]
        
        new_body = None
        if func_decl.body is not None:
            new_body = self.resolve_block(func_decl.body, inner_map)
        return FunctionDeclaration(func_decl.name, new_params, new_body)

    def resolve_declaration(self, decl, identifier_map):
        match decl:
            case FunDecl(function_declaration):
                if function_declaration.body is not None:
                    raise RuntimeError(f"Local function definition {function_declaration}")
                return FunDecl(self.resolve_function_declaration(function_declaration, identifier_map))
            case VarDecl(variable_declaration):
                return FunDecl(self.resolve_variable_declaration(variable_declaration, identifier_map))
            case _:
                raise RuntimeError(f"Could not validate semantics for declaration {decl}")
    
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
    
    def label_statement(self, statement, current_label):
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
        return Block([
            S(self.label_statement(item.statement, current_label))
            if isinstance(item, S) else item
            for item in block.block_items
        ])
    
    def label_function_declaration(self, fun_decl):
        body = self.label_block(fun_decl.body) if fun_decl.body else None
        return FunctionDeclaration(fun_decl.name, fun_decl.params, body)

    def validate_program(self, program):
        identifier_map: dict[str, MapEntry] = {}
        new_function_decls = []
        for function_decl in program.function_declarations:
            resolved = self.resolve_function_declaration(function_decl, identifier_map)
            labelled = self.label_function_declaration(resolved)
            new_function_decls.append(labelled)
        return Program(new_function_decls)
