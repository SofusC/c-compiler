from __future__ import annotations
from abc import ABC
from enum import Enum, auto
from dataclasses import dataclass


class ASTNode(ABC):
    pass

@dataclass
class Program(ASTNode):
    function: FunctionDefinition



@dataclass
class FunctionDefinition(ASTNode):
    name: str
    body: Statement



class Statement(ASTNode):
    pass

@dataclass
class Return(Statement):
    exp: Exp



class Exp(ASTNode):
    pass

@dataclass
class Constant(Exp):
    constant: int

@dataclass
class Unary(Exp):
    unary_operator: UnaryOperator
    exp: Exp
    
class UnaryOperator(Enum):
    Complement  = auto()
    Negate      = auto()

@dataclass
class Binary(Exp):
    binary_operator: BinaryOperator
    left_exp: Exp
    right_exp: Exp

class BinaryOperator(Enum):
    Add         = auto()
    Subtract    = auto()
    Multiply    = auto()
    Divide      = auto()
    Remainder   = auto()
