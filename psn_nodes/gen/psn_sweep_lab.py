"""PSN Sweep Lab (pure-logic core).

This module implements the *planning, validation, and analysis* logic for
automated XY(Z) parameter sweeps (schedulers / step counts / cfg) used to
build comparison grids for the ComfyUI School curriculum.

Because the real sweep requires GPU/torch/ComfyUI internals (running the
sampler, rendering images, computing SSIM/LPIPS), this module implements ONLY
the pure-logic, secure-by-design part:

  * parsing and validating the comma-separated value list (allow-listed
    parameter names, integer/float coercion, max-10 cap, no duplicates);
  * building the grid layout (rows x cols) for a given number of values;
  * formatting the per-cell labels and the human-readable score table;
  * selecting the best value from a numeric score table (max or min metric).

All functions and node wrappers take plain values (numbers, strings, JSON
text) and return plain values. No torch, no ComfyUI, no network, no file or
OS access, no eval/exec, no dunder tricks. The actual image grid and metric
computation are left to the GPU side; here we only produce the plan and the
analysis of already-computed scores.
"""

import json
import math

try:
    from psn import expr, orchestration
except Exception:  # pragma: no cover - optional helpers
    expr = None
    orchestration = None

CAT = "ParametricStudio/Sweep"

# Allow-listed parameter names (spec: steps, cfg, sampler).
PARAM_NAMES = ("steps", "cfg", "sampler")

# Allow-listed metrics (spec: ssim, lpips).
METRICS = ("ssim", "lpips")

# Hard cap on the number of sweep values (risk mitigation).
MAX_VALUES = 10

# Hard cap on grid cells (defensive; MAX_VALUES already bounds this).
MAX_CELLS = 10


