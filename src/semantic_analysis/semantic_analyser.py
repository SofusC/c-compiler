from __future__ import annotations
from ..utils import log
from .variable_resolver import resolve_program
from .typechecker import typecheck_program
from .loop_labeller import label_program

@log("Validating program:")
def validate_program(program):
    program = resolve_program(program)
    typecheck_program(program)
    program = label_program(program)
    return program
