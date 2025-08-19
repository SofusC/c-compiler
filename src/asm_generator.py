from .ir_ast import *
from .assembly_ast import *
from .c_ast import ConstInt, ConstLong, Int, Long
from .semantic_analysis.symbol_table import symbol_table

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

SIZE_OF_RIP = 8
SIZE_OF_RBP = 8
SIZE_OF_PROLOGUE = SIZE_OF_RIP + SIZE_OF_RBP
SIZE_OF_STACK_ARG = 8

def lower_program(program: IRProgram) -> AsmProgram:
    toplevels = [lower_toplevel(toplevel) for toplevel in program.toplevels]
    return AsmProgram(toplevels)

def lower_toplevel(toplevel: IRTopLevel):
    match toplevel:
        case IRFunctionDefinition():
            return lower_function_definition(toplevel)
        case IRStaticVariable(name, global_, type, init):
            return AsmStaticVar(name, global_, get_type_alignment(type), init)
        case _:
            raise NotImplementedError(f"Top-level object {toplevel} cannot be transformed to assembly AST yet.")

def lower_function_definition(func_def: IRFunctionDefinition) -> AsmFunctionDef:
    param_regs = AsmRegs.system_v_argument_regs()
    asm_instructions = []
    for reg, param in zip(param_regs, func_def.params):
        param_type = lower_operand_type(IRVar(param))
        asm_instructions.append(
            AsmMov(
                param_type, 
                AsmReg(reg), 
                AsmPseudo(param)
            )
        )

    stack_params = func_def.params[len(param_regs):]
    for i, param in enumerate(stack_params):
        param_type = lower_operand_type(IRVar(param))
        asm_instructions.append(
            AsmMov(
                param_type, 
                AsmStack(SIZE_OF_PROLOGUE + i*SIZE_OF_STACK_ARG), 
                AsmPseudo(param)
            )
        )
        
    for instruction in func_def.body:
        asm_instructions += lower_instr(instruction)
    return AsmFunctionDef(func_def.name, func_def.global_, asm_instructions)

def lower_instr(instruction: IRInstruction) -> List[AsmInstruction]:
    match instruction:
        case IRReturn(val):
            return lower_return(val)
        case IRUnary(unop, src, dst):
            return lower_unary(unop, src, dst)
        case IRBinary(binop, src1, src2, dst):
            return lower_binary(binop, src1, src2, dst)
        case IRJump(target):
            return [AsmJmp(target)]
        case IRJumpIfZero(condition, target):
            return [AsmCmp(lower_operand_type(condition), AsmImm(0), lower_operand(condition)),
                    AsmJmpCC(AsmCondCode.E, target)]
        case IRJumpIfNotZero(condition, target):
            return [AsmCmp(lower_operand_type(condition), AsmImm(0), lower_operand(condition)),
                    AsmJmpCC(AsmCondCode.NE, target)]
        case IRCopy(src, dst):
            return [AsmMov(lower_operand_type(src), lower_operand(src), lower_operand(dst))]
        case IRLabel(identifier):
            return [AsmLabel(identifier)]
        case IRFunCall(fun_name, args, dst):
            return lower_fun_call(fun_name, args, dst)
        case IRSignExtend(src, dst):
            return [AsmMovsx(lower_operand(src), lower_operand(dst))]
        case IRTruncate(src, dst):
            return [AsmMov(
                        AssemblyType.Longword, 
                        lower_operand(src), 
                        lower_operand(dst)
                    )]
        case _:
            raise NotImplementedError(f"IR instruction {instruction} can not be transformed to assembly AST yet.")
    
def lower_return(ir_val: IRVal) -> List[AsmInstruction]:
    val = lower_operand(ir_val)
    return [AsmMov(
                lower_operand_type(ir_val), 
                val, 
                AsmReg(AsmRegs.AX)
            ), 
            AsmRet()]
        
