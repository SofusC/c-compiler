from __future__ import annotations
from dataclasses import dataclass
from abc import ABC
from typing import List
from enum import Enum, auto

class TackyNode(ABC):
    pass

@dataclass
class IRProgram(TackyNode):
    function: IRFunctionDefinition

@dataclass
class IRFunctionDefinition(TackyNode):
    name: str
    body: List[IRInstruction]
    

class IRInstruction(TackyNode):
    pass

@dataclass
class IRReturn(IRInstruction):
    val: IRVal
    
@dataclass
class IRUnary(IRInstruction):
    unary_operator: IRUnaryOperator
    src: IRVal
    dst: IRVal

@dataclass
class IRBinary(IRInstruction):
    binary_operator: IRBinaryOperator
    src1: IRVal
    src2: IRVal
    dst: IRVal



class IRVal(TackyNode):
    pass

@dataclass
class IRConstant(IRVal):
    int: int
    
@dataclass
class IRVar(IRVal):
    identifier: str



class IRUnaryOperator(Enum):
    Complement  = auto()
    Negate      = auto()
    
class IRBinaryOperator(Enum):
    Add         = auto()
    Subtract    = auto()
    Multiply    = auto()
    Divide      = auto()
    Remainder   = auto()
        
