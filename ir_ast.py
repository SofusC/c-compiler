from __future__ import annotations
from dataclasses import dataclass
from abc import ABC
from typing import List
from enum import Enum, auto

class TackyNode(ABC):
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
class IRProgram(TackyNode):
    function: IRFunctionDefinition

@dataclass
class IRFunctionDefinition(TackyNode):
    name: str
    body: List[IRInstruction]
    
    def __str__(self):
        def indent(text, level):
            prefix = "   "
            return "\n".join(prefix * level + str(line) for line in text)
        return f"IRFunctionDefinition(\n{indent(['name: ' + self.name], 1)}\n{indent(['instructions:'], 1)}\n{indent(self.body, 2)}"
        


class IRInstruction(TackyNode):
    def __str__(self):
        class_name = self.__class__.__name__
        fields = self.__dict__.items()
        field_strings = []
        for _, field in fields:
            field_strings.append(f"{field}")
        return f"{class_name}(" + ", ".join(field_strings) + ")"

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
    def __str__(self):
        class_name = self.__class__.__name__
        value, = self.__dict__.values()
        return f"{class_name}({value})"

@dataclass
class IRConstant(IRVal):
    int: int
    
@dataclass
class IRVar(IRVal):
    identifier: str



class IRUnaryOperator(Enum):
    COMPLEMENT  = auto()
    NEGATE      = auto()

    def __str__(self):
        return f"{self.name}"
    
class IRBinaryOperator(Enum):
    ADD         = auto()
    SUBTRACT    = auto()
    MULTIPLY    = auto()
    DIVIDE      = auto()
    REMAINDER   = auto()

    def __str__(self):
        return f"{self.name}"
    
