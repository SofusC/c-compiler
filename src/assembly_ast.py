from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import List

@dataclass
class AsmProgram():
    function_definitions: List[AsmFunctionDef]

@dataclass
class AsmFunctionDef():
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

@dataclass
class AsmDeallocateStack(AsmInstruction):
    int: int

@dataclass
class AsmPush(AsmInstruction):
    operand: AsmOperand

@dataclass
class AsmCall(AsmInstruction):
    identifier: str

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
    AX  = (f"%rax",  f"%eax",  f"%al")
    CX  = (f"%rcx",  f"%ecx",  f"%cl")
    DX  = (f"%rdx",  f"%edx",  f"%dl")
    DI  = (f"%rdi",  f"%edi",  f"%dil")
    SI  = (f"%rsi",  f"%esi",  f"%sil")
    R8  = (f"%r8",   f"%r8d",  f"%r8b")
    R9  = (f"%r9",   f"%r9d",  f"%r9b")
    R10 = (f"%r10",  f"%r10d", f"%r10b")
    R11 = (f"%r11",  f"%r11d", f"%r11b")

    def __init__(self, qword, dword, byte):
        self._qword = qword
        self._dword = dword
        self._byte = byte

    def as_qword(self):
        return self._qword

    def as_dword(self):
        return self._dword
    
    def as_byte(self):
        return self._byte