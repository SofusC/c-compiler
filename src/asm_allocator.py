from assembly_ast import *

class AsmAllocator():
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
    
    def legalize_operands(self, function_definition):
        #function = program.function_definition
        #new_instructions = []
        #for instruction in function.instructions:
        #    new_instructions.extend(self._legalize(instruction))
        #function.instructions = new_instructions
        #for function_definition in program.function_definitions:
            #instructions = function_definition.instructions
            #function_definition.instructions = [self._legalize(instr) for instr in function_definition.instructions]
            #new_instructions = []
            #for instruction in function_definition.instructions:
            #    new_instructions.extend(self._legalize(instruction))
            #function_definition.instructions = new_instructions
        new_instructions = []
        for instr in function_definition.instructions:
            new_instructions.extend(self._legalize(instr))
        function_definition.instructions = new_instructions

    def add_stack_frame(self, function_definition):
        #for function_definition in program.function_definitions:
        size = abs(self.stack_counter)
        size += 16 - (size % 16)
        function_definition.instructions[:0] = [AsmAllocateStack(size)]

    def _allocate_stack_slot(self, identifier):
        if identifier not in self.identifiers:
            self.stack_counter -= 4
            self.identifiers[identifier] = self.stack_counter
        return self.identifiers[identifier]

    def lower_pseudo_regs(self, function_definition): # TODO: this function needs refactoring
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
                case AsmPush(operand):
                    return AsmPush(remove_pseudos(operand))
                case _:
                    return instruction
        
        self.identifiers = {}
        self.stack_counter = 0
        #new_function_definitions = []
        #for function_definition in program.function_definitions:
            #instructions = function_definition.instructions
        function_definition.instructions = [check_instruction(instr) for instr in function_definition.instructions]
            #new_function_definitions.append(lowered_instrs)
            #raise Error("This is wrong, edit in place instead")
        #program.function_definitions = new_function_definitions
    
    def legalize(self, program):
        for function_definition in program.function_definitions:
            self.lower_pseudo_regs(function_definition)
            self.add_stack_frame(function_definition)
            self.legalize_operands(function_definition)
        #TODO: Modfiy or return new?