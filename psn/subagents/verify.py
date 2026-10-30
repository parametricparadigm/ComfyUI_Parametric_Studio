"""Checks a role's output with plain code: a small JSON-schema subset, JSON extraction, text normalisation. No model judges another model's facts here."""
import re, json

def extract_json(text):
    """First JSON object in a model reply (handles ``` fences and chatter around it); None when there is none."""
    t = re.sub(r"```(?:json)?", "", text or "")
    dec, i = json.JSONDecoder(), t.find("{")
    while i >= 0:
        try: return dec.raw_decode(t[i:])[0]
        except json.JSONDecodeError: i = t.find("{", i + 1)
    return None

def validate(obj, schema, path="$"):
    """Subset: type, required, properties, items, enum, minimum, maximum, minItems, maxItems, minLength, maxLength, uniqueItems. -> list of problems."""
    p, t = [], schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "number": (int, float), "integer": int}
    if t and not (isinstance(obj, types[t]) and not (t in ("number", "integer") and isinstance(obj, bool))): return [f"{path}: expected {t}, got {type(obj).__name__}"]
    if "enum" in schema and obj not in schema["enum"]: p.append(f"{path}: {obj!r} not one of {schema['enum']}")
    if t in ("number", "integer"):
        if "minimum" in schema and obj < schema["minimum"]: p.append(f"{path}: {obj} < {schema['minimum']}")
        if "maximum" in schema and obj > schema["maximum"]: p.append(f"{path}: {obj} > {schema['maximum']}")
    if t == "string":
        if "minLength" in schema and len(obj) < schema["minLength"]: p.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(obj) > schema["maxLength"]: p.append(f"{path}: longer than {schema['maxLength']} characters")
    if t == "array":
        if "minItems" in schema and len(obj) < schema["minItems"]: p.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(obj) > schema["maxItems"]: p.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in obj}) < len(obj): p.append(f"{path}: duplicate items")
        for i, x in enumerate(obj):
            if "items" in schema: p += validate(x, schema["items"], f"{path}[{i}]")
    if t == "object":
        for k in schema.get("required", []):
            if k not in obj: p.append(f"{path}: missing '{k}'")
        for k, s in schema.get("properties", {}).items():
            if k in obj: p += validate(obj[k], s, f"{path}.{k}")
    return p

def norm(s): return re.sub(r"\s+", " ", re.sub(r"[‘’]", "'", re.sub(r"[“”]", '"', str(s)))).strip().lower()
def contains(haystack, needle): return bool(norm(needle)) and norm(needle) in norm(haystack)
def numbers(s): return set(re.findall(r"\d+(?:[.,]\d+)?", str(s)))

import re as _re
SFW_BLOCK = _re.compile(r"\b(nude|naked|nsfw|porn\w*|explicit|erotic\w*|sex(?:ual|y)?|nipple\w*|genital\w*|fetish|gore|decapitat\w*|child\s+abuse|underage|loli\w*)\b", _re.I)
