"""ParametricStudio: exact arithmetic evaluation node.

A dedicated tool for exact arithmetic so that numeric parameters
(resolution, duration, VRAM estimates, ...) are computed precisely
instead of being approximated or hallucinated by a language model.

The node evaluates a small, safe arithmetic expression using Python's
`ast` module (no eval/exec). It supports integers, floats, the usual
binary operators (+ - * / // % **), unary +/-, parentheses, and a
few named constants (pi, e). Division by zero and other errors are
reported cleanly instead of raising.
"""

import ast
import math
import operator

CAT = "ParametricStudio/Tools"

# ---------------------------------------------------------------------------
# Safe expression evaluator (ast-based, no eval/exec/compile)
# ---------------------------------------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node):
    """Recursively evaluate an AST node. Raises ValueError on anything
    that is not a plain arithmetic expression."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("only numeric constants are allowed")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError("operator not allowed: %s" % type(node.op).__name__)
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError("unary operator not allowed: %s" % type(node.op).__name__)
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise ValueError("unknown name: %s" % node.id)
    raise ValueError("expression element not allowed: %s" % type(node).__name__)


def exact_eval(expr):
    """Evaluate a numeric arithmetic expression exactly (int/float).

    Returns (value, error). On success error is None; on failure value
    is None and error is a human-readable string.
    """
    if not isinstance(expr, str):
        return None, "expression must be a string"
    text = expr.strip()
    if not text:
        return None, "expression is empty"
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        return None, "syntax error: %s" % exc.msg
    try:
        value = _eval_node(tree)
    except ZeroDivisionError:
        return None, "division by zero"
    except OverflowError:
        return None, "overflow"
    except ValueError as exc:
        return None, str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return None, "evaluation error: %s" % exc
    if isinstance(value, float) and value.is_integer():
        # keep ints as ints when the result is whole
        if abs(value) < 1e15:
            value = int(value)
    return value, None


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_ExactArithmetic:
    """Evaluate an arithmetic expression exactly (no LLM guessing).

    Use this to compute resolutions, durations, VRAM estimates, etc.
    so the workflow uses precise numbers. Returns the numeric result
    as a FLOAT and a human-readable status string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "expression": ("STRING", {"default": "1024 * 768", "multiline": False}),
            },
            "optional": {
                "fallback": ("FLOAT", {"default": 0.0, "min": -1e12, "max": 1e12}),
            },
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("value", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, expression, fallback=0.0):
        value, error = exact_eval(expression)
        if error is not None:
            return (float(fallback), "error: %s" % error)
        return (float(value), "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_ExactArithmetic": PSN_ExactArithmetic,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ExactArithmetic": "Exact Arithmetic (ParametricStudio)",
}
