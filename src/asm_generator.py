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
                case AsmCmp(AsmStack() as operand1, AsmStack() as operand2):
                    tmp = AsmReg(AsmRegs.R10)
                    return [AsmMov(operand1, tmp),
                            AsmCmp(tmp, operand2)]
                case AsmCmp(operand1, AsmImm() as operand2):
                    tmp = AsmReg(AsmRegs.R11)
                    return [AsmMov(operand2, tmp),
                            AsmCmp(operand1, tmp)]
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

    def lower_pseudo_regs(self, program): # TODO: this function needs refactoring
        def remove_pseudos(ast_node):
            match ast_node:
                case AsmPseudo(identifier):
                    stack_offset = self._allocate_stack_slot(identifier)
                    return AsmStack(stack_offset)
                case _:
                    return ast_node
        def check_instruction(instruction):
            match instruction:
                case AsmMov(src, dst):
                    return AsmMov(remove_pseudos(src), remove_pseudos(dst))
                case AsmUnary(unop, operand):
                    return AsmUnary(unop, remove_pseudos(operand))
                case AsmBinary(binop, src, dst):
                    return AsmBinary(binop, remove_pseudos(src), remove_pseudos(dst))
                case AsmCmp(operand1, operand2):
                    return AsmCmp(remove_pseudos(operand1), remove_pseudos(operand2))
                case AsmIdiv(src):
                    return AsmIdiv(remove_pseudos(src))
                case AsmSetCC(cond_code, operand):
                    return AsmSetCC(cond_code, remove_pseudos(operand))
                case _:
                    return instruction
        instructions = program.function_definition.instructions
        lowered_instrs = [check_instruction(instr) for instr in instructions]
        program.function_definition.instructions = lowered_instrs
            
def lower_to_asm(ast_node):
    match ast_node:
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
            return lower_unary(unop, src, dst)
        case IRBinary(binop, src1, src2, dst):
            return lower_binary(binop, src1, src2, dst)
        case IRJump(target):
            return [AsmJmp(target)]
        case IRJumpIfZero(condition, target):
            return [AsmCmp(AsmImm(0), lower_operand(condition)),
                    AsmJmpCC(AsmCondCode.E, target)]
        case IRJumpIfNotZero(condition, target):
            return [AsmCmp(AsmImm(0), lower_operand(condition)),
                    AsmJmpCC(AsmCondCode.NE, target)]
        case IRCopy(src, dst):
            return [AsmMov(lower_operand(src), lower_operand(dst))]
        case IRLabel(identifier):
            return [AsmLabel(identifier)]
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")
        

def lower_unary(unop, src, dst):
    match unop:
        case IRUnaryOperator.Not:
            return [AsmCmp(AsmImm(0), src),
                    AsmMov(AsmImm(0), dst),
                    AsmSetCC(AsmCondCode.E, dst)]
        case _:
            return [AsmMov(lower_operand(src), lower_operand(dst)), 
                    AsmUnary(lower_operator(unop), lower_operand(dst))]

        
def lower_binary(binop, src1, src2, dst):
    src1, src2, dst = lower_operand(src1), lower_operand(src2), lower_operand(dst)
    match binop:
        case IRBinaryOperator.Divide:
            dividend_reg = AsmReg(AsmRegs.AX)
            return [AsmMov(src1, dividend_reg),
                    AsmCdq(),
                    AsmIdiv(src2),
                    AsmMov(dividend_reg, dst)]
        case IRBinaryOperator.Remainder:
            return [AsmMov(src1, AsmReg(AsmRegs.AX)),
                    AsmCdq(),
                    AsmIdiv(src2),
                    AsmMov(AsmReg(AsmRegs.DX), dst)]
        case relational if binop.is_relational:
            relational = lower_relational(relational)
            return [AsmCmp(src2, src1),
                    AsmMov(AsmImm(0), dst),
                    AsmSetCC(relational, dst)]
        case _:
            binop = lower_operator(binop)
            return [AsmMov(src1, dst),
                    AsmBinary(binop, src2, dst)]

def lower_relational(ast_node):
    match ast_node:
        case IRBinaryOperator.Equal:
            return AsmCondCode.E
        case IRBinaryOperator.NotEqual:
            return AsmCondCode.NE
        case IRBinaryOperator.LessThan:
            return AsmCondCode.L
        case IRBinaryOperator.LessOrEqual:
            return AsmCondCode.LE
        case IRBinaryOperator.GreaterThan:
            return AsmCondCode.G
        case IRBinaryOperator.GreaterOrEqual:
            return AsmCondCode.GE
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
        
def emit_function(name, instructions):
    res =   f"   .globl {name}\n"
    res +=  f"{name}:\n"
    res +=  f"   pushq  %rbp\n"
    res +=  f"   movq   %rsp, %rbp\n"
    for instruction in instructions:
        res += emit_code(instruction)
    return res
    
def emit_operand(operand):
    match operand:
        case AsmReg(reg):
            return reg.value
        case AsmStack(offset):
            return f"{offset}(%rbp)"
        case AsmImm(int):
            return f"${int}"
        
def emit_code(ast_node): # TODO: Move this to a code_emitter.py file
    match ast_node:
        case AsmProgram(function_definition):
            res = emit_code(function_definition)
            res += '   .section .note.GNU-stack,"",@progbits\n'
            return res
        case AsmFunction(name, instructions):
            return emit_function(name, instructions)
        case AsmMov(src, dst):
            src_operand = emit_code(src)
            dst_operand = emit_code(dst)
            return  f"   movl   {src_operand}, {dst_operand}\n"
        case AsmRet():
            res =   f"   movq   %rbp, %rsp\n"
            res +=  f"   popq   %rbp\n"
            res +=  f"   ret\n"
            return res
        case AsmUnary(unop, operand):
            unop = emit_code(unop)
            asm_operand = emit_code(operand)
            res =   f"   {unop}   {asm_operand}\n"
            return res
        case AsmBinary(binop, src, dst):
            binop = emit_code(binop)
            src, dst = emit_code(src), emit_code(dst)
            return  f"   {binop}   {src}, {dst}\n"
        case AsmIdiv(operand):
            operand = emit_code(operand)
            return  f"   idivl  {operand}\n"
        case AsmCdq():
            return  f"   cdq\n"
        case AsmAllocateStack(int):
            return  f"   subq   ${int},  %rsp\n"
        case AsmOperand() as operand:
            return emit_operand(operand)
        case AsmUnaryOperator() | AsmBinaryOperator() as op:
            return op.value
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {ast_node}")
