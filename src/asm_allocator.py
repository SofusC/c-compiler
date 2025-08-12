from .assembly_ast import *
from .c_ast import Int, Long, FunType
from .semantic_analysis.typechecker import symbol_table, StaticAttr, static_type_conversion
from typing import List, Dict

TMP_REG_1 = AsmReg(AsmRegs.R10)
TMP_REG_2 = AsmReg(AsmRegs.R11)
INT_SIZE = 4
STACK_ALIGNMENT = 16
MAX_ITER = 100

class BackendSymEntry():
    pass

@dataclass
class ObjEntry(BackendSymEntry):
    type: AssemblyType
    is_static: bool

@dataclass
class FunEntry(BackendSymEntry):
    defined: bool

backend_symbol_table: dict[str, BackendSymEntry] = {}

#TODO: No need for this to be a class?
class AsmAllocator():
    def _two_stack_operands(self, instruction: AsmInstruction) -> List[AsmInstruction]:
        """
        Transforms instructions with two stack operands into legal forms.
        """
        match instruction:
            case AsmMov(t, src, dst):
                return [AsmMov(t, src, TMP_REG_1), 
                        AsmMov(t, TMP_REG_1, dst)]
            case AsmBinary(binop, t, src, dst):
                return [AsmMov(t, src, TMP_REG_1), 
                        AsmBinary(binop, t, TMP_REG_1, dst)]
            case AsmCmp(t, src, dst):
                return [AsmMov(t, src, TMP_REG_1),
                        AsmCmp(t, TMP_REG_1, dst)]
            
    def _fix_movsx(self, instruction: AsmMovsx) -> List[AsmInstruction]:
        match instruction:
            #case AsmMovsx(AsmImm() as src, dst) if self._is_memory_operand(dst):
            #    return [AsmMov(AssemblyType.Longword, src, TMP_REG_1),
            #            AsmMovsx(TMP_REG_1, TMP_REG_2),
            #            AsmMov(AssemblyType.Quadword, TMP_REG_2, dst)]
            case AsmMovsx(AsmImm() as src, dst):
                return [AsmMov(AssemblyType.Longword, src, TMP_REG_1),
                        AsmMovsx(TMP_REG_1, dst)]
            case AsmMovsx(src, dst) if self._is_memory_operand(dst):
                return [AsmMovsx(src, TMP_REG_2),
                        AsmMov(AssemblyType.Quadword, TMP_REG_2, dst)]

    def _is_memory_operand(self, operand: AsmOperand) -> bool:
        return isinstance(operand, (AsmStack, AsmData))
    
    def _in_range_of_int(self, number: int) -> bool:
        return -2**31 <= number and number <= 2**31-1
    
    #TODO: Can this and submethods be simplified given new looping check?
    def _legalize(self, instruction: AsmInstruction) -> List[AsmInstruction]:
        match instruction:
            case AsmMov(_, src, dst) | AsmCmp(_, src, dst) if self._is_memory_operand(src) and self._is_memory_operand(dst):
                # mov and cmp doesnt allow two memory operands.
                return self._two_stack_operands(instruction)
            case AsmBinary(binop, _, src, dst) if self._is_memory_operand(src) and self._is_memory_operand(dst) and binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub):
                # add and sub doesnt allow two memory operands.
                return self._two_stack_operands(instruction)
            case AsmBinary(AsmBinaryOperator.Mult, t, src, dst) if self._is_memory_operand(dst):
                # mul doesnt allow dst operand to be in memory
                return [AsmMov(t, dst, TMP_REG_2), 
                        AsmBinary(AsmBinaryOperator.Mult, t, src, TMP_REG_2),
                        AsmMov(t, TMP_REG_2, dst)]
            case AsmCmp(t, operand1, AsmImm() as operand2):
                # cmp doesnt allow second operand to be immediate value
                return [AsmMov(t, operand2, TMP_REG_2),
                        AsmCmp(t, operand1, TMP_REG_2)]
            case AsmIdiv(t, AsmImm() as operand):
                # idiv doesnt allow operand to be immediate value
                return [AsmMov(t, operand, TMP_REG_1),
                        AsmIdiv(t, TMP_REG_1)]
            #TODO: Refactor these
            case AsmMovsx(src, dst) if isinstance(src, AsmImm) or self._is_memory_operand(dst):
                return self._fix_movsx(instruction)
            case AsmBinary(binop, AssemblyType.Quadword, AsmImm() as src, dst) if not self._in_range_of_int(src.int) and binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub, AsmBinaryOperator.Mult):
                return [AsmMov(AssemblyType.Quadword, src, TMP_REG_1),
                        AsmBinary(binop, AssemblyType.Quadword, TMP_REG_1, dst)]
            case AsmCmp(AssemblyType.Quadword, AsmImm() as op1, op2) if not self._in_range_of_int(op1.int):
                return [AsmMov(AssemblyType.Quadword, op1, TMP_REG_1),
                        AsmCmp(AssemblyType.Quadword, TMP_REG_1, op2)]
            case AsmPush(AsmImm() as op) if not self._in_range_of_int(op.int):
                return [AsmMov(AssemblyType.Quadword, op, TMP_REG_1),
                        AsmPush(TMP_REG_1)]
            case AsmMov(AssemblyType.Quadword, AsmImm() as src, dst) if not self._in_range_of_int(src.int) and self._is_memory_operand(dst):
                return [AsmMov(AssemblyType.Quadword, src, TMP_REG_1),
                        AsmMov(AssemblyType.Quadword, TMP_REG_1, dst)]
            case AsmMov(AssemblyType.Longword, AsmImm(val), dst) if not self._in_range_of_int(val):
                return [AsmMov(AssemblyType.Longword, AsmImm(static_type_conversion(val, Int())), dst)]
            case _:
                return [instruction]
    
    def legalize_operands(self, fn_def: AsmFunctionDef) -> None:
        for _ in range(MAX_ITER):
            old_instructions = fn_def.instructions
            new_instructions = [
                i for instr in old_instructions for i in self._legalize(instr)
            ]
            if new_instructions == old_instructions:
                break
            fn_def.instructions = new_instructions
        else:
            raise RuntimeError("legalize_operands reached iteration limit")

    def add_stack_frame(self, fn_def: AsmFunctionDef) -> None:
        size: int = abs(self.stack_counter)
        size += STACK_ALIGNMENT - (size % STACK_ALIGNMENT)
        fn_def.instructions.insert(0, AsmBinary(AsmBinaryOperator.Sub, AssemblyType.Quadword, AsmImm(size), AsmReg(AsmRegs.SP)))

    def _allocate_stack_slot(self, identifier: str) -> AsmOperand: #TODO: Rename
        if identifier in self.identifiers:
            return AsmStack(self.identifiers[identifier])

        if identifier in backend_symbol_table:
            if backend_symbol_table[identifier].is_static:
                return AsmData(identifier)
        #TODO: Move this size lookup and refactor
        if backend_symbol_table[identifier].type == AssemblyType.Longword:
            size = 4
            self.stack_counter -= size
        elif backend_symbol_table[identifier].type == AssemblyType.Quadword:
            size = 8
            self.stack_counter -= size
            self.stack_counter -= self.stack_counter % 8
        else:
            raise RuntimeError(f"Compiler error, cant find size of type {backend_symbol_table[identifier].type}")
        self.identifiers[identifier] = self.stack_counter
        return AsmStack(self.stack_counter)

    def _remove_pseudos(self, node: AsmOperand) -> AsmOperand:
        if isinstance(node, AsmPseudo):
            return self._allocate_stack_slot(node.identifier)
        return node

    def _check_instruction(self, instr: AsmInstruction) -> AsmInstruction:
        new_attrs = {}
        for attr, value in instr.__dict__.items():
            new_attrs[attr] = self._remove_pseudos(value)
        return type(instr)(**new_attrs)
    
    def lower_pseudo_regs(self, function_definition: AsmFunctionDef) -> None:
        """
        Replaces pseudo-registers with locations on the stack.
        """        
        self.identifiers: Dict[str, int] = {}
        self.stack_counter: int = 0
        function_definition.instructions = [self._check_instruction(instr) for instr in function_definition.instructions]

    def convert_symbol_table(self):
        for identifier, sym_entry in symbol_table.items():
            if isinstance(sym_entry.type, FunType):
                backend_symbol_table[identifier] = FunEntry(True if sym_entry.attrs.defined else False)
            elif isinstance(sym_entry.type, Int) or isinstance(sym_entry.type, Long):
                assem_type = AssemblyType.Longword if isinstance(sym_entry.type, Int) else AssemblyType.Quadword
                is_static = True if isinstance(sym_entry.attrs, StaticAttr) else False
                backend_symbol_table[identifier] = ObjEntry(assem_type, is_static)
            else:
                raise RuntimeError(f"Compiler error, cannot convert {identifier}:{sym_entry} to backend symbol table")

    def legalize(self, program: AsmProgram) -> None:
        self.convert_symbol_table()
        for toplevel in program.top_levels:
            if isinstance(toplevel, AsmFunctionDef):
                self.lower_pseudo_regs(toplevel)
                self.add_stack_frame(toplevel)
                self.legalize_operands(toplevel)