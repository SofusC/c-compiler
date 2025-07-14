from .assembly_ast import *
from .semantic_analysis.typechecker import symbol_table
from typing import List, Dict, Any

TMP_REG_1 = AsmReg(AsmRegs.R10)
TMP_REG_2 = AsmReg(AsmRegs.R11)
INT_SIZE = 4
STACK_ALIGNMENT = 16

#TODO: No need for this to be a class?
class AsmAllocator():
    def _two_stack_operands(self, instruction: AsmInstruction) -> List[AsmInstruction]:
        """
        Transforms instructions with two stack operands into legal forms.
        """
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

    def _is_memory_operand(self, operand: AsmOperand) -> bool:
        return isinstance(operand, (AsmStack, AsmData))
    
    def _legalize(self, instruction: AsmInstruction) -> List[AsmInstruction]:
        match instruction:
            case AsmMov(src, dst) | AsmCmp(src, dst) if self._is_memory_operand(src) and self._is_memory_operand(dst):
                # mov and cmp doesnt allow two memory operands.
                return self._two_stack_operands(instruction)
            case AsmBinary(binop, src, dst) if self._is_memory_operand(src) and self._is_memory_operand(dst) and binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub):
                # add and sub doesnt allow two memory operands.
                return self._two_stack_operands(instruction)
            case AsmBinary(AsmBinaryOperator.Mult, src, dst) if self._is_memory_operand(dst):
                # mul doesnt allow dst operand to be in memory
                return [AsmMov(dst, TMP_REG_2), 
                        AsmBinary(AsmBinaryOperator.Mult, src, TMP_REG_2),
                        AsmMov(TMP_REG_2, dst)]
            case AsmCmp(operand1, AsmImm() as operand2):
                # cmp doesnt allow second operand to be immediate value
                return [AsmMov(operand2, TMP_REG_2),
                        AsmCmp(operand1, TMP_REG_2)]
            case AsmIdiv(AsmImm() as operand):
                # idiv doesnt allow operand to be immediate value
                return [AsmMov(operand, TMP_REG_1),
                        AsmIdiv(TMP_REG_1)]
            case _:
                return [instruction]
    
    def legalize_operands(self, fn_def: AsmFunctionDef) -> None:
        fn_def.instructions = [i for instr in fn_def.instructions for i in self._legalize(instr)]

    def add_stack_frame(self, fn_def: AsmFunctionDef) -> None:
        size: int = abs(self.stack_counter)
        size += STACK_ALIGNMENT - (size % STACK_ALIGNMENT)
        fn_def.instructions.insert(0, AsmAllocateStack(size))

    def _allocate_stack_slot(self, identifier: str) -> AsmOperand:
        #TODO: Refactor
        if identifier not in self.identifiers:
            if identifier in symbol_table:
                if getattr(symbol_table[identifier].attrs, "global_", False):
                    return AsmData(identifier)
            self.stack_counter -= INT_SIZE
            self.identifiers[identifier] = self.stack_counter
        return AsmStack(self.identifiers[identifier])

    def lower_pseudo_regs(self, function_definition: AsmFunctionDef) -> None:
        """
        Replaces pseudo-registers with locations on the stack.
        """
        def remove_pseudos(node: AsmOperand) -> AsmOperand: #TODO: Move these out of method
            if isinstance(node, AsmPseudo):
                return self._allocate_stack_slot(node.identifier)
            return node
        
        def check_instruction(instr: AsmInstruction) -> AsmInstruction:
            new_attrs = {}
            for attr, value in instr.__dict__.items():
                new_attrs[attr] = remove_pseudos(value)
            return type(instr)(**new_attrs)
        
        self.identifiers: Dict[str, int] = {}
        self.stack_counter: int = 0
        function_definition.instructions = [check_instruction(instr) for instr in function_definition.instructions]
    
    def legalize(self, program: AsmProgram) -> None:
        for toplevel in program.top_levels:
            if isinstance(toplevel, AsmFunctionDef):
                self.lower_pseudo_regs(toplevel)
                self.add_stack_frame(toplevel)
                self.legalize_operands(toplevel)