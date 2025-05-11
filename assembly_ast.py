from enum import Enum, auto

class AsmProgram():
    def __init__(self, _function_definition):
        self.function_definition = _function_definition

    def __str__(self, indent = 0):
        return " " * indent + "Program(" + "\n" + self.function_definition.__str__(indent + 1) + "\n" + " " * indent + ")"

class AsmFunction():
    def __init__(self, _name, _instructions):
        self.name = _name
        self.instructions = _instructions

    def __str__(self, indent = 0):
        res = " " * indent + "Function(" + "\n"
        res += " " * (indent + 1) + f"name = {self.name}" + "\n"
        res += " " * (indent + 1) + f"instructions:\n"
        for ins in self.instructions:
            res += ins.__str__(indent+2) + "\n"
        res += " " * indent + ")"
        return res



class AsmMov():
    def __init__(self, _src, _dst):
        self.src = _src
        self.dst = _dst

    def __str__(self, indent = 0):
        return " " * indent + f"Mov({self.src}, {self.dst})"

class AsmUnary():
    def __init__(self, _unary_operator, _operand):
        self.unary_operator = _unary_operator
        self.operand = _operand

    def __str__(self, indent = 0):
        return " " * indent + f"Unary({self.unary_operator}, {self.operand})"
    
class AsmAllocateStack():
    def __init__(self, _int):
        self.int = _int

    def __str__(self, indent = 0):
        return " " * indent + f"AllocateStack({self.int})"

class AsmRet():
    def __str__(self, indent = 0):
        return " " * indent + f"Ret"



class AsmUnaryOperator(Enum):
    Neg = auto()
    Not = auto()



class AsmImm():
    def __init__(self, _int):
        self.int = _int

    def __str__(self):
        return f"Imm({self.int})"
    
class AsmReg():
    def __init__(self, _reg):
        self.reg = _reg

    def __str__(self):
        return f"Reg({self.reg})"
    
class AsmPseudo():
    def __init__(self, _identifier):
        self.identifier = _identifier

    def __str__(self):
        return f"Pseudo({self.identifier})"
    
class AsmStack():
    def __init__(self, _int):
        self.int = _int   

    def __str__(self):
        return f"Stack({self.int})"

    
    
class AsmRegs(Enum):
    AX = auto()
    R10 = auto()
