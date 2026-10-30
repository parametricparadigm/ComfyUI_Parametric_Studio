"""Child process for psn.sandbox. Reads {"code","inputs","allow"} as JSON on stdin, validates the code's AST (import allow-list, no underscore attributes, no dangerous names),
runs it with a minimal builtins table, and prints one result line. Started as `python -I -S sandbox_runner.py` with resource limits set by the parent.
This is defence in depth, not an OS sandbox: the parent also limits CPU/memory/files and kills on timeout; do not run hostile code outside a container."""
import sys, json, ast, io

MARK = "@@PSN_RESULT@@"
DEFAULT_ALLOW = {"math", "json", "re", "statistics", "itertools", "collections", "functools", "string", "textwrap", "datetime", "random", "decimal", "fractions", "heapq", "bisect", "unicodedata", "hashlib", "base64", "binascii"}
BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr", "hasattr", "type", "object", "memoryview", "help", "exit", "quit", "super", "classmethod", "staticmethod", "property"}
BAD_ATTRS = {"format", "format_map", "vformat", "Formatter", "mro", "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "f_back", "f_globals", "f_locals", "f_builtins", "tb_frame", "tb_next", "co_code", "func_globals", "system", "popen", "modules"}

def check(tree, allow):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in allow or "." in a.name: raise ValueError(f"import of '{a.name}' is not allowed")
        elif isinstance(n, ast.ImportFrom):
            if n.level or (n.module or "").split(".")[0] not in allow or "." in (n.module or ""): raise ValueError(f"import from '{n.module}' is not allowed")
            if any(a.name.startswith("_") or a.name == "*" for a in n.names): raise ValueError("import of private names is not allowed")
        elif isinstance(n, ast.Attribute):
            if n.attr.startswith("_") or n.attr in BAD_ATTRS: raise ValueError(f"attribute '{n.attr}' is not allowed")
        elif isinstance(n, ast.Name):
            if n.id in BAD_NAMES or n.id.startswith("__"): raise ValueError(f"name '{n.id}' is not allowed")
        elif isinstance(n, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith, ast.Global, ast.Nonlocal)): raise ValueError(f"{type(n).__name__} is not allowed")
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 200000: raise ValueError("string literal too long")

def main():
    real_out = sys.stdout
    payload = json.loads(sys.stdin.read()); code, inputs = payload["code"], payload.get("inputs")
    allow = DEFAULT_ALLOW if not payload.get("allow") else (DEFAULT_ALLOW & set(payload["allow"]))
    buf = io.StringIO()
    def out(ok, **kw):
        kw.update(ok=ok, stdout=buf.getvalue()[:10000]); real_out.write("\n" + MARK + json.dumps(kw) + "\n"); real_out.flush()
    try:
        tree = ast.parse(code); check(tree, allow)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:
        return out(False, error=f"rejected: {e}")
    import builtins as b
    safe = {k: getattr(b, k) for k in ("abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int", "isinstance", "issubclass", "len", "list", "map", "max", "min", "range", "reversed", "round", "set", "frozenset", "sorted", "str", "sum", "tuple", "zip", "divmod", "pow", "chr", "ord", "bin", "hex", "oct", "repr", "slice", "iter", "next", "callable", "bytes", "bytearray", "complex",
                                              "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "ZeroDivisionError", "ArithmeticError", "RuntimeError", "StopIteration", "AssertionError", "OverflowError", "LookupError", "AttributeError", "NotImplementedError", "True", "False", "None")}
    def _print(*a, sep=" ", end="\n", **kw):
        if buf.tell() < 20000: buf.write(sep.join(str(x) for x in a) + end)
    safe["print"] = _print
    real_import = b.__import__
    def _imp(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name.split(".")[0] not in allow or "." in name: raise ImportError(f"import of '{name}' is not allowed")
        if any(str(f).startswith("_") for f in (fromlist or ())): raise ImportError("private names are not importable")
        return real_import(name, globals, locals, fromlist, level)
    safe["__import__"] = _imp
    try:
        import socket
        def _blocked(*a, **k): raise OSError("network is disabled")
        socket.socket = socket.create_connection = socket.getaddrinfo = _blocked
    except Exception: pass
    env = {"__builtins__": safe, "__name__": "psn_sandbox", "inputs": inputs}
    try:
        exec(compile(tree, "<psn>", "exec"), env)
        if callable(env.get("run")): res = env["run"](inputs)
        elif "result" in env: res = env["result"]
        else: return out(False, error="define run(inputs) or set a variable named result")
        s = json.dumps(res)
        if len(s) > 1_000_000: return out(False, error="result is larger than 1 MB")
        return out(True, result=json.loads(s))
    except BaseException as e:
        return out(False, error=f"{type(e).__name__}: {str(e)[:300]}")

if __name__ == "__main__":
    main()
