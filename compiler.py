import lexer
import parser

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "codegen", "all"]:
        ast = parser.parse(tokens)

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
    elif flag == "codegen":
        asm.pretty()
    else:
        print(ast)
        asm.pretty()

    return output