from . import pretty_printer
from . import lexer
from . import parser
from . import emitter
from . import asm_generator
from . import asm_allocator
from . import code_emitter
from .semantic_analysis.semantic_analyser import validate_program

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "validate", "tacky", "codegen", "all", "testall", "c"]:
        ast = parser.Parser(tokens).parse_program()

    if flag in ["validate", "tacky", "codegen", "all", "testall", "c"]:
        analysed_ast = validate_program(ast)

    if flag in ["tacky", "codegen", "all", "testall", "c"]:
        emitted_ir = emitter.emit_program(analysed_ast)

    if flag in ["codegen", "all", "testall", "c"]:
        asm = asm_generator.lower_program(emitted_ir)
        asm_allocator.legalize(asm)

    if flag in ["all", "testall", "c"]:
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            assembly_code = code_emitter.emit_program_code(asm)
            f.write(assembly_code)

    #TODO: This is not printed when an error is raised
    if flag == "lex":
        [print(token) for token in tokens]
    elif flag == "parse":
        print("C AST:")
        pretty_printer.printer(ast)
    elif flag == "validate":
        print("Validated C AST:")
        pretty_printer.printer(analysed_ast)
    elif flag == "tacky":
        print("Tacky AST:")
        pretty_printer.printer(emitted_ir)
    elif flag == "codegen":
        print("Assembly AST:")
        pretty_printer.printer(asm)
    elif flag == "testall":
        print("C AST:")
        pretty_printer.printer(ast)
        print("Validated C AST:")
        pretty_printer.printer(analysed_ast)
        print("Tacky AST:")
        pretty_printer.printer(emitted_ir)
        print("Assembly AST:")
        pretty_printer.printer(asm)
        print("Assembly code:")
        print(assembly_code)

    return output