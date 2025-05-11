from ir_ast import *
from assembly_ast import *

class AsmAllocator():
    def __init__(self):
        self.identifiers = {}
        self.stack_counter = 0

    def fix_invalid_mov_instructions(self, program):
        function = program.function_definition
        new_instructions = []
        for instruction in function.instructions:
            if isinstance(instruction, AsmMov):
                src, dst = instruction.src, instruction.dst
                if isinstance(src, AsmStack) and isinstance(dst, AsmStack):
                    tmp = AsmReg(AsmRegs.R10)
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
            
def generate_asm_ast(ast_node):
    match ast_node:
        case IRProgram(function = f):
            return AsmProgram(generate_asm_ast(f))
        case IRFunctionDefinition(name = name, body = instructions):
            asm_instructions = []
            for instruction in instructions:
                asm_instructions += generate_asm_ast(instruction)
            return AsmFunction(name, asm_instructions)
        case IRReturn(val = val):
            val = generate_asm_ast(val)
            return [AsmMov(val, AsmReg(AsmRegs.AX)), 
                    AsmRet()]
        case IRUnary(unary_operator = u, src = src, dst = dst):
            return [AsmMov(generate_asm_ast(src), generate_asm_ast(dst)), 
                    AsmUnary(generate_asm_ast(u), generate_asm_ast(dst))]
        case IRUnaryOperator.COMPLEMENT:
            return AsmUnaryOperator.Not
        case IRUnaryOperator.NEGATE:
            return AsmUnaryOperator.Neg
        case IRConstant(int = constant):
            return AsmImm(constant)
        case IRVar(identifier = identifier):
            return AsmPseudo(identifier)
        case _:
            raise NotImplementedError(f"IR object {ast_node} is not implemented yet.")
        
def generate_asm_code(ast_node):
    match ast_node:
        case AsmProgram(function_definition = function_definition):
            res = generate_asm_code(function_definition)
            res += '   .section .note.GNU-stack,"",@progbits\n'
            return res
        case AsmFunction(name = name, instructions = instructions):
            res =   f"   .globl {name}\n"
            res +=  f"{name}:\n"
            res +=  f"   pushq  %rbp\n"
            res +=  f"   movq   %rsp, %rbp\n"
            for instruction in instructions:
                res += generate_asm_code(instruction)
            return res
        case AsmMov(src = src, dst = dst):
            src_operand = generate_asm_code(src)
            dst_operand = generate_asm_code(dst)
            return  f"   movl   {src_operand}, {dst_operand}\n"
        case AsmRet():
            res =   f"   movq   %rbp, %rsp\n"
            res +=  f"   popq   %rbp\n"
            res +=  f"   ret\n"
            return res
        case AsmUnary(unary_operator = unary_operator, operand = operand):
            unary_instruction = generate_asm_code(unary_operator)
            asm_operand = generate_asm_code(operand)
            res =  f"   {unary_instruction}   {asm_operand}\n"
            return res
        case AsmAllocateStack(int = int):
            res =  f"   subq   ${int},  %rsp\n"
            return res
        case AsmUnaryOperator.Neg:
            return "negl"
        case AsmUnaryOperator.Not:
            return "notl"
        case AsmReg(reg = AsmRegs.AX):
            return f"%eax"
        case AsmReg(reg = AsmRegs.R10):
            return f"%r10d"
        case AsmStack(int = int):
            return f"{int}(%rbp)"
        case AsmImm(int = int):
            return f"${int}"
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {ast_node}")
