import sys, os, click
from . import pretty_printer, lexer, parser, emitter, asm_generator, asm_allocator, code_emitter
from .semantic_analysis.semantic_analyser import validate_program
from .compiler_stages import CompilerStage
from .gcc_runner import preprocess, assemble, assemble_object

def run_compiler(input_files, stage):
    for file in input_files:
        preprocessed = None
        try:
            preprocessed = preprocess(file)
            compiled = compile_c(preprocessed, stage)
            if stage in [CompilerStage.ALL, CompilerStage.TESTALL]:
                assemble(compiled)
            if stage == CompilerStage.C:
                assemble_object(compiled)
        except RuntimeError as err:
            click.echo(f"Error: {err}", err=True)
            sys.exit(1)
        finally:
            if preprocessed and os.path.exists(preprocessed):
                os.remove(preprocessed)

def compile_c(file, flag):
    tokens = lexer.lex(file)
    if flag == CompilerStage.LEX:
        [print(token) for token in tokens]
        return
    
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