"""Safe expression evaluator for ComfyUI_Parametric_Studio. Original implementation (design from the owner's spec; no third-party code).
It NEVER calls eval/exec/compile: the expression is parsed with ast and walked by a small interpreter that only knows a whitelist of node types and functions.
No attribute access, no names beyond the supplied variables and constants, no comprehensions/lambdas, bounded size and bounded results."""
import ast, math, operator

class ExprError(ValueError):
    pass

MAX_LEN, MAX_NODES, MAX_DEPTH, MAX_STR, MAX_SEQ = 2000, 400, 40, 100_000, 10_000
CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}

def _size_ok(v):
    if isinstance(v, (str, bytes)) and len(v) > MAX_STR: raise ExprError("string too long")
    if isinstance(v, (list, tuple, dict)) and len(v) > MAX_SEQ: raise ExprError("sequence too long")
    return v

def _pow(a, b):
    if isinstance(a, bool) or isinstance(b, bool): a, b = int(a), int(b)
    if isinstance(a, int) and isinstance(b, int):
        if b < 0: return a ** b
        if b > 256 or (abs(a) > 1 and b * max(1, a.bit_length()) > 4096): raise ExprError("power too large")
    elif isinstance(b, (int, float)) and abs(b) > 1e4: raise ExprError("power too large")
    if not all(isinstance(x, (int, float)) for x in (a, b)): raise ExprError("power needs numbers")
    return a ** b

def _mul(a, b):
    for s, n in ((a, b), (b, a)):
        if isinstance(s, (str, list, tuple)) and isinstance(n, int) and not isinstance(n, bool):
            if len(s) * max(n, 0) > MAX_STR: raise ExprError("result too large")
    return a * b

def _add(a, b):
    if isinstance(a, (str, list, tuple)) and isinstance(b, type(a)) and len(a) + len(b) > MAX_STR: raise ExprError("result too large")
    return a + b

BIN = {ast.Add: _add, ast.Sub: operator.sub, ast.Mult: _mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: _pow}
UN = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}
CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}

def _clamp(x, lo, hi): return max(lo, min(hi, x))
def _lerp(a, b, t): return a + (b - a) * t
def _sign(x): return (x > 0) - (x < 0)
def _seq(n, m=None, step=1):
    r = range(n) if m is None else range(n, m, step)
    if len(r) > MAX_SEQ: raise ExprError("range too long")
    return list(r)
def _join(sep, items): return _size_ok(str(sep).join(str(i) for i in items))
def _replace(s, a, b): return _size_ok(str(s).replace(str(a), str(b)))
def _at(seq, i, default=None):
    try: return seq[i]
    except (IndexError, KeyError, TypeError): return default
def _num(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)): raise ExprError("number expected")
    return x

FUNCS = {
    "abs": abs, "min": min, "max": max, "round": round, "int": int, "float": float, "str": str, "bool": bool, "len": len, "sum": lambda xs: sum(xs), "sorted": lambda xs: sorted(xs),
    "sqrt": lambda x: math.sqrt(_num(x)), "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2, "hypot": math.hypot,
    "floor": math.floor, "ceil": math.ceil, "log": math.log, "log2": math.log2, "log10": math.log10, "exp": lambda x: math.exp(_num(x)), "radians": math.radians, "degrees": math.degrees,
    "clamp": _clamp, "lerp": _lerp, "sign": _sign, "seq": _seq, "at": _at, "join": _join, "replace": _replace,
    "lower": lambda s: str(s).lower(), "upper": lambda s: str(s).upper(), "strip": lambda s: str(s).strip(), "startswith": lambda s, p: str(s).startswith(str(p)),
    "endswith": lambda s, p: str(s).endswith(str(p)), "contains": lambda s, p: str(p) in str(s), "split": lambda s, sep=None: str(s).split(None if sep is None else str(sep))[:MAX_SEQ],
}
ALLOWED = (int, float, bool, str, type(None), list, tuple, dict)

