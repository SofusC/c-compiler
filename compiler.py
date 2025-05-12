import lexer
import parser
import emitter
import asm_generator
import pretty_printer

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "tacky", "codegen", "all", "testall"]:
        ast = parser.Parser(tokens).parse_program()

    if flag in ["tacky", "codegen", "all", "testall"]:
        emitted_ir = emitter.IREmitter().emit_program(ast)

    if flag in ["codegen", "all", "testall"]:
        asm = asm_generator.lower_to_asm(emitted_ir)
        allocator = asm_generator.AsmAllocator()
        allocator.lower_pseudo_regs(asm)
        allocator.add_stack_frame(asm)
        allocator.legalize_instr(asm)

    if flag in ["all", "testall"]:
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            assembly_code = asm_generator.emit_code(asm)
            f.write(assembly_code)

    if flag == "lex":
        [print(token) for token in tokens]
    elif flag == "parse":
        pretty_printer.printer(ast)
    elif flag == "tacky":
        pretty_printer.printer(emitted_ir)
    elif flag == "codegen":
        pretty_printer.printer(asm)
    elif flag == "testall":
        print("C AST:")
        pretty_printer.printer(ast)
        print("Tacky AST:")
        pretty_printer.printer(emitted_ir)
        print("Assembly AST:")
        pretty_printer.printer(asm)
        print("Assembly code:")
        print(assembly_code)

    return output