from .gcc_runner import *
import sys
from . import compiler
import click
import os
from enum import Enum
from . import pretty_printer
from . import lexer
from . import parser
from . import emitter
from . import asm_generator
from . import asm_allocator
from . import code_emitter
from .semantic_analysis.semantic_analyser import validate_program


class CompilerStage(Enum):
    LEX         = "lex"
    PARSE       = "parse"
    VALIDATE    = "validate"
    TACKY       = "tacky"
    CODEGEN     = "codegen"
    ALL         = "all"
    TESTALL     = "testall"
    C           = "c"

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

def run_compiler(input_files, stage):
    """Run the compiler workflow for the given files and stage."""
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

@click.command()
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
@click.option("--lex", is_flag=True, help="Run lexer only.")
@click.option("--parse", "parse_stage", is_flag=True, help="Parse C into AST.")
@click.option("--validate", is_flag=True, help="Validate C AST.")
@click.option("--tacky", is_flag=True, help="Generate Tacky IR.")
@click.option("--codegen", is_flag=True, help="Generate assembly code.")
@click.option("--all", "all_stage", is_flag=True, help="Run all stages.")
@click.option("--testall", is_flag=True, help="Run all stages and print intermediate results.")
@click.option("-c", "stage_c", is_flag=True, help="Compile to object file.")
def main(input_files, lex, parse_stage, validate, tacky, codegen, all_stage, testall, stage_c):
    """Compile one or more C files."""
    if not input_files and not any([lex, parse_stage, validate, tacky, codegen, all_stage, testall, stage_c]):
        click.echo(main.get_help(click.Context(main)))
        sys.exit(0)

    # Map flags to enum
    stage_map = {
        lex: CompilerStage.LEX,
        parse_stage: CompilerStage.PARSE,
        validate: CompilerStage.VALIDATE,
        tacky: CompilerStage.TACKY,
        codegen: CompilerStage.CODEGEN,
        all_stage: CompilerStage.ALL,
        testall: CompilerStage.TESTALL,
        stage_c: CompilerStage.C,
    }

    # Select the stage that was flagged
    selected_stages = [stage for flag, stage in stage_map.items() if flag]

    if len(selected_stages) > 1:
        click.echo("Error: Only one stage flag can be used at a time.", err=True)
        sys.exit(1)

    stage = selected_stages[0] if selected_stages else CompilerStage.ALL
    run_compiler(input_files, stage)


if __name__ == "__main__":
    main()