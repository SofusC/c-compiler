import os
import subprocess
import click

def preprocess(file):
    """Preprocess a C file to produce a .i file."""
    base, _ = os.path.splitext(file)
    output_file = f"{base}.i"

    run_gcc(["gcc", "-E", "-P", file, "-o", output_file],
            f"Preprocessing failed for {file}")

    return output_file

def assemble(file):
    """Assemble a file into an executable binary."""
    base, _ = os.path.splitext(file)
    output_file = base
    run_gcc(["gcc", file, "-o", output_file],
            f"Assembling failed for {file}")

    try:
        os.remove(file)
    except OSError as e:
        click.echo(f"Warning: Could not remove {file}: {e}", err=True)

    return output_file

def assemble_object(file):
    """Assemble a file into an object (.o) file."""
    base, _ = os.path.splitext(file)
    output_file = f"{base}.o"

    run_gcc(["gcc", "-c", file, "-o", output_file],
            f"Assembling object failed for {file}")

    try:
        os.remove(file)
    except OSError as e:
        click.echo(f"Warning: Could not remove {file}: {e}", err=True)

    return output_file

def run_gcc(command, error_message):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, err=True)

    if result.returncode != 0:
        raise RuntimeError(error_message)