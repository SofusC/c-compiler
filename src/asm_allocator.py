from assembly_ast import *

TMP_REG_1 = AsmReg(AsmRegs.R10)
TMP_REG_2 = AsmReg(AsmRegs.R11)
INT_SIZE = 4
STACK_ALIGNMENT = 16

class AsmAllocator():
    def _two_stack_operands(self, instruction):
        match instruction:
            case AsmMov(src, dst):
                return [AsmMov(src, TMP_REG_1), 
                        AsmMov(TMP_REG_1, dst)]
            case AsmBinary(binop, src, dst):
                return [AsmMov(src, TMP_REG_1), 
                        AsmBinary(binop, TMP_REG_1, dst)]
            case AsmCmp(src, dst):
                return [AsmMov(src, TMP_REG_1),
                        AsmCmp(TMP_REG_1, dst)]

    def _legalize(self, instruction):
        match instruction:
            case AsmMov(AsmStack(), AsmStack()) | AsmCmp(AsmStack(), AsmStack()):
                return self._two_stack_operands(instruction)
            case AsmBinary(binop, AsmStack(), AsmStack()) if binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub):
                return self._two_stack_operands(instruction)
            case AsmBinary(AsmBinaryOperator.Mult, src, AsmStack() as dst):
                return [AsmMov(dst, TMP_REG_2), 
                        AsmBinary(AsmBinaryOperator.Mult, src, TMP_REG_2),
                        AsmMov(TMP_REG_2, dst)]
            case AsmCmp(operand1, AsmImm() as operand2):
                return [AsmMov(operand2, TMP_REG_2),
                        AsmCmp(operand1, TMP_REG_2)]
            case AsmIdiv(AsmImm() as operand):
                return [AsmMov(operand, TMP_REG_1),
                        AsmIdiv(TMP_REG_1)]
            case _:
                return [instruction]
    
    def legalize_operands(self, fn_def):
        fn_def.instructions = [i for instr in fn_def.instructions for i in self._legalize(instr)]

    def add_stack_frame(self, fn_def):
        size = abs(self.stack_counter)
        size += STACK_ALIGNMENT - (size % STACK_ALIGNMENT)
        fn_def.instructions.insert(0, AsmAllocateStack(size))

    def _allocate_stack_slot(self, identifier):
        if identifier not in self.identifiers:
            self.stack_counter -= INT_SIZE
            self.identifiers[identifier] = self.stack_counter
        return self.identifiers[identifier]

    def lower_pseudo_regs(self, function_definition):
        def remove_pseudos(node):
            if isinstance(node, AsmPseudo):
                return AsmStack(self._allocate_stack_slot(node.identifier))
            return node
                
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
                case AsmPush(operand):
                    return AsmPush(remove_pseudos(operand))
                case _:
                    return instruction
        
        self.identifiers = {}
        self.stack_counter = 0
        function_definition.instructions = [check_instruction(instr) for instr in function_definition.instructions]
    
    def legalize(self, program):
        for function_definition in program.function_definitions:
            self.lower_pseudo_regs(function_definition)
            self.add_stack_frame(function_definition)
            self.legalize_operands(function_definition)