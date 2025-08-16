from . import pretty_printer
from . import lexer
from . import parser
from . import emitter
from . import asm_generator
from . import asm_allocator
from . import code_emitter
from .semantic_analysis.semantic_analyser import validate_program

"""
def compile_c(file, flag):
    tokens = lexer.lex(file)
    if flag == CompilerStage.LEX:
        [print(token) for token in tokens]
        return
    print(flag)
    print(CompilerStage.PARSE)
    print(flag == CompilerStage.PARSE)
    c_ast = parser.Parser(tokens).parse_program()
    if flag == CompilerStage.PARSE:
        print("C AST:")
        pretty_printer.printer(c_ast)
        return
    
    analysed_ast = validate_program(c_ast)
    if flag == CompilerStage.VALIDATE:
        print("Validated C AST:")
        pretty_printer.printer(analysed_ast)
        return

    emitted_ir = emitter.emit_program(analysed_ast)
    if flag == CompilerStage.TACKY:
        print("Tacky AST:")
        pretty_printer.printer(emitted_ir)
        return

    asm = asm_generator.lower_program(emitted_ir)
    asm_allocator.legalize(asm)
    if flag == CompilerStage.CODEGEN:
        print("Assembly AST:")
        pretty_printer.printer(asm)
        return

    output = file[:-2] + ".s"
    with open(output, "w") as f:
        assembly_code = code_emitter.emit_program_code(asm)
        f.write(assembly_code)

    #if flag in ["all", "c"]:
    #    print("Assembly code:")
    #    print(assembly_code)
    
    return output
"""