class _Eval:
    def __init__(self, variables):
        self.vars = dict(variables); self.count = 0
    def ev(self, n, depth=0):
        self.count += 1
        if self.count > MAX_NODES or depth > MAX_DEPTH: raise ExprError("expression too complex")
        t = type(n)
        if t is ast.Constant:
            if isinstance(n.value, (int, float, bool, str, type(None))): return _size_ok(n.value)
            raise ExprError("constant type not allowed")
        if t is ast.Name:
            if n.id in self.vars: return self.vars[n.id]
            if n.id in CONSTS: return CONSTS[n.id]
            raise ExprError(f"unknown name '{n.id}'")
        if t is ast.BinOp and type(n.op) in BIN: return _size_ok(BIN[type(n.op)](self.ev(n.left, depth + 1), self.ev(n.right, depth + 1)))
        if t is ast.UnaryOp and type(n.op) in UN: return UN[type(n.op)](self.ev(n.operand, depth + 1))
        if t is ast.BoolOp:
            val = None
            for v in n.values:
                val = self.ev(v, depth + 1)
                if isinstance(n.op, ast.And) and not val: return val
                if isinstance(n.op, ast.Or) and val: return val
            return val
        if t is ast.Compare:
            left = self.ev(n.left, depth + 1)
            for op, comp in zip(n.ops, n.comparators):
                if type(op) not in CMP: raise ExprError("comparison not allowed")
                right = self.ev(comp, depth + 1)
                if not CMP[type(op)](left, right): return False
                left = right
            return True
        if t is ast.IfExp: return self.ev(n.body, depth + 1) if self.ev(n.test, depth + 1) else self.ev(n.orelse, depth + 1)
        if t in (ast.List, ast.Tuple):
            if len(n.elts) > MAX_SEQ: raise ExprError("sequence too long")
            out = [self.ev(e, depth + 1) for e in n.elts]; return out if t is ast.List else tuple(out)
        if t is ast.Dict:
            if any(k is None for k in n.keys): raise ExprError("dict unpacking not allowed")
            return {self.ev(k, depth + 1): self.ev(v, depth + 1) for k, v in zip(n.keys, n.values)}
        if t is ast.Subscript:
            base = self.ev(n.value, depth + 1)
            if not isinstance(base, (list, tuple, str, dict)): raise ExprError("cannot index this value")
            sl = n.slice
            if isinstance(sl, ast.Slice):
                parts = [self.ev(x, depth + 1) if x is not None else None for x in (sl.lower, sl.upper, sl.step)]
                if not isinstance(base, (list, tuple, str)) or any(p is not None and not isinstance(p, int) for p in parts): raise ExprError("bad slice")
                try: return base[slice(*parts)]
                except ValueError as e: raise ExprError(f"bad slice: {e}")
            idx = self.ev(sl, depth + 1)
            try: return base[idx]
            except (IndexError, KeyError, TypeError) as e: raise ExprError(f"index error: {e}")
        if t is ast.Call:
            if not isinstance(n.func, ast.Name) or n.func.id not in FUNCS: raise ExprError("function not allowed")
            if any(isinstance(a, ast.Starred) for a in n.args) or any(k.arg is None for k in n.keywords): raise ExprError("star arguments not allowed")
            args = [self.ev(a, depth + 1) for a in n.args]; kw = {k.arg: self.ev(k.value, depth + 1) for k in n.keywords}
            try: return _size_ok(FUNCS[n.func.id](*args, **kw))
            except ExprError: raise
            except (ValueError, TypeError, ZeroDivisionError, OverflowError) as e: raise ExprError(f"{n.func.id}: {e}")
        raise ExprError(f"{t.__name__} is not allowed")

def evaluate(expression, variables=None):
    """Evaluate `expression` with `variables`; returns int/float/bool/str/None/list/tuple/dict. Raises ExprError on anything not whitelisted."""
    if not isinstance(expression, str): raise ExprError("expression must be text")
    if len(expression) > MAX_LEN: raise ExprError("expression too long")
    try: tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e: raise ExprError(f"syntax error: {e}")
    for v in (variables or {}).values():
        if not isinstance(v, ALLOWED): raise ExprError("variable has an unsupported type")
    try: out = _Eval(variables or {}).ev(tree.body)
    except RecursionError: raise ExprError("expression too deeply nested")
    except ZeroDivisionError: raise ExprError("division by zero")
    except OverflowError: raise ExprError("number too large")
    if not isinstance(out, ALLOWED): raise ExprError("result type not allowed")
    return out
