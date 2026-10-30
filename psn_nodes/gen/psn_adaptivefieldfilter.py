"""PSN_AdaptiveFieldFilter -- pure-logic, secure-by-design part of the
"Adaptive Field Filtering by Intermittent Noise Enhancement" node.

The full node would apply a high-pass (Laplacian) filter to a LATENT tensor
to enhance detail. That requires torch/scipy and GPU access, which are OUT
of scope here. This module implements ONLY the safe, dependency-free logic:

  * config validation (strength / threshold / kernel_size / mode),
  * allow-list checks (mode must be in a fixed set),
  * filter-kernel construction (a separable high-pass / Laplacian kernel),
  * a "detail enhancement" estimate (Laplacian variance proxy) computed on a
    plain 2-D grid of numbers.

All functions and node wrappers take plain values (numbers, strings, JSON
text). No torch, no comfy imports, no network, no subprocess, no file/OS
access, no eval/exec, no dunder tricks.
"""

import json
import math

# --- safe helpers from the psn package (safe evaluator + gate/retry) -------
try:
    from psn import expr, orchestration as _orch
except Exception:  # pragma: no cover - psn may be absent in some sandboxes
    expr = None
    _orch = None

CAT = "ParametricStudio/Field"

# Allow-list of supported filter modes.
_MODES = ("laplacian", "highpass", "none")

# Hard bounds to keep the node secure-by-design (no runaway kernels).
_STRENGTH_MIN = 0.0
_STRENGTH_MAX = 10.0
_THRESHOLD_MIN = 0.0
_THRESHOLD_MAX = 1.0
_KERNEL_MIN = 3
_KERNEL_MAX = 15


def _is_number(value):
    """Return True if value is a real number (int/float, not bool)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return False


def _clamp(value, lo, hi):
    """Clamp a number into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def validate_config(strength, threshold, kernel_size, mode):
    """Validate and normalise the filter configuration.

    Returns a tuple ``(ok, config, reason)`` where ``config`` is a dict of
    clamped/normalised values when ``ok`` is True, otherwise ``config`` is
    None and ``reason`` explains the failure.
    """
    # mode must be in the allow-list (case-insensitive, stripped).
    if not isinstance(mode, str):
        return (False, None, "mode must be a string")
    mode_norm = mode.strip().lower()
    if mode_norm not in _MODES:
        return (False, None, "mode must be one of %s" % (", ".join(_MODES)))

    if not _is_number(strength):
        return (False, None, "strength must be a number")
    if not _is_number(threshold):
        return (False, None, "threshold must be a number")
    if not _is_number(kernel_size) or int(kernel_size) != kernel_size:
        return (False, None, "kernel_size must be an integer")

    strength = _clamp(float(strength), _STRENGTH_MIN, _STRENGTH_MAX)
    threshold = _clamp(float(threshold), _THRESHOLD_MIN, _THRESHOLD_MAX)
    kernel_size = int(_clamp(int(kernel_size), _KERNEL_MIN, _KERNEL_MAX))

    # Kernel must be odd for a symmetric Laplacian / high-pass.
    if kernel_size % 2 == 0:
        kernel_size += 1

    config = {
        "strength": strength,
        "threshold": threshold,
        "kernel_size": kernel_size,
        "mode": mode_norm,
    }
    return (True, config, "ok")


def build_kernel(kernel_size, mode):
    """Build a 2-D high-pass / Laplacian filter kernel.

    For ``mode == "laplacian"`` the kernel is the standard 4-neighbour
    Laplacian (centre +4, orthogonal neighbours -1, rest 0). For
    ``mode == "highpass"`` the kernel is a box high-pass (centre positive,
    surrounding ring negative) normalised so the sum is zero. For
    ``mode == "none"`` an identity (delta) kernel is returned.

    Returns a list-of-lists of floats.
    """
    n = int(kernel_size)
    half = n // 2
    kernel = [[0.0] * n for _ in range(n)]

    if mode == "none":
        kernel[half][half] = 1.0
        return kernel

    if mode == "laplacian":
        kernel[half][half] = 4.0
        if half - 1 >= 0:
            kernel[half - 1][half] = -1.0
        if half + 1 < n:
            kernel[half + 1][half] = -1.0
        if half - 1 >= 0:
            kernel[half][half - 1] = -1.0
        if half + 1 < n:
            kernel[half][half + 1] = -1.0
        return kernel

    # highpass: centre positive, ring negative, sum zero.
    centre = float(n * n - 1)
    kernel[half][half] = centre
    for r in range(n):
        for c in range(n):
            if r == half and c == half:
                continue
            kernel[r][c] = -1.0
    return kernel