def _is_number(value):
    """Return True if value is a real number (int/float, not bool, not NaN)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isnan(value)
    return False


def parse_values(raw, param_name):
    """Parse a comma-separated value string into a validated list.

    Returns (values, error). On success error is None and values is a list of
    ints (for 'steps') or floats (for 'cfg') or strings (for 'sampler').
    On failure values is None and error is a human-readable reason.
    """
    if param_name not in PARAM_NAMES:
        return None, "param_name must be one of %s" % (", ".join(PARAM_NAMES))

    if raw is None:
        return None, "values must be a non-empty string"

    if not isinstance(raw, str):
        return None, "values must be a comma-separated string"

    stripped = raw.strip()
    if stripped == "":
        return None, "values must be a non-empty string"

    parts = [p.strip() for p in stripped.split(",")]
    parts = [p for p in parts if p != ""]
    if not parts:
        return None, "values must contain at least one value"

    if len(parts) > MAX_VALUES:
        return None, "too many values (max %d)" % MAX_VALUES

    seen = set()
    out = []
    for p in parts:
        if param_name == "sampler":
            token = p
            if token == "":
                return None, "empty sampler name"
            if token in seen:
                return None, "duplicate value: %s" % token
            seen.add(token)
            out.append(token)
            continue

        # Numeric parameter: steps (int) or cfg (float).
        try:
            if param_name == "steps":
                num = int(p)
            else:
                num = float(p)
        except (ValueError, TypeError):
            return None, "invalid %s value: %s" % (param_name, p)

        if param_name == "steps":
            if num < 1:
                return None, "steps must be >= 1 (got %d)" % num
        else:
            if math.isnan(num) or math.isinf(num):
                return None, "cfg must be finite (got %s)" % p
            if num < 0:
                return None, "cfg must be >= 0 (got %s)" % p

        key = num
        if key in seen:
            return None, "duplicate value: %s" % p
        seen.add(key)
        out.append(num)

    return out, None


def grid_layout(count):
    """Return (rows, cols) for a grid holding `count` cells.

    Uses a near-square layout: cols = ceil(sqrt(count)), rows = ceil(count/cols).
    """
    if count <= 0:
        return (0, 0)
    cols = int(math.ceil(math.sqrt(count)))
    rows = int(math.ceil(count / cols))
    return (rows, cols)


def build_labels(values):
    """Return a list of per-cell label strings, one per value."""
    return [str(v) for v in values]


def format_score_table(values, scores, metric):
    """Return a human-readable score table string.

    `values` and `scores` must be the same length. `metric` is one of METRICS.
    """
    if metric not in METRICS:
        return "error: metric must be one of %s" % (", ".join(METRICS))
    if len(values) != len(scores):
        return "error: values and scores length mismatch"
    lines = ["%s score table" % metric]
    for v, s in zip(values, scores):
        lines.append("%s: %s" % (v, s))
    return "\n".join(lines)


def select_best(values, scores, metric):
    """Return (best_value, best_score, error).

    For 'ssim' higher is better; for 'lpips' lower is better.
    """
    if metric not in METRICS:
        return None, None, "metric must be one of %s" % (", ".join(METRICS))
    if len(values) != len(scores):
        return None, None, "values and scores length mismatch"
    if len(values) == 0:
        return None, None, "no values to analyze"

    for s in scores:
        if not _is_number(s):
            return None, None, "scores must be numeric"

    if metric == "ssim":
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
    else:
        best_idx = min(range(len(scores)), key=lambda i: scores[i])

    return values[best_idx], scores[best_idx], None


class PSN_Sweep_Config:
    """Plan an XY(Z) parameter sweep.

    Pure-logic node: validates the parameter name and the comma-separated value
    list, builds the grid layout and per-cell labels, and emits a JSON plan that
    the GPU side can use to actually run the sampler and render the grid.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "param_name": (list(PARAM_NAMES),),
                "values": ("STRING", {"default": "10,20,30", "multiline": False}),
            },
            "optional": {
                "max_values": ("INT", {"default": MAX_VALUES, "min": 1, "max": MAX_VALUES, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "BOOLEAN")
    RETURN_NAMES = ("plan_json", "labels", "rows", "cols", "valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, param_name, values, max_values=MAX_VALUES):
        # Enforce the hard cap regardless of the optional knob.
        cap = min(int(max_values), MAX_VALUES)
        parsed, err = parse_values(values, param_name)
        if err is not None:
            plan = json.dumps({"ok": False, "error": err})
            return (plan, "", 0, 0, False)

        if len(parsed) > cap:
            plan = json.dumps({"ok": False, "error": "too many values (max %d)" % cap})
            return (plan, "", 0, 0, False)

        rows, cols = grid_layout(len(parsed))
        labels = build_labels(parsed)
        plan = json.dumps({
            "ok": True,
            "param_name": param_name,
            "values": parsed,
            "rows": rows,
            "cols": cols,
            "labels": labels,
        })
        return (plan, ", ".join(labels), rows, cols, True)


class PSN_Sweep_Analyzer:
    """Analyze already-computed sweep scores and pick the best value.

    Pure-logic node: takes the value list (as a comma-separated string) and the
    numeric scores (as a JSON array string), validates them, formats a score
    table, and selects the best value for the chosen metric.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "values": ("STRING", {"default": "10,20,30", "multiline": False}),
                "scores": ("STRING", {"default": "[0.5, 0.7, 0.6]", "multiline": False}),
                "metric": (list(METRICS),),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("best_value", "score_table", "best_score", "valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, values, scores, metric):
        # Parse the value list (treat as generic tokens; param name unknown here).
        if not isinstance(values, str) or values.strip() == "":
            return ("", "error: values must be a non-empty string", 0.0, False)
        val_tokens = [t.strip() for t in values.split(",") if t.strip() != ""]
        if not val_tokens:
            return ("", "error: values must be a non-empty string", 0.0, False)

        # Parse the scores JSON array.
        try:
            score_list = json.loads(scores)
        except (ValueError, TypeError):
            return ("", "error: scores must be a JSON array of numbers", 0.0, False)
        if not isinstance(score_list, list):
            return ("", "error: scores must be a JSON array of numbers", 0.0, False)

        if len(val_tokens) != len(score_list):
            return ("", "error: values and scores length mismatch", 0.0, False)

        best_value, best_score, err = select_best(val_tokens, score_list, metric)
        if err is not None:
            return ("", "error: %s" % err, 0.0, False)

        table = format_score_table(val_tokens, score_list, metric)
        return (str(best_value), table, float(best_score), True)


NODE_CLASS_MAPPINGS = {
    "PSN_Sweep_Config": PSN_Sweep_Config,
    "PSN_Sweep_Analyzer": PSN_Sweep_Analyzer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Sweep_Config": "PSN Sweep Config",
    "PSN_Sweep_Analyzer": "PSN Sweep Analyzer",
}
