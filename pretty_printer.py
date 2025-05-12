from enum import Enum

def is_simple(obj):
    return isinstance(obj, (int, float, str, bool, type(None)))

def printer(program):
    pretty = print_node(program)
    print(pretty)

def indent(text, level):
    return "    " * level + text

def print_list(list, level = 0):
    res = indent("instructions:", level)
    for elem in list:
        res += "\n"
        res += print_node(elem, level + 1, True)
    return res

def print_node(node, level = 0, in_list = False):
    if is_simple(node):
        return indent(str(node), level)
    if isinstance(node, list):
        return print_list(node, level)
    if isinstance(node, Enum):
        return indent(node.name, level)
    class_name = node.__class__.__name__
    vals = node.__dict__.values()
    if all(is_simple(val) for val in vals) or in_list:
        return indent(f"{class_name}(" + ", ".join(str(val) for val in vals) + ")",level)

    res = indent(f"{class_name}(", level)

    for key, val in node.__dict__.items():
        res += "\n"
        if is_simple(val):
            res += indent(str(val), level + 1)
        else:
            res += print_node(val, level + 1)
    res += "\n"
    res += indent(")", level)
    return res
    