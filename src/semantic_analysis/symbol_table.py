from __future__ import annotations
from dataclasses import dataclass
from ..c_ast import Type

symbol_table: dict[str, SymbolEntry] = {}

@dataclass
class IntInit:
    int: int
@dataclass
class LongInit:
    int: int

StaticInit = IntInit | LongInit

class Tentative:
    pass
@dataclass
class Initial:
    init: StaticInit
class NoInitializer:
    pass

InitialValue = Tentative | Initial | NoInitializer

@dataclass
class FunAttr:
    defined: bool
    global_: bool
@dataclass
class StaticAttr:
    init: InitialValue
    global_: bool
class LocalAttr:
    pass

IdentifierAttr = FunAttr | StaticAttr | LocalAttr

@dataclass
class SymbolEntry:
    type: Type
    defined: bool | None = None
    attrs: IdentifierAttr | None = None
