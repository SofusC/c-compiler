from .assembly_ast import *
from .semantic_analysis.typechecker import symbol_table

def emit_program_code(program):
    res = []
    for function in program.function_definitions:
        res.extend(emit_function(function.name, function.instructions))
    res.append('   .section .note.GNU-stack,"",@progbits')
    return "\n".join(res) + "\n"

def emit_function(name, instructions):
    res = [f"   .globl {name}",
           f"{name}:",
           f"   pushq  %rbp",
           f"   movq   %rsp, %rbp"]
    for instr in instructions:
        lines = emit_instruction(instr)
        if isinstance(lines, list):
            res.extend("   " + line for line in lines)
        else:
            res.append("   " + lines)
    return res
        
def emit_instruction(ast_node):
    match ast_node:
        case AsmMov(src, dst):
            return f"movl   {emit_operand(src)}, {emit_operand(dst)}"
        case AsmRet():
            return [
                f"movq   %rbp, %rsp",
                f"popq   %rbp",
                f"ret"
            ]
        case AsmUnary(unop, operand):
            return f"{unop.value}   {emit_operand(operand)}"
        case AsmBinary(binop, src, dst):
            return f"{binop.value}   {emit_operand(src)}, {emit_operand(dst)}"
        case AsmIdiv(operand):
            return f"idivl  {emit_operand(operand)}"
        case AsmCdq():
            return f"cdq"
        case AsmAllocateStack(size):
            return f"subq   ${size},  %rsp"
        case AsmCmp(op1, op2):
            return f"cmpl   {emit_operand(op1)}, {emit_operand(op2)}"
        case AsmJmp(label):
            return f"jmp    .L{label}"
        case AsmJmpCC(cc, label):
            return f"j{cc.value}    .L{label}"
        case AsmSetCC(cc, operand):
            return f"set{cc.value}  {emit_operand(operand, 'byte')}"
        case AsmLabel(label):
            return f".L{label}:"
        case AsmDeallocateStack(size):
            return f"addq   ${size}, %rsp"
        case AsmPush(operand):
            return f"pushq   {emit_operand(operand, 'qword')}"
        case AsmCall(func):
            suffix = "@PLT" if func in symbol_table else ""
            return f"call   {func}{suffix}"
        case _:
            raise NotImplementedError(f"Can't generate assembly code for {ast_node}")

def emit_operand(operand, size = "dword"):
    match operand:
        case AsmReg(reg):
            if size == "byte":
                return reg.as_byte()
            if size == "dword":
                return reg.as_dword()
            if size == "qword":
                return reg.as_qword()
        case AsmStack(offset):
            return f"{offset}(%rbp)"
        case AsmImm(int):
            return f"${int}"
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {operand}")