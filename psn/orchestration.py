"""Orchestration helpers (original design): quality gate, attempt planning, retry-until-pass and rule-based routing. Pure Python so the studio backend and the ComfyUI nodes share one implementation."""
from .expr import evaluate, ExprError

MODES = (">=", ">", "<=", "<", "==", "!=")

def gate(score, threshold, mode=">="):
    """-> (passed, reason). Missing/NaN scores fail."""
    if mode not in MODES: raise ValueError(f"mode must be one of {MODES}")
    try: s, t = float(score), float(threshold)
    except (TypeError, ValueError): return False, "score is not a number"
    if s != s: return False, "score is NaN"
    ok = {">=": s >= t, ">": s > t, "<=": s <= t, "<": s < t, "==": s == t, "!=": s != t}[mode]
    return ok, f"score {s:g} {mode} {t:g}: {'pass' if ok else 'fail'}"

def plan_attempts(n, base_seed=0, cfg=None, cfg_step=0.0, steps=None, steps_step=0):
    """Deterministic schedule: a new seed per attempt, optional cfg and steps drift (e.g. +1 step per retry)."""
    n = max(1, min(int(n), 100)); out = []
    for i in range(n):
        d = {"attempt": i, "seed": (int(base_seed) + i * 7919) % (2**63)}
        if cfg is not None: d["cfg"] = round(float(cfg) + i * float(cfg_step), 4)
        if steps is not None: d["steps"] = max(1, int(steps) + i * int(steps_step))
        out.append(d)
    return out

def retry(run_fn, score_fn, max_tries=3, threshold=0.5, mode=">=", plan=None, stop_on_pass=True):
    """Run run_fn(attempt_dict) up to max_tries, score each with score_fn(result), keep the best. Exceptions count as a failed attempt (recorded, not raised).
    -> {"passed", "best", "best_score", "history": [{"attempt","score","passed","reason","error"}]}"""
    plan = plan or plan_attempts(max_tries); history = []; best = None; best_s = None
    for att in plan[:max_tries]:
        try: res = run_fn(att); s = score_fn(res); err = None
        except Exception as e: res, s, err = None, float("nan"), f"{type(e).__name__}: {e}"
        ok, why = gate(s, threshold, mode); history.append({"attempt": att.get("attempt"), "score": s, "passed": ok, "reason": why, "error": err})
        if err is None and (best_s is None or (s == s and (best_s != best_s or s > best_s))): best, best_s = res, s
        if ok and stop_on_pass: break
    return {"passed": any(h["passed"] for h in history), "best": best, "best_score": best_s, "history": history}

def route(fields, rules, default=None):
    """First rule whose safe expression is true wins. rules = [(expression, target), ...]; fields = dict of simple values. Bad expressions raise ExprError."""
    for expr, target in rules:
        if evaluate(expr, fields): return target
    return default
