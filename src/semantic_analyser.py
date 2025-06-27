from __future__ import annotations
from c_ast import *
from typing import NamedTuple
import copy
from utils import log

symbol_table: dict[str, TypeChecker.SymbolEntry] = {}

@log("Validating program:")
def validate_program(program):
    program = VariableResolver().resolve_program(program)
    TypeChecker().typecheck_program(program)
    program = LoopLabeller().label_program(program)
    return program

class VariableResolver:
    class MapEntry(NamedTuple):
        name: str
        from_current_scope: bool
        has_linkage: bool

    @log
    def copy_identifier_map(self, identifier_map):
        result = copy.deepcopy(identifier_map)
        result = {k: self.MapEntry(v.name, False, v.has_linkage) for k, v in result.items()}
        return result
    
    @log
    def resolve_for_init(self, init, identifier_map):
        match init:
            case InitDecl(decl):
                return InitDecl(self.resolve_local_variable_declaration(decl, identifier_map))
            case InitExp(None):
                return InitExp(None)
            case InitExp(exp):
                return InitExp(self.resolve_exp(exp, identifier_map))

    @log
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

    @log
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
    
    @log
    def resolve_block(self, block, identifier_map):
        new_block_items = []
        for blockitem in block.block_items:
            match blockitem:
                case D(declaration):
                    resolved = D(self.resolve_local_declaration(declaration, identifier_map))
                case S(statement):
                    resolved = S(self.resolve_statement(statement, identifier_map))
                case _:
                    raise RuntimeError(f"Could not validate semantics for blockitem {blockitem}")
            new_block_items.append(resolved)
        return Block(new_block_items)
    
    #TODO: Move into resolve_param function?
    @log
    def register_identifier(self, name, identifier_map):
        if name in identifier_map and identifier_map[name].from_current_scope:
            raise RuntimeError("Duplicate variable declaration")
        unique_name = NameGenerator.make_temporary(name)
        identifier_map[name] = self.MapEntry(
            name = unique_name, 
            from_current_scope = True, 
            has_linkage = False)
        return unique_name

    #@log
    #def resolve_variable_declaration(self, var_decl, identifier_map):
    #    name = var_decl.name
    #    unique_name = self.register_identifier(name, identifier_map)
    #    init = var_decl.init
    #    if init is not None:
    #        init = self.resolve_exp(init, identifier_map)
    #    return VariableDeclaration(unique_name, init)

    @log
    def resolve_param(self, param, identifier_map):
        return self.register_identifier(param, identifier_map)

    @log
    def resolve_local_function_declaration(self, func_decl, identifier_map):
        if func_decl.storage_class == StorageClass.static:
            raise RuntimeError(f"Block scope function declaration {func_decl} cannot include static specifier")
        return self.resolve_file_scope_function_declaration(func_decl, identifier_map)
    
    @log
    def resolve_local_variable_declaration(self, var_decl: VariableDeclaration, identifier_map):
        if var_decl.name in identifier_map:
            prev_entry = identifier_map[var_decl.name]
            if prev_entry.from_current_scope:
                if not (prev_entry.has_linkage and var_decl.storage_class == StorageClass.extern):
                    raise RuntimeError(f"Conflicting local declarations {var_decl} and {prev_entry}")
        
        if var_decl.storage_class == StorageClass.extern:
            identifier_map[var_decl.name] = self.MapEntry(
                name = var_decl.name,
                from_current_scope = True,
                has_linkage = True
            )
            return var_decl
        unique_name = NameGenerator.make_temporary(var_decl.name)
        identifier_map[var_decl.name] = self.MapEntry(
            name = unique_name,
            from_current_scope = True,
            has_linkage = False
        )
        init = var_decl.init
        if init is not None:
            init = self.resolve_exp(init, identifier_map)
        return VariableDeclaration(unique_name, init, var_decl.storage_class)        

    #TODO: Refactor with resolve_file_scope_declaration
    @log
    def resolve_local_declaration(self, decl, identifier_map):
        match decl:
            case FunDecl(function_declaration):
                if function_declaration.body is not None:
                    raise RuntimeError(f"Local function definition {function_declaration}")
                return FunDecl(self.resolve_local_function_declaration(function_declaration, identifier_map))
            case VarDecl(variable_declaration):
                return VarDecl(self.resolve_local_variable_declaration(variable_declaration, identifier_map))
            case _:
                raise RuntimeError(f"Could not validate semantics for declaration {decl}")
    
    @log
    def resolve_file_scope_function_declaration(self, func_decl, identifier_map):
        if func_decl.name in identifier_map:
            prev_entry = identifier_map[func_decl.name]
            if prev_entry.from_current_scope and not prev_entry.has_linkage:
                raise RuntimeError("Duplicate declaration")

        identifier_map[func_decl.name] = self.MapEntry(
            name = func_decl.name,
            from_current_scope = True,
            has_linkage = True
        )

        inner_map = self.copy_identifier_map(identifier_map)
        new_params = [self.resolve_param(param, inner_map) for param in func_decl.params]
        
        new_body = None
        if func_decl.body is not None:
            new_body = self.resolve_block(func_decl.body, inner_map)
        return FunctionDeclaration(func_decl.name, new_params, new_body, func_decl.storage_class)
            
    @log
    def resolve_file_scope_variable_declaration(self, var_decl, identifier_map):
        identifier_map[var_decl.name] = self.MapEntry(
            name = var_decl.name,
            from_current_scope = True,
            has_linkage = True
        )
        return var_decl
            
    @log
    def resolve_file_scope_declaration(self, decl, identifier_map):
        match decl:
            case FunDecl(function_declaration):
                return FunDecl(self.resolve_file_scope_function_declaration(function_declaration, identifier_map))
            case VarDecl(variable_declaration):
                return VarDecl(self.resolve_file_scope_variable_declaration(variable_declaration, identifier_map))
            case _:
                raise RuntimeError(f"Could not validate semantics for declaration {decl}")
            
    @log("Resolving variables:")
    def resolve_program(self, program):
        identifier_map: dict[str, VariableResolver.MapEntry] = {}
        new_decls = []
        for decl in program.declarations:
            resolved = self.resolve_file_scope_declaration(decl, identifier_map)
            new_decls.append(resolved)
        return Program(new_decls)

    
