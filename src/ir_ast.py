from __future__ import annotations
from dataclasses import dataclass
from abc import ABC
from typing import List
from enum import Enum, auto
from .c_ast import Type, Const
from .semantic_analysis.typechecker import StaticInit

class TackyNode(ABC):
    pass

@dataclass
class IRProgram(TackyNode):
    toplevels: List[IRTopLevel]



class IRTopLevel(TackyNode):
    pass

@dataclass
class IRFunctionDefinition(IRTopLevel):
    name: str
    global_: bool
    params: List[str]
    body: List[IRInstruction]

@dataclass
class IRStaticVariable(IRTopLevel):
    name: str
    global_: bool
    type: Type
    init: StaticInit



class IRInstruction(TackyNode):
    pass

@dataclass
class IRReturn(IRInstruction):
    val: IRVal

@dataclass
class IRSignExtend(IRInstruction):
    src: IRVal
    dst: IRVal

@dataclass
class IRTruncate(IRInstruction):
    src: IRVal
    dst: IRVal

@dataclass
class IRZeroExtend(IRInstruction):
    src: IRVal
    dst: IRVal
    
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

@dataclass
class IRCopy(IRInstruction):
    src: IRVal
    dst: IRVal

@dataclass
class IRJump(IRInstruction):
    target: str

@dataclass
class IRJumpIfZero(IRInstruction):
    condition: IRVal
    target: str

@dataclass
class IRJumpIfNotZero(IRInstruction):
    condition: IRVal
    target: str

@dataclass
class IRLabel(IRInstruction):
    identifier: str

@dataclass
class IRFunCall(IRInstruction):
    fun_name: str
    args: List[IRVal]
    dst: IRVal
    


class IRVal(TackyNode):
    pass

@dataclass
class IRConstant(IRVal):
    const: Const
    
@dataclass
class IRVar(IRVal):
    identifier: str



class IRUnaryOperator(Enum):
    Complement  = auto()
    Negate      = auto()
    Not         = auto()
    
class IRBinaryOperator(Enum):
    Add             = auto()
    Subtract        = auto()
    Multiply        = auto()
    Divide          = auto()
    Remainder       = auto()
    
    Equal           = auto()
    NotEqual        = auto()
    LessThan        = auto()
    LessOrEqual     = auto()
    GreaterThan     = auto()
    GreaterOrEqual  = auto()

    @property
    def is_relational(self):
        return self in {IRBinaryOperator.Equal, IRBinaryOperator.NotEqual, IRBinaryOperator.LessThan, IRBinaryOperator.LessOrEqual, IRBinaryOperator.GreaterThan, IRBinaryOperator.GreaterOrEqual}
    
    @property
    def is_arithmetic(self):
        return self in {IRBinaryOperator.Add, IRBinaryOperator.Subtract, IRBinaryOperator.Multiply, IRBinaryOperator.Divide, IRBinaryOperator.Remainder}
        
