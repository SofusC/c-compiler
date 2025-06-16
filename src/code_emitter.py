from assembly_ast import *
from semantic_analyser import symbol_table

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
    for instruction in instructions:
        res.extend(["   " + line for line in emit_code(instruction)])
    return res
        
def emit_code(ast_node):
    match ast_node:
        case AsmMov(src, dst):
            return [f"movl   {emit_operand(src)}, {emit_operand(dst)}"]
        case AsmRet():
            res = [f"movq   %rbp, %rsp",
                   f"popq   %rbp",
                   f"ret"]
            return res
        case AsmUnary(unop, operand):
            return [f"{unop.value}   {emit_operand(operand)}"]
        case AsmBinary(binop, src, dst):
            src, dst = emit_operand(src), emit_operand(dst)
            return [f"{binop.value}   {src}, {dst}"]
        case AsmIdiv(operand):
            return [f"idivl  {emit_operand(operand)}"]
        case AsmCdq():
            return [f"cdq"]
        case AsmAllocateStack(int):
            return [f"subq   ${int},  %rsp"]
        case AsmCmp(operand1, operand2):
            return [f"cmpl   {emit_operand(operand1)}, {emit_operand(operand2)}"]
        case AsmJmp(label):
            return [f"jmp   .L{label}"]
        case AsmJmpCC(cc, label):
            return [f"j{cc.value}    .L{label}"]
        case AsmSetCC(cc, operand):
            operand = emit_operand(operand, "byte")
            return [f"set{cc.value}  {operand}"]
        case AsmLabel(label):
            return [f".L{label}:"]
        case AsmDeallocateStack(int):
            return [f"addq   ${int}, %rsp"]
        case AsmPush(operand):
            operand = emit_operand(operand, "qword")
            return [f"pushq   {operand}"]
        case AsmCall(func):
            res = f"call   {func}"
            if func in symbol_table:
                res += "@PLT"
            return [res]
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {ast_node}")

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