class TypeChecker:
    class Int:
        pass

    @dataclass
    class FunType:
        param_count: int

    Type = Int | FunType

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
        init: TypeChecker.InitialValue
        global_: bool
    class LocalAttr:
        pass
    
    IdentifierAttr = FunAttr | StaticAttr | LocalAttr

    @dataclass
    class SymbolEntry:
        type: TypeChecker.Type
        defined: bool | None = None
        attrs: TypeChecker.IdentifierAttr | None = None

    @log("Typechecking:")
    def typecheck_program(self, program):
        for decl in program.declarations:
            self.typecheck_file_scope_declaration(decl)

    @log
    def typecheck_file_scope_declaration(self, decl):
        match decl:
            case FunDecl(fun_decl):
                self.typecheck_function_declaration(fun_decl)
            case VarDecl(var_decl):
                self.typecheck_file_scope_variable_declaration(var_decl)
            case _:
                raise RuntimeError(f"Cannot typecheck declaration {decl}")
    
    @log
    def typecheck_function_declaration(self, decl: FunctionDeclaration):
        fun_type = self.FunType(len(decl.params))
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

        attrs = self.FunAttr(defined=(already_defined or has_body), global_ = global_decl)
        symbol_table[decl.name] = self.SymbolEntry(
            type = fun_type, 
            defined = already_defined or has_body,
            attrs = attrs
        )
        if has_body:
            for param in decl.params:
                symbol_table[param] = self.SymbolEntry(self.Int())
            self.typecheck_block(decl.body)

    @log
    def typecheck_file_scope_variable_declaration(self, var_decl: VariableDeclaration):
        if isinstance(var_decl.init, Constant):
            initial_value = TypeChecker.Initial(var_decl.init)
        elif var_decl.init is None:
            if var_decl.storage_class == StorageClass.extern:
                initial_value = TypeChecker.NoInitializer()
            else:
                initial_value = TypeChecker.Tentative()
        else:
            raise RuntimeError(f"Non-constant initializer {var_decl.init}")
        
        global_ = var_decl.storage_class != StorageClass.static

        if var_decl.name in symbol_table:
            old_decl = symbol_table[var_decl.name]
            if not isinstance(old_decl.type, TypeChecker.Int):
                raise RuntimeError(f"Function redeclared as variable {var_decl}")
            if var_decl.storage_class == StorageClass.extern:
                global_ = old_decl.attrs.global_
            elif old_decl.attrs.global_ != global_:
                raise RuntimeError(f"Conflicting variable linkage between {old_decl} and {var_decl}")
            
            if isinstance(old_decl.attrs.init, TypeChecker.Initial):
                if isinstance(initial_value, TypeChecker.Initial):
                    raise RuntimeError(f"Conflicting file scope variable declarations with initializers {old_decl.attrs.init} and {initial_value}")
                else:
                    initial_value = old_decl.attrs.init
            elif not isinstance(initial_value, TypeChecker.Initial) and isinstance(old_decl.attrs.init, TypeChecker.Tentative):
                initial_value = TypeChecker.Tentative()
        attrs = TypeChecker.StaticAttr(init = initial_value, global_ = global_)
        symbol_table[var_decl.name] = TypeChecker.SymbolEntry(
            type = TypeChecker.Int(), 
            attrs = attrs)

    @log
    def typecheck_block(self, block):
        for block_item in block.block_items:
            self.typecheck_block_item(block_item)

    @log
    def typecheck_block_item(self, item):
        match item:
            case D(decl):
                self.typecheck_local_declaration(decl)
            case S(stmt):
                self.typecheck_statement(stmt)
            case _:
                raise RuntimeError(f"Cannot typecheck block item {item}")
            
    @log
    def typecheck_local_declaration(self, decl):
        match decl:
            case FunDecl(fun_decl):
                self.typecheck_function_declaration(fun_decl)
            case VarDecl(var_decl):
                self.typecheck_local_variable_declaration(var_decl)
            case _:
                raise RuntimeError(f"Cannot typecheck declaration {decl}")
    
    @log
    def typecheck_local_variable_declaration(self, var_decl: VariableDeclaration):
        if var_decl.storage_class == StorageClass.extern:
            if var_decl.init is not None:
                raise RuntimeError(f"Initializer on local extern variable declaration {var_decl}")
            if var_decl.name in symbol_table:
                old_decl = symbol_table[var_decl.name]
                if not isinstance(old_decl.type, TypeChecker.Int):
                    raise RuntimeError(f"Function redeclared as variable {var_decl}")
            else:
                symbol_table[var_decl.name] = TypeChecker.SymbolEntry(
                    type = TypeChecker.Int(),
                    attrs = TypeChecker.StaticAttr(init = TypeChecker.NoInitializer(), global_ = True)
                )
        elif var_decl.storage_class == StorageClass.static:
            if isinstance(var_decl.init, Constant):
                initial_value = var_decl.init
            elif var_decl.init is None:
                initial_value = TypeChecker.Initial(0)
            else:
                raise RuntimeError(f"Non-constant initializer on local static variable {var_decl}")
            symbol_table[var_decl.name] = TypeChecker.SymbolEntry(
                type = TypeChecker.Int(),
                attrs = TypeChecker.StaticAttr(init = initial_value, global_ = False)
            )
        else:
            symbol_table[var_decl.name] = self.SymbolEntry(
                type = self.Int(),
                attrs = TypeChecker.LocalAttr())
        if var_decl.init is not None:
            self.typecheck_exp(var_decl.init)

    @log
    def typecheck_statement(self, stmt):
        match stmt:
            case Return(exp) | Expression(exp):
                self.typecheck_exp(exp)
            case If(cond, then, else_):
                self.typecheck_exp(cond)
                self.typecheck_statement(then)
                if else_:
                    self.typecheck_statement(else_)
            case Compound(block):
                self.typecheck_block(block)
            case Break() | Continue() | Null():
                pass
            case While(cond, body, _) | DoWhile(body, cond, _):
                self.typecheck_exp(cond)
                self.typecheck_statement(body)
            case For(init, cond, post, body, _):
                self.typecheck_for_init(init)
                if cond:
                    self.typecheck_exp(cond)
                if post:
                    self.typecheck_exp(post)
                self.typecheck_statement(body)
            case _:
                raise RuntimeError(f"Cannot typecheck statement {stmt}")

    @log
    def typecheck_for_init(self, init):
        match init:
            case InitDecl(decl):
                if decl.storage_class is not None:
                    raise RuntimeError(f"Cannot have storage class specifier in for init {decl}")
                self.typecheck_local_variable_declaration(decl)
            case InitExp(None):
                pass
            case InitExp(exp):
                self.typecheck_exp(exp)
            case _:
                raise RuntimeError(f"Cannot typecheck for init {init}")

    @log
    def typecheck_exp(self, exp):
        match exp:
            case Constant():
                pass
            case Unary(_, exp):
                self.typecheck_exp(exp)
            case Binary(_, left, right) | Assignment(left, right):
                self.typecheck_exp(left)
                self.typecheck_exp(right)
            case Conditional(cond, then, else_):
                self.typecheck_exp(cond)
                self.typecheck_exp(then)
                self.typecheck_exp(else_)
            case FunctionCall(identifier, args):
                f_type = symbol_table[identifier].type
                if isinstance(f_type, self.Int):
                    raise RuntimeError(f"Variable used as function name {identifier}")
                if f_type.param_count != len(args):
                    raise RuntimeError(f"Function {identifier} called with wrong number of arguments, expected {f_type.param_count}, found {len(args)}")
                for arg in args:
                    self.typecheck_exp(arg)
            case Var(v):
                if not isinstance(symbol_table[v].type, self.Int):
                    raise RuntimeError(f"Function name {v} used as variable")
            case _:
                raise RuntimeError(f"Cannot typecheck exp {exp}")

