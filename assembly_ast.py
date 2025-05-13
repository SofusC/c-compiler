from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass
from typing import List

@dataclass
class AsmProgram():
    function_definition: AsmFunction

@dataclass
class AsmFunction():
    name: str
    instructions: List[AsmInstruction]

class AsmInstruction():
    pass

@dataclass
class AsmMov(AsmInstruction):
    src: AsmOperand
    dst: AsmOperand

@dataclass
class AsmUnary(AsmInstruction):
    unary_operator: AsmUnaryOperator
    operand: AsmOperand

@dataclass
class AsmBinary(AsmInstruction):
    binary_operator: AsmBinaryOperator
    src: AsmOperand
    dst: AsmOperand

@dataclass
class AsmIdiv(AsmInstruction):
    src: AsmOperand

    
class AsmCdq(AsmInstruction):
    pass

    
@dataclass
class AsmAllocateStack(AsmInstruction):
    int: int

class AsmRet(AsmInstruction):
    pass


class AsmUnaryOperator(Enum):
    Neg = auto()
    Not = auto()

class AsmBinaryOperator(Enum):
    Add = auto()
    Sub = auto()
    Mult = auto()



class AsmOperand():
    pass

@dataclass
class AsmImm(AsmOperand):
    int: int

@dataclass
class AsmReg(AsmOperand):
    reg: AsmRegs
    
@dataclass
class AsmPseudo(AsmOperand):
    identifier: str

@dataclass
class AsmStack(AsmOperand):
    int: int

    
    
class AsmRegs(Enum):
    AX = auto()
    DX = auto()
    R10 = auto()
    R11 = auto()
