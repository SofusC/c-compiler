from __future__ import annotations
from abc import ABC
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class ASTNode(ABC):
    pass



@dataclass
class Program(ASTNode):
    declarations: List[Declaration]



class Declaration(ASTNode):
    pass

@dataclass
class FunDecl(Declaration):
    function_declaration: FunctionDeclaration

@dataclass
class VarDecl(Declaration):
    variable_declaration: VariableDeclaration



@dataclass
class VariableDeclaration(ASTNode):
    name: str
    init: Exp | None
    var_type: Type
    storage_class: StorageClass | None

@dataclass
class FunctionDeclaration(ASTNode):
    name: str
    params: List[str]
    body: Block | None
    fun_type: Type
    storage_class: StorageClass | None



class Type(ASTNode): 
    pass

class IntegralType(Type):
    BIT_WIDTH: int

    def is_signed(self) -> bool:
        raise NotImplementedError()
    
    def __repr__(cls):
        return cls.__name__
    
class SignedType(IntegralType):
    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.MIN_VALUE = -2**(cls.BIT_WIDTH - 1)
        cls.MAX_VALUE = 2**(cls.BIT_WIDTH - 1) - 1
        cls.RANGE = 2**cls.BIT_WIDTH

    def is_signed(self) -> bool:
        return True

class Int(SignedType):
    BIT_WIDTH = 32

class Long(SignedType): 
    BIT_WIDTH = 64

class UnsignedType(IntegralType):
    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.MIN_VALUE = 0
        cls.MAX_VALUE = 2**(cls.BIT_WIDTH) - 1
        cls.RANGE = 2**cls.BIT_WIDTH

    def is_signed(self) -> bool:
        return False

class UInt(UnsignedType):
    BIT_WIDTH = 32

class ULong(UnsignedType):
    BIT_WIDTH = 64


@dataclass(frozen = True)
class FunType(Type):
    params: List[Type]
    ret: Type



class StorageClass(Enum):
    static = auto()
    extern = auto()



@dataclass
class Block(ASTNode):
    block_items: List[BlockItem]



class ForInit(ASTNode):
    pass

@dataclass
class InitDecl(ForInit):
    declaration: VariableDeclaration

@dataclass
class InitExp(ForInit):
    exp: Exp | None = None



class BlockItem(ASTNode):
    pass

@dataclass
class D(BlockItem):
    declaration: Declaration

@dataclass
class S(BlockItem):
    statement: Statement



class Statement(BlockItem):
    pass

@dataclass
class Return(Statement):
    exp: Exp

@dataclass
class Expression(Statement):
    exp: Exp

@dataclass
class If(Statement):
    condition: Exp
    then: Statement
    else_: Statement | None

@dataclass
class Compound(Statement):
    block: Block

@dataclass
class Break(Statement):
    label: str | None = None

@dataclass
class Continue(Statement):
    label: str | None = None

@dataclass
class While(Statement):
    condition: Exp
    body: Statement
    label: str | None = None

@dataclass
class DoWhile(Statement):
    body: Statement
    condition: Exp
    label: str | None = None
    
@dataclass
class For(Statement):
    init: ForInit
    condition: Exp | None
    post: Exp | None
    body: Statement
    label: str | None = None
    
class Null(Statement):
    pass


@dataclass(kw_only = True)
class Exp(ASTNode):
    type: Type | None = None

@dataclass
class Constant(Exp):
    constant: Const

@dataclass
class Var(Exp):
    identifier: str

@dataclass
class Cast(Exp):
    target_type: Type
    exp: Exp

@dataclass
class Unary(Exp):
    unary_operator: UnaryOperator
    exp: Exp

@dataclass
class Binary(Exp):
    binary_operator: BinaryOperator
    left_exp: Exp
    right_exp: Exp

@dataclass
class Assignment(Exp):
    left: Exp
    right: Exp

@dataclass
class Conditional(Exp):
    condition: Exp
    then_exp: Exp
    else_exp: Exp

@dataclass
class FunctionCall(Exp):
    identifier: str
    args: List[Exp]



class UnaryOperator(Enum):
    Complement = auto()
    Negate = auto()
    Not = auto()

    @property
    def is_logical(self):
        return self == UnaryOperator.Not #TODO: Are other properties like this needed? Can this be moved to a base class for operators?

class BinaryOperator(Enum):
    Add = auto()
    Subtract = auto()
    Multiply = auto()
    Divide = auto()
    Remainder = auto()

    And = auto()
    Or = auto()

    Equal = auto()
    NotEqual = auto()
    LessThan = auto()
    LessOrEqual = auto()
    GreaterThan = auto()
    GreaterOrEqual = auto()

    @property
    def is_logical(self):
        return self in {BinaryOperator.And, BinaryOperator.Or}
    
    @property
    def is_arithmetic(self):
        return self in {BinaryOperator.Add, BinaryOperator.Subtract, BinaryOperator.Multiply, BinaryOperator.Divide, BinaryOperator.Remainder}


class Const(ASTNode):
    pass

@dataclass
class ConstInt(Const):
    int: int
    
@dataclass
class ConstLong(Const):
    int: int
    
@dataclass
class ConstUInt(Const):
    int: int
    
@dataclass
class ConstULong(Const):
    int: int