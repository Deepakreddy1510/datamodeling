"""Small fallback subset of PyYAML used in constrained test environments.

This module intentionally implements only the simple mapping/list syntax used by
this repository's fixtures. It is not a general YAML parser.
"""

class YAMLError(Exception):
    pass


def _scalar(value):
    value = value.strip()
    if value == "":
        return ""
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    return value


def _container_for_next(lines, index, indent):
    for j in range(index + 1, len(lines)):
        raw = lines[j]
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        next_indent = len(raw) - len(raw.lstrip(" "))
        if next_indent <= indent:
            return {}
        return [] if raw.strip().startswith("- ") else {}
    return {}


def safe_load(text):
    if text is None:
        return None
    lines = [line.rstrip() for line in str(text).splitlines()]
    root = {}
    stack = [(-1, root)]
    for index, raw in enumerate(lines):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        item = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise YAMLError("Invalid indentation")
        parent = stack[-1][1]
        if item.startswith("- "):
            if not isinstance(parent, list):
                raise YAMLError("List item found outside a list")
            value = item[2:].strip()
            if ":" in value and not value.startswith(('"', "'")):
                key, remainder = value.split(":", 1)
                child = {key.strip(): _scalar(remainder) if remainder.strip() else _container_for_next(lines, index, indent)}
                parent.append(child)
                if not remainder.strip():
                    stack.append((indent, child[key.strip()]))
            else:
                parent.append(_scalar(value))
            continue
        if ":" not in item:
            raise YAMLError(f"Invalid YAML line: {item}")
        key, remainder = item.split(":", 1)
        key = key.strip()
        if not isinstance(parent, dict):
            raise YAMLError("Mapping item found inside a scalar/list")
        if remainder.strip():
            parent[key] = _scalar(remainder)
        else:
            parent[key] = _container_for_next(lines, index, indent)
            stack.append((indent, parent[key]))
    return root