class LoopLabeller:
    @log
    def ensure_label(self, current_label, kind):
        if current_label is None:
            raise RuntimeError(f"{kind} statement outside loop")
        return current_label
    
    @log
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
    
    @log
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
    
    @log
    def label_block(self, block, current_label = None):
        return Block([
            S(self.label_statement(item.statement, current_label))
            if isinstance(item, S) else item
            for item in block.block_items
        ])
    
    @log
    def label_function_declaration(self, fun_decl):
        body = self.label_block(fun_decl.body) if fun_decl.body else None
        return FunctionDeclaration(fun_decl.name, fun_decl.params, body, fun_decl.storage_class)
    
    @log("Labelling loops:")
    def label_program(self, program):
        new_decls = []
        for decl in program.declarations:
            if isinstance(decl, FunDecl):
                labelled = FunDecl(self.label_function_declaration(decl.function_declaration))
            else:
                labelled = decl
            new_decls.append(labelled)
        return Program(new_decls)


class NameGenerator:
    _counter = 0

    @classmethod
    @log
    def _next_id(cls):
        val = cls._counter
        cls._counter += 1
        return val
    
    @classmethod
    @log
    def make_temporary(cls, name = "tmp"):
        unique_name = f"{name}.{cls._next_id()}"
        return unique_name
    
    @classmethod
    @log
    def make_label(cls, label_name):
        return f"{label_name}{cls._next_id()}"
