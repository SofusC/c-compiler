from __future__ import annotations
from dataclasses import dataclass
from ..c_ast import Type

symbol_table: dict[str, SymbolEntry] = {}


@dataclass
class SymbolEntry:
    type: Type
    defined: bool | None = None
    attrs: IdentifierAttr | None = None


class IdentifierAttr:
    pass
@dataclass
class FunAttr(IdentifierAttr):
    defined: bool
    global_: bool
@dataclass
class StaticAttr(IdentifierAttr):
    init: InitialValue
    global_: bool
class LocalAttr(IdentifierAttr):
    pass


class InitialValue:
    pass
class Tentative(InitialValue):
    pass
@dataclass
class Initial(InitialValue):
    init: StaticInit
class NoInitializer(InitialValue):
    pass


class StaticInit:
    pass
@dataclass
class IntInit(StaticInit):
    int: int
@dataclass
class LongInit(StaticInit):
    int: int
@dataclass
class UIntInit(StaticInit):
    int: int
@dataclass
class ULongInit(StaticInit):
    int: int