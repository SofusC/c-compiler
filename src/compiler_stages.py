from enum import Enum, auto

class CompilerStage(Enum):
    LEX         = auto()
    PARSE       = auto()
    VALIDATE    = auto()
    TACKY       = auto()
    CODEGEN     = auto()
    ALL         = auto()
    TESTALL     = auto()
    C           = auto()
