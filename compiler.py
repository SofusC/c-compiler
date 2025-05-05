import lexer
import parser
import emitter
import assembly_ast

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "tacky", "codegen", "all"]:
        ast = parser.Parser(tokens).parse_program()

    if flag in ["tacky", "codegen", "all"]:
        emitted_ir = emitter.IREmitter().emit_program(ast)

    if flag in ["codegen", "all"]:
        asm = assembly_ast.AsmGenerator().generate_asm_ast(emitted_ir)

    if flag in ["all"]:
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            assembly_code = assembly_ast.AsmGenerator().generate_asm_code(asm)
            f.write(assembly_code)

    if flag == "lex":
        [print(token) for token in tokens]
    elif flag == "parse":
        print(ast)
    elif flag == "tacky":
        print(emitted_ir)
    elif flag == "codegen":
        print(asm)
    else:
        print(ast)
        print(asm)

    return output