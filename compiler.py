import lexer
import parser

def compile_c(file, flag):
    if flag == "lex":
        tokens = lexer.lex(file)
    elif flag == "parse":
        tokens = lexer.lex(file)
        [print(token) for token in tokens]
        ast = parser.parse(tokens)
        print(ast)
    elif flag == "codegen":
        tokens = lexer.lex(file)
        ast = parser.parse(tokens)
        print(ast)
        asm = ast.generate()
        asm.pretty()
    else:
        tokens = lexer.lex(file)
        ast = parser.parse(tokens)
        print(ast)
        asm = ast.generate()
        asm.pretty()
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            asm.generate(f)
        return output
