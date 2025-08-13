from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import List
from .semantic_analysis.typechecker import StaticInit

@dataclass
class AsmProgram():
    top_levels: List[AsmTopLevel]



class AssemblyType(Enum):
    Longword = "l"
    Quadword = "q"


class AsmTopLevel():
    pass

@dataclass
class AsmFunctionDef(AsmTopLevel):
    name: str
    global_: bool
    instructions: List[AsmInstruction]

@dataclass
class AsmStaticVar(AsmTopLevel):
    name: str
    global_: bool
    alignment: int
    init: StaticInit


class AsmInstruction():
    pass

@dataclass
class AsmMov(AsmInstruction):
    type_: AssemblyType
    src: AsmOperand
    dst: AsmOperand

@dataclass
class AsmMovsx(AsmInstruction):
    src: AsmOperand
    dst: AsmOperand

@dataclass
class AsmUnary(AsmInstruction):
    unary_operator: AsmUnaryOperator
    type_: AssemblyType
    operand: AsmOperand

@dataclass
class AsmBinary(AsmInstruction):
    binary_operator: AsmBinaryOperator
    type_: AssemblyType
    src: AsmOperand
    dst: AsmOperand

@dataclass
class AsmCmp(AsmInstruction):
    type_: AssemblyType
    operand1: AsmOperand
    operand2: AsmOperand

@dataclass
class AsmIdiv(AsmInstruction):
    type_: AssemblyType
    src: AsmOperand

@dataclass
class AsmCdq(AsmInstruction):
    type_: AssemblyType

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
class AsmPush(AsmInstruction):
    operand: AsmOperand

@dataclass
class AsmCall(AsmInstruction):
    identifier: str

class AsmRet(AsmInstruction):
    pass



class AsmUnaryOperator(Enum):
    Neg = "neg"
    Not = "not"

class AsmBinaryOperator(Enum):
    Add = "add"
    Sub = "sub"
    Mult = "imul"



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

@dataclass
class AsmData(AsmOperand):
    identifier: str



class AsmCondCode(Enum):
    E  = f"e "
    NE = f"ne"
    G  = f"g "
    GE = f"ge"
    L  = f"l "
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
    SP  = (f"%rsp",  f"%esp",  f"%spl")

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
    
    @classmethod
    def system_v_argument_regs(cls):
        return [cls.DI, cls.SI, cls.DX, cls.CX, cls.R8, cls.R9]