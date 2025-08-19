from .assembly_ast import *
from .c_ast import Int, Long, FunType
from .semantic_analysis.symbol_table import SymbolEntry, StaticAttr, symbol_table
from .semantic_analysis.typechecker import static_type_conversion
from typing import List, Dict

TMP_REG_1 = AsmReg(AsmRegs.R10)
TMP_REG_2 = AsmReg(AsmRegs.R11)
LONGWORD_SIZE = 4
QUADWORD_SIZE = 8
STACK_ALIGNMENT = 16
MAX_ITER = 100

identifiers: Dict[str, int] = {}
stack_counter: int = 0

class BackendSymEntry:
    pass

@dataclass
class ObjEntry(BackendSymEntry):
    type: AssemblyType
    is_static: bool

@dataclass
class FunEntry(BackendSymEntry):
    defined: bool

backend_symbol_table: dict[str, BackendSymEntry] = {}


def _two_stack_operands(instruction: AsmInstruction) -> List[AsmInstruction]:
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
        
def _dst_in_memory(instruction: AsmInstruction) -> List[AsmInstruction]:
    match instruction:
        case AsmBinary(_, t, src, dst):
            return [AsmMov(t, dst, TMP_REG_2), 
                    AsmBinary(AsmBinaryOperator.Mult, t, src, TMP_REG_2),
                    AsmMov(t, TMP_REG_2, dst)]
        case AsmMovsx(src, dst):
            return [AsmMovsx(src, TMP_REG_2),
                    AsmMov(AssemblyType.Quadword, TMP_REG_2, dst)]
        
def _immediate_operand(instruction: AsmInstruction) -> List[AsmInstruction]:
    match instruction:
        case AsmCmp(t, operand1, operand2):
            return [AsmMov(t, operand2, TMP_REG_2),
                    AsmCmp(t, operand1, TMP_REG_2)]
        case AsmIdiv(t, operand):
            return [AsmMov(t, operand, TMP_REG_1),
                    AsmIdiv(t, TMP_REG_1)]
        case AsmMovsx(src, dst):
            return [AsmMov(AssemblyType.Longword, src, TMP_REG_1),
                    AsmMovsx(TMP_REG_1, dst)]
        
def _large_immediate_value(instruction: AsmInstruction) -> List[AsmInstruction]:
    match instruction:
        case AsmBinary(binop, _, src, dst):
            return [AsmMov(AssemblyType.Quadword, src, TMP_REG_1),
                    AsmBinary(binop, AssemblyType.Quadword, TMP_REG_1, dst)]
        case AsmCmp(_, op1, op2):
            return [AsmMov(AssemblyType.Quadword, op1, TMP_REG_1),
                    AsmCmp(AssemblyType.Quadword, TMP_REG_1, op2)]
        case AsmPush(op):
            return [AsmMov(AssemblyType.Quadword, op, TMP_REG_1),
                    AsmPush(TMP_REG_1)]
        case AsmMov(_, src, dst):
            return [AsmMov(AssemblyType.Quadword, src, TMP_REG_1),
                    AsmMov(AssemblyType.Quadword, TMP_REG_1, dst)]
        
def _quadword_in_movl(instruction: AsmMov) -> List[AsmInstruction]:
    val, dst = instruction.src.int, instruction.dst
    return [AsmMov(AssemblyType.Longword, AsmImm(static_type_conversion(val, Int)), dst)]


def _is_memory_operand(operand: AsmOperand) -> bool:
    return isinstance(operand, (AsmStack, AsmData))

def _in_range_of_int(number: int) -> bool:
    return Int.MIN_VALUE <= number and number <= Int.MAX_VALUE

def _two_mem_ops(src: AsmOperand, dst: AsmOperand) -> bool:
        return _is_memory_operand(src) and _is_memory_operand(dst)

