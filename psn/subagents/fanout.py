"""Run several subagents at once and join the answers: first_ok, vote (majority of identical answers), all, merge (text joined), best (highest score from a judge role)."""
import json, concurrent.futures as cf
from collections import Counter
from psn.subagents.runner import run_subagent

def fan_out(jobs, max_workers=4, runner=run_subagent, **kw):
    """jobs: [{"role", "task", "ctx"?}] -> results in the same order. A crash in one job becomes a failed Result, never an exception for the others."""
    def one(j):
        try: return runner(j["role"], j["task"], j.get("ctx"), **kw)
        except PermissionError: raise
        except Exception as e:
            from psn.subagents.runner import Result
            return Result(False, str(j.get("role")), problems=[f"{type(e).__name__}: {str(e)[:120]}"])
    with cf.ThreadPoolExecutor(max(1, min(int(max_workers), len(jobs) or 1))) as ex: return list(ex.map(one, jobs))

def _key(o): return json.dumps(o, sort_keys=True, default=str)

def join(results, how="first_ok", score=None):
    """-> {"ok", "output", "detail"}. vote: the most common verified output (ties: earliest). best: highest score(output) among verified outputs."""
    good = [r for r in results if r.ok]
    if how == "all": return {"ok": bool(good), "output": [r.output for r in good], "detail": f"{len(good)}/{len(results)} verified"}
    if not good: return {"ok": False, "output": None, "detail": "no verified answer: " + "; ".join(sum((r.problems[:1] for r in results), []))[:300]}
    if how == "first_ok": return {"ok": True, "output": good[0].output, "detail": f"{len(good)}/{len(results)} verified"}
    if how == "vote":
        c = Counter(_key(r.output) for r in good); top, n = c.most_common(1)[0]
        return {"ok": True, "output": next(r.output for r in good if _key(r.output) == top), "detail": f"{n} of {len(good)} verified answers agree"}
    if how == "merge": return {"ok": True, "output": "\n\n".join(o if isinstance(o, str) else _key(o) for o in (r.output for r in good)), "detail": f"merged {len(good)}"}
    if how == "best":
        if score is None: raise ValueError("how='best' needs a score(output) function")
        b = max(good, key=lambda r: score(r.output)); return {"ok": True, "output": b.output, "detail": f"best of {len(good)}, score {score(b.output):.3f}"}
    raise ValueError(f"unknown join '{how}'")
