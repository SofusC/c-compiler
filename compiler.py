import lexer
import parser
import asm_generator

def compile_c(file, flag):
    if flag == "lex":
        tokens = lexer.lex(file)
    if flag == "parse":
        tokens = lexer.lex(file)
        [print(token) for token in tokens]
        ast = parser.parse(tokens)
        print(ast)
    if flag == "codegen":
        tokens = lexer.lex(file)
        ast = parser.parse(tokens)
        print(ast)
        asm = ast.generate()
        asm.pretty()
