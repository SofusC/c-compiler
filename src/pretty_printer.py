from enum import Enum
from dataclasses import is_dataclass, fields, asdict

def is_simple(obj):
    return isinstance(obj, (int, float, str, bool, type(None)))

def printer(program):
    pretty = print_node(program)
    print(pretty)

def indent(text, level):
    return "    " * level + text

def print_list(list, level = 0):
    lines = [indent("instructions:", level)]
    for elem in list:
        lines.append(print_node(elem, level + 1, True))
    return "\n".join(lines)

def get_attr_values(obj):
    if is_dataclass(obj):
        return [getattr(obj, f.name) for f in fields(obj)]
    elif isinstance(obj, type):
        return [repr(obj)]
    elif hasattr(obj, "__dict__"):
        return list(obj.__dict__.values())
    else:
        return []

def print_node(node, level = 0, in_list = False):
    if is_simple(node):
        return indent(str(node), level)
    if isinstance(node, list):
        return print_list(node, level)
    if isinstance(node, Enum):
        return indent(node.name, level)
    
    class_name = node.__class__.__name__
    values = get_attr_values(node)

    inline = all(is_simple(val) for val in values) #or in_list
    if inline:
        return indent(f"{class_name}(" + ", ".join(print_node(val, 0, True) for val in values) + ")", level)

    lines = [indent(f"{class_name}(", level)]

    for val in values:
        lines.append(print_node(val, level + 1))
    lines.append(indent(")", level))
    return "\n".join(lines)
    