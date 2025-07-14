from .ir_ast import *
from .assembly_ast import *

_RELATIONAL_MAP = {
    IRBinaryOperator.Equal          : AsmCondCode.E,
    IRBinaryOperator.NotEqual       : AsmCondCode.NE,
    IRBinaryOperator.LessThan       : AsmCondCode.L,
    IRBinaryOperator.LessOrEqual    : AsmCondCode.LE,
    IRBinaryOperator.GreaterThan    : AsmCondCode.G,
    IRBinaryOperator.GreaterOrEqual : AsmCondCode.GE,
}

_OPERATOR_MAP = {
    IRUnaryOperator.Complement      : AsmUnaryOperator.Not,
    IRUnaryOperator.Negate          : AsmUnaryOperator.Neg,
    IRBinaryOperator.Add            : AsmBinaryOperator.Add,
    IRBinaryOperator.Subtract       : AsmBinaryOperator.Sub,
    IRBinaryOperator.Multiply       : AsmBinaryOperator.Mult,
}
        
def lower_program(program: IRProgram):
    toplevels = [lower_toplevel(toplevel) for toplevel in program.toplevels]
    return AsmProgram(toplevels)

def lower_toplevel(toplevel: IRTopLevel):
    match toplevel:
        case IRFunctionDefinition():
            return lower_function_definition(toplevel)
        case IRStaticVariable(name, global_, init):
            return AsmStaticVar(name, global_, init)
        case _:
            raise NotImplementedError(f"Top-level object {toplevel} cannot be transformed to assembly AST yet.")

def lower_function_definition(func_def: IRFunctionDefinition):
    param_regs = AsmRegs.system_v_argument_regs()
    asm_instructions = []
    for reg, param in zip(param_regs, func_def.params):
        asm_instructions.append(AsmMov(AsmReg(reg), lower_operand(IRVar(param))))
    for i, param in enumerate(func_def.params[len(param_regs):]):
        asm_instructions.append(AsmMov(AsmStack(16 + i*8), lower_operand(IRVar(param))))
        
    for instruction in func_def.body:
        asm_instructions += lower_instr(instruction)
    return AsmFunctionDef(func_def.name, func_def.global_, asm_instructions)

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
        case IRFunCall(fun_name, args, dst):
            return lower_fun_call(fun_name, args, dst)
        case _:
            raise NotImplementedError(f"IR object {ast_node} can not be transformed to assembly AST yet.")
        
def lower_fun_call(fun_name, args: List[IRVal], dst):
    arg_registers = AsmRegs.system_v_argument_regs()
    instructions = []
    register_args, stack_args = args[:6], args[6:]
    stack_padding = 0
    if len(stack_args) % 2 == 1:
        stack_padding = 8

    if stack_padding != 0:
        instructions.append(AsmAllocateStack(stack_padding))

    reg_index = 0
    for tacky_arg in register_args:
        r = arg_registers[reg_index]
        assembly_arg = lower_operand(tacky_arg)
        instructions.append(AsmMov(assembly_arg, AsmReg(r)))
        reg_index += 1

    for tacky_arg in stack_args[::-1]:
        assembly_arg = lower_operand(tacky_arg)
        if isinstance(assembly_arg, AsmImm) or isinstance(assembly_arg, AsmReg): #Always true?
            instructions.append(AsmPush(assembly_arg))
        else:
            instructions.extend([AsmMov(assembly_arg, AsmReg(AsmRegs.AX)),
                                 AsmPush(AsmReg(AsmRegs.AX))])
    instructions.append(AsmCall(fun_name))

    bytes_to_remove = 8 * len(stack_args) + stack_padding
    if bytes_to_remove != 0:
        instructions.append(AsmDeallocateStack(bytes_to_remove))

    assembly_dst = lower_operand(dst)
    instructions.append(AsmMov(AsmReg(AsmRegs.AX), assembly_dst))
    return instructions

def lower_unary(unop, src, dst):
    src, dst = lower_operand(src), lower_operand(dst)
    match unop:
        case IRUnaryOperator.Not:
            return [AsmCmp(AsmImm(0), src),
                    AsmMov(AsmImm(0), dst),
                    AsmSetCC(AsmCondCode.E, dst)]
        case _:
            return [AsmMov(src, dst), 
                    AsmUnary(lower_operator(unop), dst)]

        
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
    try:
        return _RELATIONAL_MAP[ast_node]
    except KeyError:
        raise NotImplementedError(f"IR relational object {ast_node} cannot be transformed to assembly AST yet.")

def lower_operator(ast_node):
    try:
        return _OPERATOR_MAP[ast_node]
    except KeyError:
        raise NotImplementedError(f"IR operator object {ast_node} cannot be transformed to assembly AST yet.")

def lower_operand(ast_node):
    match ast_node:
        case IRConstant(constant):
            return AsmImm(constant)
        case IRVar(identifier):
            return AsmPseudo(identifier)
        case _:
            raise NotImplementedError(f"IR operand object {ast_node} can not be transformed to assembly AST yet.")
