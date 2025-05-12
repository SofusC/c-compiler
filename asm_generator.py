from ir_ast import *
from assembly_ast import *

class AsmAllocator():
    def __init__(self):
        self.identifiers = {}
        self.stack_counter = 0
        
    def legalize_instr(self, program):
        def legalize(instruction):
            match instruction:
                case AsmMov(AsmStack() as src, AsmStack() as dst):
                    tmp = AsmReg(AsmRegs.R10)
                    return [AsmMov(src, tmp), AsmMov(tmp, dst)]
                case AsmBinary(AsmBinaryOperator.Add | AsmBinaryOperator.Sub as binop, AsmStack() as src, AsmStack() as dst):
                    tmp = AsmReg(AsmRegs.R10)
                    return [AsmMov(src, tmp), 
                            AsmBinary(binop, tmp, dst)]
                case AsmBinary(AsmBinaryOperator.Mult, src, AsmStack() as dst):
                    tmp = AsmReg(AsmRegs.R11)
                    return [AsmMov(dst, tmp), 
                            AsmBinary(AsmBinaryOperator.Mult, src, tmp),
                            AsmMov(tmp, dst)]
                case AsmIdiv(AsmImm() as operand):
                    tmp = AsmReg(AsmRegs.R10)
                    return [AsmMov(operand, tmp),
                            AsmIdiv(tmp)]
                case _:
                    return [instruction]
        
        function = program.function_definition
        new_instructions = []
        for instruction in function.instructions:
            new_instructions.extend(legalize(instruction))
        function.instructions = new_instructions

    def add_stack_frame(self, program):
        function = program.function_definition
        function.instructions[:0] = [AsmAllocateStack(abs(self.stack_counter))]

    def _allocate_stack_slot(self, identifier):
        if identifier not in self.identifiers:
            self.stack_counter -= 4
            self.identifiers[identifier] = self.stack_counter
        return self.identifiers[identifier]

    def lower_pseudo_regs(self, program):
        def remove_pseudos(ast_node):
            match ast_node:
                case AsmPseudo(identifier):
                    stack_offset = self._allocate_stack_slot(identifier)
                    return AsmStack(stack_offset)
                case AsmMov(src, dst):
                    return AsmMov(remove_pseudos(src), remove_pseudos(dst))
                case AsmUnary(unop, operand):
                    return AsmUnary(unop, remove_pseudos(operand))
                case AsmBinary(binop, src, dst):
                    return AsmBinary(binop, remove_pseudos(src), remove_pseudos(dst))
                case AsmIdiv(src):
                    return AsmIdiv(remove_pseudos(src))
                case _:
                    return ast_node
        instructions = program.function_definition.instructions
        lowered_instrs = [remove_pseudos(instr) for instr in instructions]
        program.function_definition.instructions = lowered_instrs
            
def lower_to_asm(ast_node):
    match ast_node:
        # TODO Remove all the redundant "function = f" pattern in this file
        case IRProgram(func):
            return AsmProgram(lower_to_asm(func))
        case IRFunctionDefinition(name, instructions):
            asm_instructions = []
            for instruction in instructions:
                asm_instructions += lower_instr(instruction)
            return AsmFunction(name, asm_instructions)
        
def lower_instr(ast_node):
    match ast_node:
        case IRReturn(val):
            val = lower_operand(val)
            return [AsmMov(val, AsmReg(AsmRegs.AX)), 
                    AsmRet()]
        case IRUnary(unop, src, dst):
            return [AsmMov(lower_operand(src), lower_operand(dst)), 
                    AsmUnary(lower_operator(unop), lower_operand(dst))]
        case IRBinary(IRBinaryOperator.Divide, src1, src2, dst):
            dividend_reg = AsmReg(AsmRegs.AX)
            return [AsmMov(lower_operand(src1), dividend_reg),
                    AsmCdq(),
                    AsmIdiv(lower_operand(src2)),
                    AsmMov(dividend_reg, lower_operand(dst))]
        case IRBinary(IRBinaryOperator.Remainder, src1, src2, dst):
            return [AsmMov(lower_operand(src1), AsmReg(AsmRegs.AX)),
                    AsmCdq(),
                    AsmIdiv(lower_operand(src2)),
                    AsmMov(AsmReg(AsmRegs.DX), lower_operand(dst))]
        case IRBinary(binary_operator, src1, src2, dst):
            asm_binop = lower_operator(binary_operator)
            asm_dst = lower_operand(dst)
            return [AsmMov(lower_operand(src1), asm_dst),
                    AsmBinary(asm_binop, lower_operand(src2), asm_dst)]
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")

def lower_operator(ast_node):
    match ast_node:
        case IRUnaryOperator.Complement:
            return AsmUnaryOperator.Not
        case IRUnaryOperator.Negate:
            return AsmUnaryOperator.Neg
        case IRBinaryOperator.Add:
            return AsmBinaryOperator.Add
        case IRBinaryOperator.Subtract:
            return AsmBinaryOperator.Sub
        case IRBinaryOperator.Multiply:
            return AsmBinaryOperator.Mult
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")
        
def lower_operand(ast_node):
    match ast_node:
        case IRConstant(constant):
            return AsmImm(constant)
        case IRVar(identifier):
            return AsmPseudo(identifier)
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")
        
def emit_code(ast_node):
    match ast_node:
        case AsmProgram(function_definition = function_definition):
            res = emit_code(function_definition)
            res += '   .section .note.GNU-stack,"",@progbits\n'
            return res
        case AsmFunction(name = name, instructions = instructions):
            res =   f"   .globl {name}\n"
            res +=  f"{name}:\n"
            res +=  f"   pushq  %rbp\n"
            res +=  f"   movq   %rsp, %rbp\n"
            for instruction in instructions:
                res += emit_code(instruction)
            return res
        case AsmMov(src = src, dst = dst):
            src_operand = emit_code(src)
            dst_operand = emit_code(dst)
            return  f"   movl   {src_operand}, {dst_operand}\n"
        case AsmRet():
            res =   f"   movq   %rbp, %rsp\n"
            res +=  f"   popq   %rbp\n"
            res +=  f"   ret\n"
            return res
        case AsmUnary(unary_operator = unary_operator, operand = operand):
            unary_instruction = emit_code(unary_operator)
            asm_operand = emit_code(operand)
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
