from __future__ import annotations
from enum import Enum
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
class AsmCmp(AsmInstruction):
    operand1: AsmOperand
    operand2: AsmOperand

@dataclass
class AsmIdiv(AsmInstruction):
    src: AsmOperand

class AsmCdq(AsmInstruction):
    pass

@dataclass
class AsmJmp(AsmInstruction):
    identifier: str

@dataclass
class AsmJmpCC(AsmInstruction):
    cond_code: AsmCondCode
    identifier: str

@dataclass
class AsmSetCC(AsmInstruction):
    cond_code: AsmCondCode
    operand: AsmOperand

@dataclass
class AsmLabel(AsmInstruction):
    identifier: str
    
@dataclass
class AsmAllocateStack(AsmInstruction):
    int: int

class AsmRet(AsmInstruction):
    pass



class AsmUnaryOperator(Enum):
    Neg = "negl"
    Not = "notl"

class AsmBinaryOperator(Enum):
    Add = "addl"
    Sub = "subl"
    Mult = "imull"



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


class AsmCondCode(Enum):
    E  = f"e"
    NE = f"ne"
    G  = f"g"
    GE = f"ge"
    L  = f"l"
    LE = f"le"
    
class AsmRegs(Enum):
    AX = f"%eax"
    DX = f"%edx"
    R10 = f"%r10d"
    R11 = f"%r11d"