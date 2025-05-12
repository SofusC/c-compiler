import lexer
import parser
import emitter
import asm_generator

def compile_c(file, flag):
    output = None
    tokens = lexer.lex(file)
    if flag in ["parse", "tacky", "codegen", "all"]:
        ast = parser.Parser(tokens).parse_program()

    if flag in ["tacky", "codegen", "all"]:
        emitted_ir = emitter.IREmitter().emit_program(ast)

    if flag in ["codegen", "all"]:
        asm = asm_generator.lower_to_asm(emitted_ir)
        allocator = asm_generator.AsmAllocator()
        allocator.lower_pseudo_regs(asm)
        allocator.add_stack_frame(asm)
        allocator.legalize_instr(asm)

    if flag in ["all"]:
        output = file[:-2] + ".s"
        with open(output, "w") as f:
            assembly_code = asm_generator.emit_code(asm)
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