def _legalize(instruction: AsmInstruction) -> List[AsmInstruction]:
    match instruction:
        # No two memory operands
        case AsmMov(_, src, dst) | AsmCmp(_, src, dst) if _two_mem_ops(src, dst):
            return _two_stack_operands(instruction)
        case AsmBinary(binop, _, src, dst) if _two_mem_ops(src, dst) and binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub):
            return _two_stack_operands(instruction)
        
        # Destination cannot be in memory
        case AsmBinary(AsmBinaryOperator.Mult, _, _, dst) if _is_memory_operand(dst):
            return _dst_in_memory(instruction)
        case AsmMovsx(_, dst) if _is_memory_operand(dst):
            return _dst_in_memory(instruction)

        # First or second operand cannot be immediate
        case AsmCmp(_, _, AsmImm()):
            return _immediate_operand(instruction)
        case AsmIdiv(_, AsmImm()):
            return _immediate_operand(instruction)
        case AsmMovsx(AsmImm(), _):
            return _immediate_operand(instruction)
        
        # Large immediate restrictions
        case AsmBinary(binop, AssemblyType.Quadword, AsmImm(val), _) if not _in_range_of_int(val) and binop in (AsmBinaryOperator.Add, AsmBinaryOperator.Sub, AsmBinaryOperator.Mult):
            return _large_immediate_value(instruction)
        case AsmCmp(AssemblyType.Quadword, AsmImm(val), _) if not _in_range_of_int(val):
            return _large_immediate_value(instruction)
        case AsmPush(AsmImm(val)) if not _in_range_of_int(val):
            return _large_immediate_value(instruction)
        case AsmMov(AssemblyType.Quadword, AsmImm(val), dst) if not _in_range_of_int(val) and _is_memory_operand(dst):
            return _large_immediate_value(instruction)
        
        # movl with large immediate needs truncation
        case AsmMov(AssemblyType.Longword, AsmImm(val), _) if not _in_range_of_int(val):
            return _quadword_in_movl(instruction)
        
        case _:
            return [instruction]

def legalize_operands(fn_def: AsmFunctionDef) -> None:
    for _ in range(MAX_ITER):
        old_instructions = fn_def.instructions
        new_instructions = [
            i for instr in old_instructions for i in _legalize(instr)
        ]
        if new_instructions == old_instructions:
            break
        fn_def.instructions = new_instructions
    else:
        raise RuntimeError("Compiler error, legalize_operands reached iteration limit")

def add_stack_frame(fn_def: AsmFunctionDef) -> None:
    stack_frame_size = abs(stack_counter)
    stack_frame_size += STACK_ALIGNMENT - (stack_frame_size % STACK_ALIGNMENT)
    fn_def.instructions.insert(0, AsmBinary(AsmBinaryOperator.Sub, AssemblyType.Quadword, AsmImm(stack_frame_size), AsmReg(AsmRegs.SP)))

def _get_stack_slot(identifier: str) -> AsmOperand:
    global identifiers, stack_counter
    if identifier in identifiers:
        return AsmStack(identifiers[identifier])

    sym_entry = backend_symbol_table[identifier]
    if sym_entry is not None and sym_entry.is_static:
            return AsmData(identifier)
        
    if sym_entry.type == AssemblyType.Longword:
        size = LONGWORD_SIZE
    elif sym_entry.type == AssemblyType.Quadword:
        size = QUADWORD_SIZE
    else:
        raise RuntimeError(f"Compiler error, cant find size of type {sym_entry.type}")
    
    stack_counter -= size
    if sym_entry.type == AssemblyType.Quadword: # align quadword
        stack_counter -= stack_counter % 8

    identifiers[identifier] = stack_counter
    return AsmStack(stack_counter)

def _remove_pseudos(node):
    if isinstance(node, AsmPseudo):
        return _get_stack_slot(node.identifier)
    return node

def _check_instruction(instr: AsmInstruction) -> AsmInstruction:
    new_attrs = {}
    for attr, value in instr.__dict__.items():
        new_attrs[attr] = _remove_pseudos(value)
    return type(instr)(**new_attrs)

def lower_pseudo_regs(function_definition: AsmFunctionDef) -> None:
    """
    Replaces pseudo-registers with locations on the stack.
    """
    global identifiers, stack_counter
    identifiers.clear()
    stack_counter = 0
    function_definition.instructions = [_check_instruction(instr) for instr in function_definition.instructions]

def _to_backend_entry(sym_entry: SymbolEntry):
    sym_type = sym_entry.type

    if isinstance(sym_type, FunType):
        return FunEntry(sym_entry.attrs.defined)
    elif sym_type is Int or sym_type is Long:
        assem_type = AssemblyType.Longword if sym_type is Int else AssemblyType.Quadword
        is_static = isinstance(sym_entry.attrs, StaticAttr)
        return ObjEntry(assem_type, is_static)
    else:
        raise RuntimeError(f"Cannot convert {sym_entry} to backend symbol table")

def convert_symbol_table():
    backend_symbol_table.update({
        identifier: _to_backend_entry(sym_entry)
        for identifier, sym_entry in symbol_table.items()
    })

def legalize(program: AsmProgram) -> None:
    convert_symbol_table()
    for toplevel in program.top_levels:
        if isinstance(toplevel, AsmFunctionDef):
            lower_pseudo_regs(toplevel)
            add_stack_frame(toplevel)
            legalize_operands(toplevel)