from .assembly_ast import *
from .semantic_analysis.symbol_table import IntInit, LongInit
from .asm_allocator import backend_symbol_table

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

def emit_static_var(static_var: AsmStaticVar):
    res = []
    if static_var.global_:
        res.append(f"   .globl {static_var.name}")
        
    section = ".data" if static_var.init.int != 0 else ".bss"
    res.append(f"   {section}")

    res.append(f"   .align {static_var.alignment}")
    res.append(f"{static_var.name}:")
    
    match static_var.init:
        case IntInit(0):
            init_line = f"   .zero 4"
        case IntInit(i):
            init_line = f"   .long {i}"
        case LongInit(0):
            init_line = f"   .zero 8"
        case LongInit(i):
            init_line = f"   .quad {i}"
        case _:
            raise RuntimeError(f"Compiler error, cannot emit code for {static_var.init}")
    res.append(init_line)
    return res
        
def emit_instruction(ast_node):
    match ast_node:
        case AsmMov(t, src, dst):
            return f"mov{t.value}   {emit_operand(src, t.value)}, {emit_operand(dst, t.value)}"
        case AsmRet():
            return [
                f"movq   %rbp, %rsp",
                f"popq   %rbp",
                f"ret"
            ]
        case AsmMovsx(src, dst):
            return f"movslq   {emit_operand(src, 'l')}, {emit_operand(dst, 'q')}"
        case AsmUnary(unop, t, operand):
            return f"{unop.value}{t.value}   {emit_operand(operand, t.value)}"
        case AsmBinary(binop, t, src, dst):
            return f"{binop.value}{t.value}   {emit_operand(src, t.value)}, {emit_operand(dst, t.value)}"
        case AsmIdiv(t, operand):
            return f"idiv{t.value}  {emit_operand(operand, t.value)}"
        case AsmCdq(AssemblyType.Longword):
            return f"cdq"
        case AsmCdq(AssemblyType.Quadword):
            return f"cqo"
        case AsmCmp(t, op1, op2):
            return f"cmp{t.value}   {emit_operand(op1, t.value)}, {emit_operand(op2, t.value)}"
        case AsmJmp(label):
            return f"jmp    .L{label}"
        case AsmJmpCC(cc, label):
            return f"j{cc.value}    .L{label}"
        case AsmSetCC(cc, operand):
            return f"set{cc.value}  {emit_operand(operand, 'byte')}"
        case AsmLabel(label):
            return f".L{label}:"
        case AsmPush(operand):
            return f"pushq   {emit_operand(operand, 'q')}"
        case AsmCall(func):
            suffix = "@PLT" if func in backend_symbol_table else ""
            return f"call   {func}{suffix}"
        case _:
            raise NotImplementedError(f"Can't generate assembly code for {ast_node}")

def emit_operand(operand, size):
    match operand:
        case AsmReg(reg):
            if size == "byte":
                return reg.as_byte()
            if size == "l":
                return reg.as_dword()
            if size == "q":
                return reg.as_qword()
        case AsmStack(offset):
            return f"{offset}(%rbp)"
        case AsmData(name):
            return f"{name}(%rip)"
        case AsmImm(int):
            return f"${int}"
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {operand}")