def lower_fun_call(fun_name: str, args: List[IRVal], dst: IRVal) -> List[AsmInstruction]:
    arg_registers = AsmRegs.system_v_argument_regs()
    instructions = []
    register_args, stack_args = args[:6], args[6:]

    stack_padding = compute_stack_padding(stack_args)
    if stack_padding:
        instructions.append(AsmBinary(AsmBinaryOperator.Sub, AssemblyType.Quadword, AsmImm(stack_padding), AsmReg(AsmRegs.SP)))

    for tacky_arg, reg in zip(register_args, arg_registers):
        assembly_arg, arg_type = lower_arg(tacky_arg)
        instructions.append(AsmMov(arg_type, assembly_arg, AsmReg(reg)))

    for tacky_arg in stack_args[::-1]:
        operand, op_type = lower_arg(tacky_arg)
        if can_push_directly(operand, op_type):
            instructions.append(AsmPush(operand))
        else:
            instructions.extend([AsmMov(AssemblyType.Longword, operand, AsmReg(AsmRegs.AX)),
                                 AsmPush(AsmReg(AsmRegs.AX))])
    instructions.append(AsmCall(fun_name))

    bytes_to_remove = SIZE_OF_STACK_ARG * len(stack_args) + stack_padding
    if bytes_to_remove:
        instructions.append(AsmBinary(AsmBinaryOperator.Add, AssemblyType.Quadword, AsmImm(bytes_to_remove), AsmReg(AsmRegs.SP)))

    dst_operand, dst_type = lower_arg(dst)
    instructions.append(AsmMov(dst_type, AsmReg(AsmRegs.AX), dst_operand))
    return instructions

def compute_stack_padding(stack_args) -> int:
    return SIZE_OF_STACK_ARG if len(stack_args) % 2 == 1 else 0

def lower_arg(arg: IRVal) -> tuple[AsmOperand, AssemblyType]:
    return lower_operand(arg), lower_operand_type(arg)

def can_push_directly(op: AsmOperand, op_type: AssemblyType) -> bool:
    return isinstance(op, (AsmImm, AsmReg)) or op_type == AssemblyType.Quadword

def lower_unary(unop, ir_src, ir_dst):
    src, src_type, dst = lower_operand(ir_src), lower_operand_type(ir_src), lower_operand(ir_dst)
    match unop:
        case IRUnaryOperator.Not:
            return [AsmCmp(src_type, AsmImm(0), src),
                    AsmMov(lower_operand_type(ir_dst), AsmImm(0), dst),
                    AsmSetCC(AsmCondCode.E, dst)]
        case _:
            return [AsmMov(src_type, src, dst), 
                    AsmUnary(lower_operator(unop), src_type, dst)]

        
def lower_binary(binop, ir_src1, ir_src2, ir_dst):
    src1, src2, dst = lower_operand(ir_src1), lower_operand(ir_src2), lower_operand(ir_dst)
    src1_type = lower_operand_type(ir_src1)
    match binop:
        case IRBinaryOperator.Divide:
            dividend_reg = AsmReg(AsmRegs.AX)
            return [AsmMov(src1_type, src1, dividend_reg),
                    AsmCdq(src1_type),
                    AsmIdiv(src1_type, src2),
                    AsmMov(src1_type, dividend_reg, dst)]
        case IRBinaryOperator.Remainder:
            return [AsmMov(src1_type, src1, AsmReg(AsmRegs.AX)),
                    AsmCdq(src1_type),
                    AsmIdiv(src1_type, src2),
                    AsmMov(src1_type, AsmReg(AsmRegs.DX), dst)]
        case relational if binop.is_relational:
            relational = lower_relational(relational)
            return [AsmCmp(src1_type, src2, src1),
                    AsmMov(lower_operand_type(ir_dst), AsmImm(0), dst),
                    AsmSetCC(relational, dst)]
        case arithmetic if binop.is_arithmetic:
            binop = lower_operator(arithmetic)
            return [AsmMov(src1_type, src1, dst),
                    AsmBinary(binop, src1_type, src2, dst)]
        case _:
            raise RuntimeError(f"Compiler error, cannot lower binary {binop}")

def lower_operand_type(operand: IRVal):
    match operand:
        case IRConstant(ConstInt()):
            return AssemblyType.Longword
        case IRConstant(ConstLong()):
            return AssemblyType.Quadword
        case IRVar(identifier) if symbol_table[identifier].type is Int:
            return AssemblyType.Longword
        case IRVar(identifier) if symbol_table[identifier].type is Long:
            return AssemblyType.Quadword
        case _:
            raise RuntimeError(f"Compiler error, cannot determine type of {operand}")

def get_type_alignment(type: Type):
    match type:
        case _ if type is Int:
            return 4
        case _ if type is Long:
            return 8
        case _:
            raise RuntimeError(f"Compiler error, cannot determine alignment of type {type}")

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

def lower_operand(ast_node: IRVal):
    match ast_node:
        case IRConstant(constant):
            return AsmImm(constant.int)
        case IRVar(identifier):
            return AsmPseudo(identifier)
        case _:
            raise NotImplementedError(f"IR operand object {ast_node} can not be transformed to assembly AST yet.")
