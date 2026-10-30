"""ComfyUI node wrappers (original). Pure logic lives in psn/: expr (safe evaluator), sandbox (separate process), orchestration (gate/plan/retry)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn import expr as _expr, sandbox as _sbx, orchestration as _orch

class AnyType(str):
    def __ne__(self, other): return False
ANY = AnyType("*")
CAT = "ParametricStudio/Logic"

def _num(x, default=0.0):
    try: return float(x)
    except (TypeError, ValueError): return default

class PSN_Expression:
    """Evaluate a safe expression (maths, comparisons, strings, lists). Nothing is executed: only whitelisted operations and functions."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"expression": ("STRING", {"multiline": True, "default": "a + b"})}, "optional": {"a": (ANY,), "b": (ANY,), "c": (ANY,), "d": (ANY,)}}
    RETURN_TYPES = (ANY, "FLOAT", "INT", "STRING", "BOOLEAN"); RETURN_NAMES = ("result", "as_float", "as_int", "as_text", "as_bool"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, expression, a=None, b=None, c=None, d=None):
        v = {k: x for k, x in (("a", a), ("b", b), ("c", c), ("d", d)) if x is not None}
        r = _expr.evaluate(expression, v); f = _num(r)
        return (r, f, int(f) if f == f and abs(f) < 2**62 else 0, r if isinstance(r, str) else json.dumps(r), bool(r))

class PSN_SandboxScript:
    """Run Python in a separate, resource-limited process (import allow-list, no network, no files, timeout). Define run(inputs) or set `result`. Defence in depth, NOT an OS sandbox."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"code": ("STRING", {"multiline": True, "default": "def run(inputs):\n    return inputs"}), "input_json": ("STRING", {"multiline": True, "default": "{}"}),
                                              "timeout_s": ("INT", {"default": 10, "min": 1, "max": 60}), "memory_mb": ("INT", {"default": 512, "min": 64, "max": 4096})}}
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING", "STRING"); RETURN_NAMES = ("result_json", "ok", "stdout", "error"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, code, input_json, timeout_s, memory_mb):
        try: data = json.loads(input_json or "null")
        except json.JSONDecodeError as e: return ("null", False, "", f"input_json is not valid JSON: {e}")
        r = _sbx.run(code, data, timeout=timeout_s, mem_mb=memory_mb); return (json.dumps(r["result"]), r["ok"], r["stdout"], r["error"])

class PSN_Branch:
    """If/else: only the chosen input is evaluated (lazy), so the other branch's nodes never run."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"condition": ("BOOLEAN", {"default": True}), "on_true": (ANY, {"lazy": True}), "on_false": (ANY, {"lazy": True})}}
    RETURN_TYPES = (ANY,); RETURN_NAMES = ("result",); FUNCTION = "run"; CATEGORY = CAT
    def check_lazy_status(self, condition, on_true=None, on_false=None):
        return ["on_true"] if condition else ["on_false"]
    def run(self, condition, on_true=None, on_false=None): return (on_true if condition else on_false,)

class PSN_QualityGate:
    """Pass the value through when score meets the threshold, otherwise output the fallback. Also reports pass/fail and why."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"score": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}), "threshold": ("FLOAT", {"default": 0.5, "min": -1e9, "max": 1e9, "step": 0.001}), "mode": (list(_orch.MODES),)},
                                  "optional": {"value": (ANY,), "fallback": (ANY,)}}
    RETURN_TYPES = ("BOOLEAN", ANY, "STRING"); RETURN_NAMES = ("passed", "result", "reason"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, score, threshold, mode, value=None, fallback=None):
        ok, why = _orch.gate(score, threshold, mode); return (ok, value if ok else fallback, why)

class PSN_AttemptPlanner:
    """Seed/cfg/steps for retry attempt N (use with a quality gate and a batch or the studio's retry loop). Deterministic."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"attempt": ("INT", {"default": 0, "min": 0, "max": 99}), "attempts": ("INT", {"default": 3, "min": 1, "max": 100}), "base_seed": ("INT", {"default": 0, "min": 0, "max": 2**62}),
                                              "cfg": ("FLOAT", {"default": 4.0, "min": 0.0, "max": 100.0, "step": 0.1}), "cfg_step": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.1}), "steps": ("INT", {"default": 20, "min": 1, "max": 1000}), "steps_step": ("INT", {"default": 0, "min": -50, "max": 50})}}
    RETURN_TYPES = ("INT", "FLOAT", "INT", "STRING"); RETURN_NAMES = ("seed", "cfg", "steps", "plan_json"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, attempt, attempts, base_seed, cfg, cfg_step, steps, steps_step):
        plan = _orch.plan_attempts(attempts, base_seed, cfg, cfg_step, steps, steps_step); p = plan[min(attempt, len(plan) - 1)]; return (p["seed"], p["cfg"], p["steps"], json.dumps(plan))

NODE_CLASS_MAPPINGS = {"PSN_Expression": PSN_Expression, "PSN_SandboxScript": PSN_SandboxScript, "PSN_Branch": PSN_Branch, "PSN_QualityGate": PSN_QualityGate, "PSN_AttemptPlanner": PSN_AttemptPlanner}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Expression": "PSN Expression (safe)", "PSN_SandboxScript": "PSN Sandboxed Script", "PSN_Branch": "PSN Branch (if/else)", "PSN_QualityGate": "PSN Quality Gate", "PSN_AttemptPlanner": "PSN Attempt Planner"}
