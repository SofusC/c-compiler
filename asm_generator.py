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

    # TODO Improve this functions structure
    def lower_pseudo_regs(self, ast_node):
        match ast_node:
            case AsmPseudo(identifier = identifier):
                if identifier not in self.identifiers:
                    self.stack_counter -= 4
                    self.identifiers[identifier] = self.stack_counter
                return AsmStack(self.identifiers[identifier])
            case AsmMov(src = src, dst = dst):
                ast_node.src = self.lower_pseudo_regs(src)
                ast_node.dst = self.lower_pseudo_regs(dst)
            case AsmUnary(operand = operand):
                ast_node.operand = self.lower_pseudo_regs(operand)
            case AsmBinary(_, src, dst):
                ast_node.src = self.lower_pseudo_regs(src)
                ast_node.dst = self.lower_pseudo_regs(dst)
            case AsmIdiv(src):
                ast_node.src = self.lower_pseudo_regs(src)
            case AsmProgram(function_definition = function_definition):
                self.lower_pseudo_regs(function_definition)
            case AsmFunction(name = name, instructions = instructions):
                for instruction in instructions:
                    self.lower_pseudo_regs(instruction)
            case _:
                return ast_node
            
def lower_to_asm(ast_node):
    match ast_node:
        # TODO Remove all the redundant "function = f" pattern in this file
        case IRProgram(function = f):
            return AsmProgram(lower_to_asm(f))
        case IRFunctionDefinition(name = name, body = instructions):
            asm_instructions = []
            for instruction in instructions:
                asm_instructions += lower_instr(instruction)
            return AsmFunction(name, asm_instructions)
        
def lower_instr(ast_node):
    match ast_node:
        case IRReturn(val = val):
            val = lower_operand(val)
            return [AsmMov(val, AsmReg(AsmRegs.AX)), 
                    AsmRet()]
        case IRUnary(unary_operator = u, src = src, dst = dst):
            return [AsmMov(lower_operand(src), lower_operand(dst)), 
                    AsmUnary(lower_operator(u), lower_operand(dst))]
        case IRBinary(IRBinaryOperator.DIVIDE, src1, src2, dst):
            dividend_reg = AsmReg(AsmRegs.AX)
            return [AsmMov(lower_operand(src1), dividend_reg),
                    AsmCdq(),
                    AsmIdiv(lower_operand(src2)),
                    AsmMov(dividend_reg, lower_operand(dst))]
        case IRBinary(IRBinaryOperator.REMAINDER, src1, src2, dst):
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
        # TODO Enums capitalized?
        case IRUnaryOperator.COMPLEMENT:
            return AsmUnaryOperator.Not
        case IRUnaryOperator.NEGATE:
            return AsmUnaryOperator.Neg
        case IRBinaryOperator.ADD:
            return AsmBinaryOperator.Add
        case IRBinaryOperator.SUBTRACT:
            return AsmBinaryOperator.Sub
        case IRBinaryOperator.MULTIPLY:
            return AsmBinaryOperator.Mult
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")
        
def lower_operand(ast_node):
    match ast_node:
        case IRConstant(int = constant):
            return AsmImm(constant)
        case IRVar(identifier = identifier):
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
