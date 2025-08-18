import sys
import click
from .compiler import run_compiler
from .compiler_stages import CompilerStage

@click.command()
@click.option("--lex", "stage", flag_value=CompilerStage.LEX, help="Run lexer only.")
@click.option("--parse", "stage", flag_value=CompilerStage.PARSE, help="Parse C into AST.")
@click.option("--validate", "stage", flag_value=CompilerStage.VALIDATE, help="Validate C AST.")
@click.option("--tacky", "stage", flag_value=CompilerStage.TACKY, help="Generate Tacky IR.")
@click.option("--codegen", "stage", flag_value=CompilerStage.CODEGEN, help="Generate assembly code.")
@click.option("--all", "stage", flag_value=CompilerStage.ALL, help="Run all stages.")
@click.option("--testall", "stage", flag_value=CompilerStage.TESTALL, help="Run all stages and print intermediate results.")
@click.option("-c", "stage", flag_value=CompilerStage.C, help="Compile to object file.")
@click.argument("input_files", nargs=-1, type=click.Path(exists=True))
def main(stage, input_files):
    if isinstance(stage, str) and stage.startswith("CompilerStage."):
        stage = CompilerStage[stage.split(".")[-1]]

    if not stage and not input_files:
        click.echo(main.get_help(click.Context(main)))
        sys.exit(0)

    if stage is None:
        stage = CompilerStage.ALL

    run_compiler(input_files, stage)



if __name__ == "__main__":
    main()