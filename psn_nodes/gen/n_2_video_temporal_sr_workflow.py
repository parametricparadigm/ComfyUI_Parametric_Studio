"""PSN Video Temporal SR Workflow (pure-logic, secure-by-design).

This module implements the *planning / validation* half of a recurrent
video super-resolution (BasicVSR++ style) workflow.  The actual neural
network inference requires ``torch``/``torchvision`` and the iSeeBetter
BasicVSR++ weights, which are intentionally NOT imported here.  Instead this
node validates the configuration, computes the per-frame upscaling plan
(temporal windowing, output resolution, VRAM budget) and returns a plain
Python "plan" that a GPU-side executor can consume.

The node therefore takes plain values (numbers, strings) and returns plain
values (numbers, strings, JSON text).  It never opens a socket, never touches
the filesystem, and never imports torch/comfy.
"""

import json
import math

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Video"

# Allow-list of known BasicVSR++ style model identifiers.
_MODEL_ALLOWLIST = (
    "iseebetter_basicvsr_plus",
    "iseebetter_basicvsr_plus_fp16",
    "basicvsr_plus_x2",
    "basicvsr_plus_x3",
    "basicvsr_plus_x4",
)

# Supported integer upscaling factors.
_SCALE_CHOICES = (1, 2, 3, 4)

# Hard bounds for the temporal window (frames processed per recurrent pass).
_WINDOW_MIN = 1
_WINDOW_MAX = 32

# Rough VRAM estimate (in MB) per frame at 1x resolution, used only to
# produce a *warning* string.  Not a real measurement.
_VRAM_PER_FRAME_MB = 128.0


def _validate_model(model_path):
    """Return (ok, reason).  Model must be a non-empty string in the allow-list."""
    if not isinstance(model_path, str):
        return False, "MODEL_PATH must be a string"
    if not model_path.strip():
        return False, "MODEL_PATH must not be empty"
    if model_path not in _MODEL_ALLOWLIST:
        return False, "MODEL_PATH '%s' is not in the allow-list %s" % (
            model_path, list(_MODEL_ALLOWLIST))
    return True, "ok"


def _validate_scale(scale):
    """Return (ok, reason).  Scale must be an int in _SCALE_CHOICES."""
    if isinstance(scale, bool):
        return False, "SCALE must be an integer, not a bool"
    if not isinstance(scale, int):
        return False, "SCALE must be an integer"
    if scale not in _SCALE_CHOICES:
        return False, "SCALE must be one of %s" % (list(_SCALE_CHOICES),)
    return True, "ok"


def _validate_window(window):
    """Return (ok, reason).  Window must be an int in [WINDOW_MIN, WINDOW_MAX]."""
    if isinstance(window, bool):
        return False, "TEMPORAL_WINDOW must be an integer, not a bool"
    if not isinstance(window, int):
        return False, "TEMPORAL_WINDOW must be an integer"
    if window < _WINDOW_MIN or window > _WINDOW_MAX:
        return False, "TEMPORAL_WINDOW must be between %d and %d" % (
            _WINDOW_MIN, _WINDOW_MAX)
    return True, "ok"


def _build_plan(num_frames, in_w, in_h, scale, window, model_path):
    """Compute the per-frame upscaling plan as a dict.

    Returns a dict with keys:
      num_frames, in_w, in_h, out_w, out_h, scale, window,
      num_windows, frames_per_window, vram_estimate_mb, warnings
    """
    out_w = in_w * scale
    out_h = in_h * scale
    num_windows = math.ceil(num_frames / window) if window > 0 else 0
    frames_per_window = window
    # Rough VRAM estimate: per-frame cost scales with output resolution.
    res_factor = (out_w * out_h) / (256.0 * 256.0)
    vram_estimate_mb = _VRAM_PER_FRAME_MB * res_factor * window

    warnings = []
    if vram_estimate_mb > 4096.0:
        warnings.append(
            "Estimated VRAM %.0f MB exceeds 4 GB; consider reducing "
            "TEMPORAL_WINDOW or using an FP16 model." % vram_estimate_mb)
    if num_frames == 0:
        warnings.append("Empty frame batch; no frames to process.")

    return {
        "num_frames": num_frames,
        "in_w": in_w,
        "in_h": in_h,
        "out_w": out_w,
        "out_h": out_h,
        "scale": scale,
        "window": window,
        "num_windows": num_windows,
        "frames_per_window": frames_per_window,
        "vram_estimate_mb": round(vram_estimate_mb, 2),
        "warnings": warnings,
    }


class PSN_Video_Temporal_SR:
    """Plan a recurrent (BasicVSR++ style) video super-resolution pass.

    Validates model / scale / temporal-window parameters, computes the
    output resolution and a per-window processing plan, and returns a JSON
    plan string plus a human-readable status.  The actual tensor upscaling
    is performed by a separate GPU-side executor that consumes this plan.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "num_frames": ("INT", {"default": 16, "min": 0, "max": 1024, "step": 1}),
                "in_width": ("INT", {"default": 256, "min": 1, "max": 8192, "step": 1}),
                "in_height": ("INT", {"default": 256, "min": 1, "max": 8192, "step": 1}),
                "MODEL_PATH": (list(_MODEL_ALLOWLIST),),
                "SCALE": (list(_SCALE_CHOICES),),
                "TEMPORAL_WINDOW": ("INT", {"default": 5, "min": _WINDOW_MIN, "max": _WINDOW_MAX, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("plan_json", "status", "out_width", "out_height", "num_windows", "vram_estimate_mb")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, num_frames, in_width, in_height, MODEL_PATH, SCALE, TEMPORAL_WINDOW):
        # --- validate model ---
        ok, why = _validate_model(MODEL_PATH)
        if not ok:
            return ("{}", "ERROR: " + why, 0, 0, 0, 0)

        # --- validate scale ---
        ok, why = _validate_scale(SCALE)
        if not ok:
            return ("{}", "ERROR: " + why, 0, 0, 0, 0)

        # --- validate temporal window ---
        ok, why = _validate_window(TEMPORAL_WINDOW)
        if not ok:
            return ("{}", "ERROR: " + why, 0, 0, 0, 0)

        # --- validate frame / resolution bounds ---
        if num_frames < 0:
            return ("{}", "ERROR: num_frames must be >= 0", 0, 0, 0, 0)
        if in_width < 1 or in_height < 1:
            return ("{}", "ERROR: in_width and in_height must be >= 1", 0, 0, 0, 0)

        plan = _build_plan(num_frames, in_width, in_height, SCALE, TEMPORAL_WINDOW, MODEL_PATH)
        plan_json = json.dumps(plan, sort_keys=True)
        status = "OK"
        if plan["warnings"]:
            status = "OK (warnings: " + "; ".join(plan["warnings"]) + ")"

        return (
            plan_json,
            status,
            plan["out_w"],
            plan["out_h"],
            plan["num_windows"],
            int(plan["vram_estimate_mb"]),
        )


NODE_CLASS_MAPPINGS = {
    "PSN_Video_Temporal_SR": PSN_Video_Temporal_SR,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Temporal_SR": "Video Temporal SR Workflow (Plan)",
}
