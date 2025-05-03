import lexer
import parser
import emitter

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "tacky", "codegen", "all"]:
        ast = parser.Parser(tokens).parse_program()

    if flag in ["tacky", "codegen", "all"]:
        emitted_ir = emitter.IREmitter().emit_program(ast)

    if flag in ["codegen", "all"]:
        asm = ast.generate()

    if flag in ["all"]:
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            asm.generate(f)

    if flag == "lex":
        [print(token) for token in tokens]
    elif flag == "parse":
        print(ast)
    elif flag == "tacky":
        print(emitted_ir)
    elif flag == "codegen":
        asm.pretty()
    else:
        print(ast)
        asm.pretty()

    return output