def _apply_kernel(grid, kernel):
    """Apply a 2-D kernel to a grid using zero padding (pure Python)."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    k = len(kernel)
    half = k // 2
    out = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            acc = 0.0
            for kr in range(k):
                for kc in range(k):
                    rr = r + kr - half
                    cc = c + kc - half
                    if 0 <= rr < rows and 0 <= cc < cols:
                        acc += grid[rr][cc] * kernel[kr][kc]
            out[r][c] = acc
    return out


def _variance(values):
    """Population variance of a flat list of numbers."""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def detail_estimate(grid, kernel):
    """Estimate detail enhancement as the Laplacian (high-pass) variance.

    A higher value indicates more high-frequency detail. This is the pure
    proxy for the "Laplacian variance increase" smoke test.
    """
    filtered = _apply_kernel(grid, kernel)
    flat = [v for row in filtered for v in row]
    return _variance(flat)


def parse_json_config(text):
    """Parse a JSON text config and validate it.

    Returns ``(ok, config, reason)``.
    """
    if not isinstance(text, str):
        return (False, None, "config text must be a string")
    try:
        data = json.loads(text)
    except Exception as exc:
        return (False, None, "invalid JSON: %s" % exc)
    if not isinstance(data, dict):
        return (False, None, "config JSON must be an object")
    strength = data.get("strength", 1.0)
    threshold = data.get("threshold", 0.5)
    kernel_size = data.get("kernel_size", 3)
    mode = data.get("mode", "laplacian")
    return validate_config(strength, threshold, kernel_size, mode)


class PSN_AdaptiveFieldFilter:
    """Validates an Adaptive Field Filter config and builds its kernel.

    Pure-logic node: takes plain numbers/strings/JSON text and returns a
    validated config, the constructed filter kernel (as JSON text), and a
    detail-enhancement estimate. No GPU/torch/ComfyUI internals are used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "strength": ("FLOAT", {"default": 1.0, "min": _STRENGTH_MIN,
                                       "max": _STRENGTH_MAX, "step": 0.01}),
                "threshold": ("FLOAT", {"default": 0.5, "min": _THRESHOLD_MIN,
                                        "max": _THRESHOLD_MAX, "step": 0.01}),
                "kernel_size": ("INT", {"default": 3, "min": _KERNEL_MIN,
                                        "max": _KERNEL_MAX, "step": 1}),
                "mode": (list(_MODES),),
            },
            "optional": {
                "config_json": ("STRING", {"default": ""}),
                "grid_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("valid", "config_json", "kernel_json", "detail_estimate")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, strength, threshold, kernel_size, mode,
            config_json="", grid_json=""):
        # If a JSON config is supplied, prefer it (it overrides the scalars).
        if config_json and config_json.strip():
            ok, config, reason = parse_json_config(config_json)
        else:
            ok, config, reason = validate_config(
                strength, threshold, kernel_size, mode)

        if not ok:
            return (False, json.dumps({"error": reason}), "null", 0.0)

        kernel = build_kernel(config["kernel_size"], config["mode"])

        detail = 0.0
        if grid_json and grid_json.strip():
            try:
                grid = json.loads(grid_json)
                if (isinstance(grid, list) and grid
                        and all(isinstance(row, list) for row in grid)):
                    detail = detail_estimate(grid, kernel)
            except Exception:
                detail = 0.0

        return (True, json.dumps(config), json.dumps(kernel), detail)


NODE_CLASS_MAPPINGS = {
    "PSN_AdaptiveFieldFilter": PSN_AdaptiveFieldFilter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_AdaptiveFieldFilter": "PSN Adaptive Field Filter",
}
