"""ComfyUI nodes for subagents (original). Logic lives in psn/subagents/: roles (what each job is and how its output is checked), runner (budgeted verified loop), fanout (parallel + join)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn.subagents import ROLES, run_subagent, fan_out
from psn.subagents.fanout import join as join_results

CAT = "ParametricStudio/Subagents"
PRIMARY = ("text", "summary", "prompt", "caption", "label", "role", "action")   # the field shown as plain text when a role's answer has one

def _ctx(context_json):
    try: c = json.loads(context_json) if (context_json or "").strip() else {}
    except json.JSONDecodeError as e: raise ValueError(f"context_json is not valid JSON: {e}")
    if not isinstance(c, dict): raise ValueError("context_json must be a JSON object")
    return c

def _as_text(out):
    if isinstance(out, dict):
        for k in PRIMARY:
            if isinstance(out.get(k), str): return out[k]
    return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)

def _save_image(image):
    import numpy as np
    from PIL import Image
    arr = (image[0].cpu().numpy().clip(0, 1) * 255).astype("uint8"); fd, p = tempfile.mkstemp(suffix=".png", prefix="psn_sub_"); os.close(fd)
    Image.fromarray(arr).save(p); return p

class PSN_Subagent:
    """Run one verified subagent. Each role has its own output contract, tools and checker: the answer only comes out as ok=true when the checker found no problems
    (quotes exist in the source, graphs validate, code passes its tests ...). Put what the checker needs in context_json (e.g. {"source": "...", "labels": [...]})."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"role": (list(ROLES),), "task": ("STRING", {"multiline": True, "default": ""})},
                "optional": {"context_json": ("STRING", {"multiline": True, "default": "{}"}), "endpoint": ("STRING", {"default": ""}), "max_attempts": ("INT", {"default": 3, "min": 1, "max": 6}),
                             "max_seconds": ("INT", {"default": 300, "min": 10, "max": 3600}), "image": ("IMAGE",)}}
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING", "STRING"); RETURN_NAMES = ("text", "output_json", "ok", "problems", "report_json"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, role, task, context_json="{}", endpoint="", max_attempts=3, max_seconds=300, image=None):
        ctx = _ctx(context_json)
        if image is not None: ctx["image_path"] = _save_image(image)
        try: r = run_subagent(role, task, ctx, endpoint=endpoint or None, max_attempts=max_attempts, max_seconds=max_seconds)
        finally:
            if image is not None and ctx.get("image_path"):
                try: os.remove(ctx["image_path"])
                except OSError: pass
        return (_as_text(r.output) if r.ok else "", json.dumps(r.output, ensure_ascii=False, default=str), r.ok, "\n".join(r.problems), json.dumps({k: v for k, v in r.as_dict().items() if k != "output"}))

class PSN_SubagentFanOut:
    """Run the same role on many tasks at once (one task per line, or a JSON list) and join the verified answers: first_ok, vote, all, or merge."""
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"role": (list(ROLES),), "tasks": ("STRING", {"multiline": True, "default": ""}), "join": (["first_ok", "vote", "merge", "all"],)},
                "optional": {"context_json": ("STRING", {"multiline": True, "default": "{}"}), "max_parallel": ("INT", {"default": 4, "min": 1, "max": 16}), "endpoint": ("STRING", {"default": ""})}}
    RETURN_TYPES = ("STRING", "STRING", "INT", "BOOLEAN"); RETURN_NAMES = ("joined_text", "result_json", "verified_count", "ok"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, role, tasks, join="first_ok", context_json="{}", max_parallel=4, endpoint=""):
        ctx = _ctx(context_json); t = tasks.strip()
        items = json.loads(t) if t.startswith("[") else [x for x in (ln.strip() for ln in t.splitlines()) if x]
        if not items: raise ValueError("no tasks given")
        rs = fan_out([{"role": role, "task": str(x), "ctx": ctx} for x in items], max_workers=max_parallel, endpoint=endpoint or None)
        j = join_results(rs, join)
        return (_as_text(j["output"]) if j["ok"] else "", json.dumps({"detail": j["detail"], "results": [r.as_dict() for r in rs]}, default=str), sum(r.ok for r in rs), j["ok"])

NODE_CLASS_MAPPINGS = {"PSN_Subagent": PSN_Subagent, "PSN_SubagentFanOut": PSN_SubagentFanOut}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Subagent": "PSN Subagent (verified)", "PSN_SubagentFanOut": "PSN Subagent Fan-Out"}
