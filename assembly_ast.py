from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass
from typing import List

@dataclass
class AsmProgram():
    function_definition: AsmFunction

    def __str__(self, indent = 0):
        return " " * indent + "Program(" + "\n" + self.function_definition.__str__(indent + 1) + "\n" + " " * indent + ")"

@dataclass
class AsmFunction():
    name: str
    instructions: List[AsmInstruction]

    def __str__(self, indent = 0):
        res = " " * indent + "Function(" + "\n"
        res += " " * (indent + 1) + f"name = {self.name}" + "\n"
        res += " " * (indent + 1) + f"instructions:\n"
        for ins in self.instructions:
            res += ins.__str__(indent+2) + "\n"
        res += " " * indent + ")"
        return res


class AsmInstruction():
    pass

@dataclass
class AsmMov(AsmInstruction):
    src: AsmOperand
    dst: AsmOperand

    def __str__(self, indent = 0):
        return " " * indent + f"Mov({self.src}, {self.dst})"

@dataclass
class AsmUnary(AsmInstruction):
    unary_operator: AsmUnaryOperator
    operand: AsmOperand

    def __str__(self, indent = 0):
        return " " * indent + f"Unary({self.unary_operator}, {self.operand})"

@dataclass
class AsmBinary(AsmInstruction):
    binary_operator: AsmBinaryOperator
    src: AsmOperand
    dst: AsmOperand

    def __str__(self, indent = 0):
        return " " * indent + f"Binary({self.binary_operator}, {self.src}, {self.dst})"
    
@dataclass
class AsmIdiv(AsmInstruction):
    src: AsmOperand

    def __str__(self, indent = 0):
        return " " * indent + f"Idiv({self.src})"
    
class AsmCdq(AsmInstruction):
    def __str__(self, indent = 0):
        return " " * indent + f"Cdq"


    
@dataclass
class AsmAllocateStack(AsmInstruction):
    int: int

    def __str__(self, indent = 0):
        return " " * indent + f"AllocateStack({self.int})"

class AsmRet(AsmInstruction):
    def __str__(self, indent = 0):
        return " " * indent + f"Ret"



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

    def __str__(self):
        return f"Imm({self.int})"
    
@dataclass
class AsmReg(AsmOperand):
    reg: AsmRegs
    
    def __str__(self):
        return f"Reg({self.reg})"
    
@dataclass
class AsmPseudo(AsmOperand):
    identifier: str

    def __str__(self):
        return f"Pseudo({self.identifier})"
    
@dataclass
class AsmStack(AsmOperand):
    int: int

    def __str__(self):
        return f"Stack({self.int})"

    
    
class AsmRegs(Enum):
    AX = auto()
    DX = auto()
    R10 = auto()
    R11 = auto()
