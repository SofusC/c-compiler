from ir_ast import *
from assembly_ast import *

def lower_to_asm(ast_node):
    match ast_node: # TODO: This is a bit weird to do as patternmatch.
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
