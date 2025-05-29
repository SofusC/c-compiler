from __future__ import annotations
from abc import ABC
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class ASTNode(ABC):
    pass


@dataclass
class Program(ASTNode):
    function: FunctionDefinition

@dataclass
class FunctionDefinition(ASTNode):
    name: str
    body: Block



@dataclass
class Block(ASTNode):
    block_items: List[BlockItem]



class BlockItem(ASTNode):
    pass

@dataclass
class Declaration(BlockItem):
    name: str
    init: Exp | None

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

class Compound(Statement):
    block: Block

class Null(Statement):
    pass



class Exp(ASTNode):
    pass

@dataclass
class Constant(Exp):
    constant: int

@dataclass
class Var(Exp):
    identifier: str

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



class UnaryOperator(Enum):
    Complement = auto()
    Negate = auto()
    Not = auto()

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
