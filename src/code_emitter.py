from .assembly_ast import *
from .semantic_analysis.typechecker import symbol_table
from .asm_allocator import INT_SIZE

def emit_program_code(program):
    res = []
    for top_level in program.top_levels:
        if isinstance(top_level, AsmFunctionDef):
            res.extend(emit_function(top_level))
        elif isinstance(top_level, AsmStaticVar):
            res.extend(emit_static_var(top_level))
        else:
            raise NotImplementedError(f"Can't generate assembly code for {top_level}")
        res.append("")
    res.append('   .section .note.GNU-stack,"",@progbits')
    return "\n".join(res) + "\n"

def emit_function(func_def):
    res = []
    if func_def.global_:
        res.append(f"   .globl {func_def.name}")
    res.extend([
        f"   .text",
        f"{func_def.name}:",
        f"   pushq  %rbp",
        f"   movq   %rsp, %rbp"])
    for instr in func_def.instructions:
        lines = emit_instruction(instr)
        if isinstance(lines, list):
            res.extend("   " + line for line in lines)
        else:
            res.append("   " + lines)
    return res

def emit_static_var(static_var):
    res = []
    if static_var.global_:
        res.append(f"   .globl {static_var.name}")
    if static_var.init != 0:
        res.append(f"   .data")
    else:
        res.append(f"   .bss")
    res.append(f"   .align 4")
    res.append(f"{static_var.name}:")
    if static_var.init != 0:
        res.append(f"   .long {static_var.init}")
    else:
        res.append(f"   .zero {INT_SIZE}")
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
        case AsmData(name):
            return f"{name}(%rip)"
        case AsmImm(int):
            return f"${int}"
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {operand}")