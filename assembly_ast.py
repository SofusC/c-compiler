import emitter

class AsmProgram():
    def __init__(self, _function_definition):
        self.function_definition = _function_definition

    def generate(self,file):
        self.function_definition.generate(file)
        file.write('   .section .note.GNU-stack,"",@progbits\n')

    def __str__(self, indent = 0):
        return " " * indent + "Program(" + "\n" + self.function_definition.__str__(indent + 1) + "\n" + " " * indent + ")"

class AsmFunction():
    def __init__(self, _name, _instructions):
        self.name = _name
        self.instructions = _instructions

    def generate(self, file):
        file.write(f"   .globl {self.name}\n")
        file.write(f"{self.name}:\n")
        for ins in self.instructions:
            ins.generate(file)

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

    def generate(self, file):
        file.write(f"   movl   ")
        self.src.generate(file)
        file.write(f",")
        self.dst.generate(file)
        file.write(f"\n")

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
    def generate(self, file):
        file.write(f"   ret\n")

    def __str__(self, indent = 0):
        return " " * indent + f"Ret"


class AsmNot():
    def __str__(self):
        return f"Not"
    
class AsmNeg():
    def __str__(self):
        return f"Neg"
    

class AsmImm():
    def __init__(self, _int):
        self.int = _int

    def generate(self, file):
        file.write(f"${self.int}")

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

    
class AsmGenerator():
    identifiers = {}
    stack_counter = 0
    def fix_invalid_mov_instructions(self, program):
        function = program.function_definition
        new_instructions = []
        for instruction in function.instructions:
            if isinstance(instruction, AsmMov):
                src, dst = instruction.src, instruction.dst
                if isinstance(src, AsmStack) and isinstance(dst, AsmStack):
                    tmp = AsmReg("R10")
                    new_instructions += [AsmMov(src, tmp), AsmMov(tmp, dst)]
                    continue
            new_instructions.append(instruction)
        function.instructions = new_instructions

    def insert_stack_allocation(self, program):
        function = program.function_definition
        function.instructions[:0] = [AsmAllocateStack(abs(self.stack_counter))]

    def replace_pseudo_registers(self, ast_node):
        match ast_node:
            case AsmPseudo(identifier = identifier):
                if identifier not in self.identifiers:
                    self.stack_counter -= 4
                    self.identifiers[identifier] = self.stack_counter
                return AsmStack(self.identifiers[identifier])
            case AsmMov(src = src, dst = dst):
                ast_node.src = self.replace_pseudo_registers(src)
                ast_node.dst = self.replace_pseudo_registers(dst)
            case AsmUnary(operand = operand):
                ast_node.operand = self.replace_pseudo_registers(operand)
            case AsmProgram(function_definition = function_definition):
                self.replace_pseudo_registers(function_definition)
            case AsmFunction(name = name, instructions = instructions):
                for instruction in instructions:
                    self.replace_pseudo_registers(instruction)
            case _:
                return ast_node
                
    def generate_asm_ast(self, ast_node):
        match ast_node:
            case emitter.IRProgram(function = f):
                program = AsmProgram(self.generate_asm_ast(f))
                self.replace_pseudo_registers(program)
                self.insert_stack_allocation(program)
                self.fix_invalid_mov_instructions(program)
                return program
            case emitter.IRFunctionDefinition(name = name, body = instructions):
                asm_instructions = []
                for instruction in instructions:
                    asm_instructions += self.generate_asm_ast(instruction)
                return AsmFunction(name, asm_instructions)
            case emitter.IRReturn(val = val):
                val = self.generate_asm_ast(val)
                return [AsmMov(val, AsmReg("AX")), 
                        AsmRet()]
            case emitter.IRUnary(unary_operator = u, src = src, dst = dst):
                return [AsmMov(self.generate_asm_ast(src), self.generate_asm_ast(dst)), 
                        AsmUnary(self.generate_asm_ast(u), self.generate_asm_ast(dst))]
            case emitter.IRComplement():
                return AsmNot()
            case emitter.IRNegate():
                return AsmNeg()
            case emitter.IRConstant(int = constant):
                return AsmImm(constant)
            case emitter.IRVar(identifier = identifier):
                return AsmPseudo(identifier)
            case _:
                raise NotImplementedError(f"IR object {ast_node} is not implemented yet.")
            
    def generate_asm_code(self, ast_node):
        match ast_node:
            case AsmProgram(function_definition = function_definition):
                res = self.generate_asm_code(function_definition)
                res += '   .section .note.GNU-stack,"",@progbits\n'
                return res
            case AsmFunction(name = name, instructions = instructions):
                res =   f"   .globl {name}\n"
                res +=  f"{name}:\n"
                res +=  f"   pushq  %rbp\n"
                res +=  f"   movq   %rsp, %rbp\n"
                for instruction in instructions:
                    res += self.generate_asm_code(instruction)
                return res
            case AsmMov(src = src, dst = dst):
                src_operand = self.generate_asm_code(src)
                dst_operand = self.generate_asm_code(dst)
                return  f"   movl   {src_operand}, {dst_operand}\n"
            case AsmRet():
                res =   f"   movq   %rbp, %rsp\n"
                res +=  f"   popq   %rbp\n"
                res +=  f"   ret\n"
                return res
            case AsmUnary(unary_operator = unary_operator, operand = operand):
                unary_instruction = self.generate_asm_code(unary_operator)
                asm_operand = self.generate_asm_code(operand)
                res =  f"   {unary_instruction}   {asm_operand}\n"
                return res
            case AsmAllocateStack(int = int):
                res =  f"   subq   ${int},  %rsp\n"
                return res
            case AsmNeg():
                return "negl"
            case AsmNot():
                return "notl"
            case AsmReg(reg = "AX"):
                return "%eax"
            case AsmReg(reg = "R10"):
                return "%r10d"
            case AsmStack(int = int):
                return f"{int}(%rbp)"
            case AsmImm(int = int):
                return f"${int}"
            case _:
                raise NotImplementedError(f"Cant generate assembly code for {ast_node}")
