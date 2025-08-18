import sys
import click
from .compiler import run_compiler
from .compiler_stages import CompilerStage

@click.command()
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
@click.option("--lex", is_flag=True, help="Run lexer only.")
@click.option("--parse", is_flag=True, help="Parse C into AST.")
@click.option("--validate", is_flag=True, help="Validate C AST.")
@click.option("--tacky", is_flag=True, help="Generate Tacky IR.")
@click.option("--codegen", is_flag=True, help="Generate assembly code.")
@click.option("--all", "all_stage", is_flag=True, help="Run all stages.")
@click.option("--testall", is_flag=True, help="Run all stages and print intermediate results.")
@click.option("-c", "stage_c", is_flag=True, help="Compile to object file.")
def main(input_files, lex, parse, validate, tacky, codegen, all_stage, testall, stage_c):
    if not input_files and not any([lex, parse, validate, tacky, codegen, all_stage, testall, stage_c]):
        click.echo(main.get_help(click.Context(main)))
        sys.exit(0)

    stage_map = {
        lex: CompilerStage.LEX,
        parse: CompilerStage.PARSE,
        validate: CompilerStage.VALIDATE,
        tacky: CompilerStage.TACKY,
        codegen: CompilerStage.CODEGEN,
        all_stage: CompilerStage.ALL,
        testall: CompilerStage.TESTALL,
        stage_c: CompilerStage.C,
    }

    selected_stages = [stage for flag, stage in stage_map.items() if flag]

    if len(selected_stages) > 1:
        click.echo("Error: Only one stage flag can be used at a time.", err=True)
        sys.exit(1)

    stage = selected_stages[0] if selected_stages else CompilerStage.ALL
    run_compiler(input_files, stage)


if __name__ == "__main__":
    main()