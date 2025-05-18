from assembly_ast import *

def emit_function(name, instructions):
    res =   f"   .globl {name}\n"
    res +=  f"{name}:\n"
    res +=  f"   pushq  %rbp\n"
    res +=  f"   movq   %rsp, %rbp\n"
    for instruction in instructions:
        res += emit_code(instruction)
    return res
    
def emit_operand(operand, size = "dword"):
    match operand:
        case AsmReg(reg):
            if size == "byte":
                return reg.as_byte()
            else:
                return reg.as_dword()
        case AsmStack(offset):
            return f"{offset}(%rbp)"
        case AsmImm(int):
            return f"${int}"
        
def emit_code(ast_node):
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
        case AsmCmp(operand1, operand2):
            operand1, operand2 = emit_code(operand1), emit_code(operand2)
            return  f"   cmpl   {operand1}, {operand2}\n"
        case AsmJmp(label):
            return  f"   jmp    .L{label}\n"
        case AsmJmpCC(cc, label):
            return  f"   j{cc.value}    .L{label}\n"
        case AsmSetCC(cc, operand):
            operand = emit_operand(operand, "byte")
            return  f"   set{cc.value}    {operand}\n"
        case AsmLabel(label):
            return  f"   .L{label}:\n"
        case _:
            raise NotImplementedError(f"Cant generate assembly code for {ast_node}")
