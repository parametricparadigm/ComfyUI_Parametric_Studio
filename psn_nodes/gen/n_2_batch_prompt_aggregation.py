"""ParametricStudio - Batch Prompt Aggregation.

Two small nodes that implement a prompt-batch loop without any external
services:

* PSN_Batch_Prompt_Loop  - pulls the next prompt out of a list and advances
  the loop index stored in a context dict.
* PSN_Accumulate_Json    - appends a generated image path to a JSON list
  stored in the context dict.

The context (``PSN_CTX``) is a plain Python dict that travels through the
workflow.  It is always copied before being returned so upstream nodes are
never mutated in place.

Only the stdlib ``json`` module is used for (de)serialization; no network,
subprocess or file access is performed here.  The actual image generation
and path capture are done by other nodes in the workflow; this module only
handles the bookkeeping.
"""

import json

CAT = "ParametricStudio/Batch"

# ComfyUI has no native "context" type; we use a dict and advertise it as
# PSN_CTX so the UI shows a distinct widget.  The dict is expected to have
# the keys:
#   "prompts" : list[str]   (optional, used by the loop node)
#   "index"   : int         (loop position, 0-based)
#   "paths"   : list[str]   (accumulated output paths)
#   "done"    : bool        (loop finished flag)

CTX = ("PSN_CTX",)


def _new_ctx(prompts=None):
    """Return a fresh, empty context dict."""
    return {
        "prompts": list(prompts) if prompts is not None else [],
        "index": 0,
        "paths": [],
        "done": False,
    }


def _copy_ctx(ctx):
    """Shallow-copy a context dict, normalising missing keys.

    Never mutates the input.  Returns a new dict.
    """
    if not isinstance(ctx, dict):
        # Bad input: treat as a fresh context.
        return _new_ctx()
    out = {
        "prompts": list(ctx.get("prompts", [])),
        "index": int(ctx.get("index", 0)),
        "paths": list(ctx.get("paths", [])),
        "done": bool(ctx.get("done", False)),
    }
    return out


class PSN_Batch_Prompt_Loop:
    """Extract the next prompt from a list and update the loop context.

    On the first call (index == 0) it returns the first prompt and sets
    index to 1.  Subsequent calls return the next prompt.  When the index
    reaches the end of the list, ``done`` is set to True and the returned
    prompt is an empty string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {"multiline": True, "default": ""}),
                "loop_ctx": CTX,
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "PSN_CTX")
    RETURN_NAMES = ("current_prompt", "updated_ctx")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompts, loop_ctx):
        ctx = _copy_ctx(loop_ctx)

        # If the caller supplied a prompt string (multiline), parse it as a
        # list of prompts (one per line) when the context has no prompts yet.
        if not ctx["prompts"] and isinstance(prompts, str) and prompts.strip():
            ctx["prompts"] = [ln.strip() for ln in prompts.splitlines() if ln.strip()]

        n = len(ctx["prompts"])
        if ctx["index"] >= n:
            ctx["done"] = True
            return ("", ctx)

        current = ctx["prompts"][ctx["index"]]
        ctx["index"] += 1
        if ctx["index"] >= n:
            ctx["done"] = True
        return (str(current), ctx)


class PSN_Accumulate_Json:
    """Append a generated image path to the JSON list in the context.

    The path is stored as a plain string.  ``json.dumps`` is used to verify
    that the value is serialisable (paths with special characters are
    handled by JSON escaping).  The context is returned as a new dict.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "item": ("STRING", {"default": ""}),
                "ctx": CTX,
            },
            "optional": {},
        }

    RETURN_TYPES = ("PSN_CTX", "STRING")
    RETURN_NAMES = ("updated_ctx", "json_list")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, item, ctx):
        c = _copy_ctx(ctx)
        if not isinstance(item, str):
            # Bad input: coerce to string so JSON stays valid.
            item = str(item)
        c["paths"].append(item)
        # Verify serialisability; json.dumps raises on non-serialisable
        # values, but a plain string is always fine.  We keep the result so
        # the node can also expose the current JSON list as a string.
        json_list = json.dumps(c["paths"], ensure_ascii=False)
        return (c, json_list)


NODE_CLASS_MAPPINGS = {
    "PSN_Batch_Prompt_Loop": PSN_Batch_Prompt_Loop,
    "PSN_Accumulate_Json": PSN_Accumulate_Json,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Batch_Prompt_Loop": "Batch Prompt Loop",
    "PSN_Accumulate_Json": "Accumulate JSON",
}
