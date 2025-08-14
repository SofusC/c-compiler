# C Compiler Project

This project is a simple C compiler implemented in Python. It parses, analyzes, and compiles a subset of the C language into x86-64 assembly, guided by Nora Sandlers book "Writing a C compiler".

## Features

- Lexical analysis, parsing, and AST generation
- Semantic analysis (type checking, variable resolution)
- Intermediate representation (IR) generation
- Assembly code generation and register allocation
- Integration with GCC for preprocessing, assembling, and linking

## Usage

To compile a C file:

```sh
python3 -m src.compiler_driver <source_file.c> [--stage]
```

### Stages

You can specify compilation stages with the following flags:

- `--lex`       : Lexical analysis only
- `--parse`     : Parse and print AST
- `--validate`  : Semantic analysis
- `--tacky`     : Generate and print IR
- `--codegen`   : Generate and print assembly AST
- `--all`       : Compile and link executable
- `-c`          : Compile to object file only

Example:

```sh
python3 -m src.compiler_driver example.c --all
```

## Project Structure

- `lexer.py`, `parser.py`         : Frontend (lexing and parsing)
- `c_ast.py`                      : C AST definitions
- `semantic_analysis/`            : Semantic analysis modules
- `ir_ast.py`, `emitter.py`       : IR and IR emission
- `assembly_ast.py`, `asm_generator.py`, `asm_allocator.py` : Assembly generation and register allocation
- `code_emitter.py`               : Final assembly code emission
- `compiler.py`, `compiler_driver.py` : Main compiler logic and driver

## Requirements

- Python 3.10+
- GCC (for preprocessing, assembling, and linking)
