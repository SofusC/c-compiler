from __future__ import annotations
from abc import ABC
from enum import Enum, auto
from dataclasses import dataclass

# TODO Write common pretty printer for all ASTs

class ASTNode(ABC):
    def __str__(self, level = 0):
        def indent(text, level):
            prefix = "   "
            return "\n".join(prefix * level + line for line in text.splitlines())
        
        class_name = self.__class__.__name__
        fields = self.__dict__.items()
        field_strings = []
        for _, value in fields:
            field_strings.append(f"{value}")
        body = "\n".join(field_strings)
        return f"{indent(class_name + '(', level)}\n{indent(body, level + 1)}\n{indent(')', level)}"


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
