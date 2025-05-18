from assembly_ast import *

class AsmAllocator():
    def __init__(self):
        self.identifiers = {}
        self.stack_counter = 0

    def _two_stack_operands(self, instruction):
        tmp = AsmReg(AsmRegs.R10)
        match instruction:
            case AsmMov(src, dst):
                return [AsmMov(src, tmp), 
                        AsmMov(tmp, dst)]
            case AsmBinary(binop, src, dst):
                return [AsmMov(src, tmp), 
                        AsmBinary(binop, tmp, dst)]
            case AsmCmp(src, dst):
                return [AsmMov(src, tmp),
                        AsmCmp(tmp, dst)]

    def _legalize(self, instruction):
        match instruction:
            case AsmMov(AsmStack(), AsmStack()) | AsmCmp(AsmStack(), AsmStack()):
                return self._two_stack_operands(instruction)
            case AsmBinary(binop, AsmStack(), AsmStack()) if binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub):
                return self._two_stack_operands(instruction)
            case AsmBinary(AsmBinaryOperator.Mult, src, AsmStack() as dst):
                tmp = AsmReg(AsmRegs.R11)
                return [AsmMov(dst, tmp), 
                        AsmBinary(AsmBinaryOperator.Mult, src, tmp),
                        AsmMov(tmp, dst)]
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
    
    def legalize_operands(self, program):
        function = program.function_definition
        new_instructions = []
        for instruction in function.instructions:
            new_instructions.extend(self._legalize(instruction))
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
            