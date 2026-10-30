"""PSN Debug Peek: pure-logic planning and layout helpers for latent-peek sampling.

This module implements ONLY the secure, pure-logic parts of the "Debug Peek"
feature. It does NOT import torch, comfy, or any GPU/ComfyUI internals, and it
performs no file, network, or subprocess I/O.

The real sampler/VAE-decode work happens inside ComfyUI; these nodes instead:
  * validate and normalize the comma-separated ``peek_steps`` string,
  * compute the ordered list of steps at which a latent should be decoded,
  * build a deterministic "peek plan" (which step, which index, enabled flag),
  * compute the grid layout (rows/cols) for arranging peeked images.

All functions take plain values (ints, floats, strings) and return plain
values (tuples of ints/bools/strings). The ComfyUI-facing node classes wrap
these helpers so they can be dropped into a workflow; the heavy lifting
(sampling, VAE decode, image compositing) is intentionally out of scope here.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Debug"

# Allowed sampler / scheduler names (allow-list; keeps the node safe-by-design).
SAMPLER_NAMES = ("euler", "euler_ancestral", "heun", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_3m_sde")
SCHEDULERS = ("normal", "karras", "exponential", "sgm_uniform", "simple")

# Hard bounds for the planning logic.
MAX_STEPS = 10000
MAX_PEEKS = 64


def _parse_peek_steps(peek_steps, total_steps):
    """Parse a comma-separated string of step indices into a validated list.

    Returns (steps_list, error_string). ``steps_list`` is a sorted, de-duplicated
    list of ints in the range [1, total_steps]. ``error_string`` is "" on success.
    """
    if total_steps is None:
        return [], "total_steps must be a positive integer"
    try:
        total = int(total_steps)
    except (TypeError, ValueError):
        return [], "total_steps must be an integer"
    if total <= 0:
        return [], "total_steps must be a positive integer"

    if peek_steps is None:
        return [], ""
    if not isinstance(peek_steps, str):
        return [], "peek_steps must be a comma-separated string"

    raw = peek_steps.strip()
    if raw == "":
        return [], ""

    seen = set()
    out = []
    for part in raw.split(","):
        token = part.strip()
        if token == "":
            continue
        try:
            val = int(token)
        except ValueError:
            return [], "peek_steps contains a non-integer token: %r" % token
        if val < 1 or val > total:
            return [], "peek step %d out of range [1, %d]" % (val, total)
        if val not in seen:
            seen.add(val)
            out.append(val)

    out.sort()
    if len(out) > MAX_PEEKS:
        return [], "too many peek steps (max %d)" % MAX_PEEKS
    return out, ""


def build_peek_plan(peek_steps, total_steps, enabled=True):
    """Build the ordered peek plan.

    Returns a tuple:
      (steps_list, indices_list, enabled_bool, error_string)
    where ``indices_list`` is the 0-based position of each peek within the plan.
    """
    steps, err = _parse_peek_steps(peek_steps, total_steps)
    if err:
        return [], [], False, err
    indices = list(range(len(steps)))
    return steps, indices, bool(enabled), ""


def grid_layout(count):
    """Compute a grid layout for ``count`` images.

    Returns (rows, cols). Uses the smallest number of rows such that the grid
    is at least as wide as it is tall (landscape bias), with a single row for
    small counts.
    """
    if count is None:
        return 1, 0
    try:
        n = int(count)
    except (TypeError, ValueError):
        return 1, 0
    if n <= 0:
        return 1, 0
    if n == 1:
        return 1, 1
    # Choose cols = ceil(sqrt(n)) then rows = ceil(n / cols).
    cols = 1
    while cols * cols < n:
        cols += 1
    rows = (n + cols - 1) // cols
    return rows, cols


class PSN_Peek_Plan:
    """Plan which sampling steps to peek at. Pure logic, no GPU work."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": MAX_STEPS, "step": 1}),
                "peek_steps": ("STRING", {"default": "1,5,10", "multiline": False}),
                "enabled": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "sampler_name": (list(SAMPLER_NAMES),),
                "scheduler": (list(SCHEDULERS),),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 63 - 1, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("peek_count", "total_steps", "enabled", "plan_summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, steps, peek_steps, enabled, sampler_name="euler", scheduler="normal", cfg=7.0, seed=0):
        plan_steps, indices, is_enabled, err = build_peek_plan(peek_steps, steps, enabled)
        if err:
            summary = "ERROR: " + err
            return (0, int(steps), False, summary)
        summary = "steps=%d peeks=%s enabled=%s sampler=%s scheduler=%s cfg=%.2f seed=%d" % (
            int(steps),
            ",".join(str(s) for s in plan_steps) if plan_steps else "none",
            str(is_enabled).lower(),
            sampler_name,
            scheduler,
            float(cfg),
            int(seed),
        )
        return (len(plan_steps), int(steps), is_enabled, summary)


class PSN_Peek_Grid:
    """Compute the grid layout for arranging peeked images. Pure logic."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "peek_count": ("INT", {"default": 3, "min": 0, "max": MAX_PEEKS, "step": 1}),
            },
            "optional": {
                "max_cols": ("INT", {"default": 0, "min": 0, "max": MAX_PEEKS, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("rows", "cols", "layout_summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, peek_count, max_cols=0):
        rows, cols = grid_layout(peek_count)
        if max_cols and max_cols > 0 and cols > max_cols:
            cols = max_cols
            rows = (int(peek_count) + cols - 1) // cols if int(peek_count) > 0 else 1
        summary = "count=%d rows=%d cols=%d" % (int(peek_count), rows, cols)
        return (rows, cols, summary)


NODE_CLASS_MAPPINGS = {
    "PSN_Peek_Plan": PSN_Peek_Plan,
    "PSN_Peek_Grid": PSN_Peek_Grid,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Peek_Plan": "PSN Peek Plan",
    "PSN_Peek_Grid": "PSN Peek Grid",
}
