
class asm_program():
    def __init__(self, _function_definition):
        self.function_definition = _function_definition

    def generate(self,file):
        self.function_definition.generate(file)
        file.write('   .section .note.GNU-stack,"",@progbits\n')

    def pretty(self, indent = 0):
        print(" " * indent + "Program(")
        self.function_definition.pretty(indent + 1)
        print(" " * indent + ")")

class asm_function():
    def __init__(self, _name, _instructions):
        self.name = _name
        self.instructions = _instructions

    def generate(self, file):
        file.write(f"   .globl {self.name}\n")
        file.write(f"{self.name}:\n")
        for ins in self.instructions:
            ins.generate(file)

    def pretty(self, indent = 0):
        print(" " * indent + "Function(")
        print(" " * (indent + 1) + f"name={self.name}")
        print(" " * (indent + 1) + f"instructions:")
        for ins in self.instructions:
            ins.pretty(indent+2)
        print(" " * indent + ")")

class asm_mov():
    def __init__(self, _src, _dst):
        self.src = _src
        self.dst = _dst

    def generate(self, file):
        file.write(f"   movl   ")
        self.src.generate(file)
        file.write(f",")
        self.dst.generate(file)
        file.write(f"\n")

    def pretty(self, indent = 0):
        print(" " * indent + f"Mov({self.src}, {self.dst})")

class asm_ret():
    def generate(self, file):
        file.write(f"   ret\n")

    def pretty(self, indent = 0):
        print(" " * indent + f"Ret")

class asm_register():
    def generate(self, file):
        file.write(f"%eax")

    def __str__(self):
        return f"Register"

class asm_imm():
    def __init__(self, _int):
        self.int = _int

    def generate(self, file):
        file.write(f"${self.int}")

    def __str__(self):
        return f"Imm({self.int})"
