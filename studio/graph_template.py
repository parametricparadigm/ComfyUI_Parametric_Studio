"""Fill ${name} placeholders in an API-format graph. A value that is exactly "${name}" is replaced by the typed value (int, float, bool, Asset ...);
a placeholder inside a longer string is replaced by its text. A name with no value raises KeyError so a template is never submitted half filled."""
from __future__ import annotations

import re

_PH = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def placeholders(graph) -> set[str]:
    found: set[str] = set()

    def walk(v):
        if isinstance(v, str):
            found.update(_PH.findall(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(graph)
    return found


def fill(graph, values: dict):
    def walk(v):
        if isinstance(v, str):
            m = _PH.fullmatch(v)
            if m:
                return values[m.group(1)]
            return _PH.sub(lambda mm: str(values[mm.group(1)]), v)
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    return walk(graph)
