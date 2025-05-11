from __future__ import annotations
from dataclasses import dataclass
from abc import ABC
from typing import List
from enum import Enum, auto
import parser

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
    


class IREmitter:
    register_counter = 0
    def make_temporary(self):
        register_name = "tmp." + str(self.register_counter)
        self.register_counter += 1
        return register_name
    
    def emit_binary_operator(self, ast_node):
        match ast_node:
            case parser.BinaryOperator.Add:
                return IRBinaryOperator.ADD
            case parser.BinaryOperator.Subtract:
                return IRBinaryOperator.SUBTRACT
            case parser.BinaryOperator.Multiply:
                return IRBinaryOperator.MULTIPLY
            case parser.BinaryOperator.Divide:
                return IRBinaryOperator.DIVIDE
            case parser.BinaryOperator.Remainder:
                return IRBinaryOperator.REMAINDER

    def emit_unary_operator(self, ast_node):
        match ast_node:
            case parser.UnaryOperator.Complement:
                return IRUnaryOperator.COMPLEMENT
            case parser.UnaryOperator.Negate:
                return IRUnaryOperator.NEGATE
            
    def emit_exp(self, ast_node, instructions):
        match ast_node:
            case parser.Constant(constant):
                return IRConstant(constant)
            case parser.Unary(unary_operator, exp):
                src = self.emit_exp(exp, instructions)
                dst_name = self.make_temporary()
                dst = IRVar(dst_name)
                tacky_op = self.emit_unary_operator(unary_operator)
                instructions.append(IRUnary(tacky_op,src,dst))
                return dst
            case parser.Binary(op, e1, e2):
                v1 = self.emit_exp(e1, instructions)
                v2 = self.emit_exp(e2, instructions)
                dst_name = self.make_temporary()
                dst = IRVar(dst_name)
                tacky_op = self.emit_binary_operator(op)
                instructions.append(IRBinary(tacky_op, v1, v2, dst))
                return dst
            case _:
                raise RuntimeError(f"{ast_node} not implemented")

    def emit_statement(self, ast_node):
        instructions = []
        ret = self.emit_exp(ast_node.exp, instructions)
        instructions.append(IRReturn(ret))
        return instructions
    
    def emit_function(self, ast_node):
        return IRFunctionDefinition(ast_node.name, self.emit_statement(ast_node.body))

    def emit_program(self, ast_node):
        return IRProgram(self.emit_function(ast_node.function))
