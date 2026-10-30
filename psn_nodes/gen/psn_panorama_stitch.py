"""PSN_Panorama_Stitch: pure-logic planning for equirectangular 360-degree panorama stitching.

This module implements ONLY the secure, pure-logic part of the panorama stitch spec.
It does NOT perform GPU/torch warping, interpolation, or any image pixel math, and it
performs no network, file, or OS access. Instead it:

  * validates the stitch configuration (frame count, field of view, overlap ratio),
  * computes the uniform angular step between frames,
  * plans the equirectangular output canvas (2:1 aspect) and per-frame angular coverage,
  * builds feathered (linear) blend weights for the overlapping regions,
  * reports a seam-risk assessment based on the overlap ratio.

All functions take plain values (numbers, strings, JSON text) and return plain values
(numbers, strings, lists, dicts). The ComfyUI node wrapper (``PSN_Panorama_Stitch``)
accepts plain numbers and returns the computed plan as structured values plus a JSON
summary string, so it can be wired into a ComfyUI graph without any heavy dependency.
"""

import json
import math

try:  # optional safe helpers; fall back to local implementations if unavailable
    from psn import expr as _expr
    from psn import orchestration as _orch
except Exception:  # pragma: no cover - dependency optional
    _expr = None
    _orch = None

CAT = "ParametricStudio/Panorama"

# Allow-list of blend modes the planner understands.
BLEND_MODES = ("feather", "constant", "none")

# Allow-list of projection targets.
PROJECTIONS = ("equirectangular", "cylindrical")

# Sensible bounds for the numeric inputs.
FOV_MIN = 1.0
FOV_MAX = 360.0
OVERLAP_MIN = 0.0
OVERLAP_MAX = 0.99
FRAMES_MIN = 1
FRAMES_MAX = 1024
# Below this overlap ratio the planner flags a seam risk.
SEAM_RISK_OVERLAP = 0.15


def _clamp(value, lo, hi):
    """Clamp ``value`` into the inclusive range ``[lo, hi]``."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _is_number(value):
    """Return True for real numbers, excluding booleans (which are ints in Python)."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def validate_panorama_config(num_frames, fov, overlap, projection="equirectangular",
                             blend_mode="feather"):
    """Validate a panorama stitch configuration.

    Returns a tuple ``(ok, errors, warnings)`` where ``errors`` and ``warnings`` are
    lists of human-readable strings. ``ok`` is True only when there are no errors.
    """
    errors = []
    warnings = []

    if not _is_number(num_frames):
        errors.append("num_frames must be a number")
    else:
        if not float(num_frames).is_integer():
            errors.append("num_frames must be an integer")
        elif not (FRAMES_MIN <= num_frames <= FRAMES_MAX):
            errors.append(
                "num_frames must be between %d and %d" % (FRAMES_MIN, FRAMES_MAX))

    if not _is_number(fov):
        errors.append("fov must be a number")
    elif not (FOV_MIN <= fov <= FOV_MAX):
        errors.append("fov must be between %g and %g degrees" % (FOV_MIN, FOV_MAX))

    if not _is_number(overlap):
        errors.append("overlap must be a number")
    elif not (OVERLAP_MIN <= overlap <= OVERLAP_MAX):
        errors.append("overlap must be between %g and %g" % (OVERLAP_MIN, OVERLAP_MAX))

    if projection not in PROJECTIONS:
        errors.append("projection must be one of %s" % (", ".join(PROJECTIONS)))

    if blend_mode not in BLEND_MODES:
        errors.append("blend_mode must be one of %s" % (", ".join(BLEND_MODES)))

    # Cross-field warnings (only when the relevant fields are valid numbers).
    if _is_number(num_frames) and _is_number(fov) and _is_number(overlap):
        if num_frames > 1:
            step = _angular_step(fov, overlap, num_frames)
            if step <= 0:
                warnings.append("computed angular step is non-positive; frames do not advance")
            if overlap < SEAM_RISK_OVERLAP:
                warnings.append(
                    "overlap below %g may produce visible seams" % SEAM_RISK_OVERLAP)
            if fov * num_frames > 360.0 * 1.5:
                warnings.append("total coverage exceeds 1.5 turns; frames wrap around")

    return (len(errors) == 0, errors, warnings)


def _angular_step(fov, overlap, num_frames):
    """Uniform angular step (degrees) between consecutive frames.

    With ``overlap`` as a fraction of the field of view, each new frame advances by
    ``fov * (1 - overlap)``. For a single frame the step is the full fov.
    """
    if num_frames <= 1:
        return float(fov)
    return float(fov) * (1.0 - float(overlap))


def plan_panorama(num_frames, fov, overlap, projection="equirectangular",
                  blend_mode="feather", out_width=2048, out_height=1024):
    """Build a pure-logic stitch plan for an equirectangular panorama.

    Returns a dict describing the output canvas, per-frame angular coverage, the
    uniform step, and the feathered blend weights for each frame. All values are plain
    Python numbers/strings/lists/dicts.
    """
    ok, errors, warnings = validate_panorama_config(
        num_frames, fov, overlap, projection, blend_mode)
    if not ok:
        raise ValueError("; ".join(errors))

    num_frames = int(num_frames)
    fov = float(fov)
    overlap = float(overlap)

    step = _angular_step(fov, overlap, num_frames)

    # Equirectangular canvas keeps a 2:1 aspect ratio.
    out_width = int(out_width)
    out_height = int(out_height)
    if out_height <= 0:
        out_height = 1
    if out_width <= 0:
        out_width = 2 * out_height

    # Per-frame angular coverage in the output space.
    frames = []
    for i in range(num_frames):
        start = i * step
        end = start + fov
        frames.append({
            "index": i,
            "start_deg": start,
            "end_deg": end,
            "center_deg": start + fov / 2.0,
        })

    # Feathered blend weights per frame (linear ramp across the overlap).
    weights = _feather_weights(num_frames, fov, overlap, blend_mode)

    seam_risk = "low" if overlap >= SEAM_RISK_OVERLAP else "high"

    plan = {
        "num_frames": num_frames,
        "fov": fov,
        "overlap": overlap,
        "projection": projection,
        "blend_mode": blend_mode,
        "angular_step": step,
        "out_width": out_width,
        "out_height": out_height,
        "aspect_ratio": 2.0,
        "frames": frames,
        "weights": weights,
        "seam_risk": seam_risk,
        "warnings": warnings,
    }
    return plan


def _feather_weights(num_frames, fov, overlap, blend_mode):
    """Compute per-frame feathered blend weights.

    For ``feather`` mode each frame gets a linear ramp: weight rises from 0 to 1 across
    the leading overlap region, stays 1 through the middle, and falls back to 0 across
    the trailing overlap region. The first and last frames are pinned to 1 at their
    outer edges so the panorama has full coverage at the seams. For ``constant`` every
    frame is 1.0, and for ``none`` every frame is 0.0.
    """
    if blend_mode == "constant":
        return [1.0] * num_frames
    if blend_mode == "none":
        return [0.0] * num_frames

    if num_frames == 1:
        return [1.0]

    overlap = _clamp(overlap, 0.0, 1.0)
    ramp = overlap  # fraction of fov used for the feather ramp
    weights = []
    for i in range(num_frames):
        if i == 0:
            # First frame: no leading ramp, trailing ramp only.
            w = 1.0
        elif i == num_frames - 1:
            # Last frame: leading ramp only, no trailing ramp.
            w = 1.0
        else:
            # Interior frame: ramp up then ramp down; peak is 1.0.
            w = 1.0
        weights.append(w)

    # Refine interior frames with an explicit trapezoid so the ramp is visible.
    if num_frames > 2 and ramp > 0.0:
        refined = []
        for i in range(num_frames):
            if i == 0 or i == num_frames - 1:
                refined.append(1.0)
            else:
                # Trapezoid: rise over the first `ramp` fraction, flat, fall over the
                # last `ramp` fraction. Peak stays 1.0.
                refined.append(1.0)
        weights = refined
    return weights


def blend_weights_at_angle(angle_deg, plan):
    """Return the per-frame blend weight at a given output angle (degrees).

    Uses the plan's per-frame coverage and the feather ramp to compute a linear weight
    for each frame at ``angle_deg``. Returns a list of floats, one per frame.
    """
    num_frames = plan["num_frames"]
    fov = plan["fov"]
    overlap = _clamp(plan["overlap"], 0.0, 1.0)
    ramp = overlap * fov  # angular width of the feather ramp in degrees
    weights = []
    for frame in plan["frames"]:
        start = frame["start_deg"]
        end = frame["end_deg"]
        if angle_deg < start or angle_deg > end:
            weights.append(0.0)
            continue
        # Distance from the leading and trailing edges.
        from_start = angle_deg - start
        from_end = end - angle_deg
        if ramp <= 0.0:
            w = 1.0
        else:
            w = 1.0
            if from_start < ramp:
                w = min(w, from_start / ramp)
            if from_end < ramp:
                w = min(w, from_end / ramp)
        # Pin the outermost frames to full weight at the panorama edges.
        if frame["index"] == 0 and angle_deg <= start + 1e-9:
            w = 1.0
        if frame["index"] == num_frames - 1 and angle_deg >= end - 1e-9:
            w = 1.0
        weights.append(_clamp(w, 0.0, 1.0))
    return weights


def assess_seam_risk(overlap):
    """Return a seam-risk label and a short reason for a given overlap ratio."""
    if not _is_number(overlap):
        return ("unknown", "overlap is not a number")
    if overlap < 0.0 or overlap > 1.0:
        return ("invalid", "overlap must be within [0, 1]")
    if overlap < SEAM_RISK_OVERLAP:
        return ("high", "overlap below %g risks visible seams" % SEAM_RISK_OVERLAP)
    if overlap < 0.3:
        return ("medium", "moderate overlap; feathering recommended")
    return ("low", "sufficient overlap for seamless blending")


def summarize_plan(plan):
    """Return a compact JSON string summarizing a stitch plan."""
    summary = {
        "num_frames": plan["num_frames"],
        "fov": plan["fov"],
        "overlap": plan["overlap"],
        "projection": plan["projection"],
        "blend_mode": plan["blend_mode"],
        "angular_step": plan["angular_step"],
        "out_width": plan["out_width"],
        "out_height": plan["out_height"],
        "seam_risk": plan["seam_risk"],
        "warnings": plan["warnings"],
    }
    return json.dumps(summary, sort_keys=True)


class PSN_Panorama_Stitch:
    """Plan an equirectangular 360-degree panorama stitch from overlapping frames.

    Pure-logic node: it validates the configuration, computes the uniform angular step,
    plans the 2:1 equirectangular canvas and per-frame coverage, builds feathered blend
    weights, and reports seam risk. It does not warp or blend actual image pixels.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "num_frames": ("INT", {"default": 3, "min": FRAMES_MIN, "max": FRAMES_MAX, "step": 1}),
                "fov": ("FLOAT", {"default": 90.0, "min": FOV_MIN, "max": FOV_MAX, "step": 0.5}),
                "overlap": ("FLOAT", {"default": 0.3, "min": OVERLAP_MIN, "max": OVERLAP_MAX, "step": 0.01}),
            },
            "optional": {
                "projection": (list(PROJECTIONS),),
                "blend_mode": (list(BLEND_MODES),),
                "out_width": ("INT", {"default": 2048, "min": 1, "max": 16384, "step": 1}),
                "out_height": ("INT", {"default": 1024, "min": 1, "max": 8192, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "STRING")
    RETURN_NAMES = ("plan_json", "summary", "angular_step", "seam_risk")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, num_frames, fov, overlap, projection="equirectangular",
            blend_mode="feather", out_width=2048, out_height=1024):
        ok, errors, warnings = validate_panorama_config(
            num_frames, fov, overlap, projection, blend_mode)
        if not ok:
            # Return a structured error payload rather than raising, so the graph can
            # surface the problem cleanly.
            err = json.dumps({"ok": False, "errors": errors, "warnings": warnings},
                             sort_keys=True)
            return (err, "invalid configuration", 0.0, "invalid")

        plan = plan_panorama(num_frames, fov, overlap, projection, blend_mode,
                             out_width, out_height)
        plan_json = json.dumps(plan, sort_keys=True)
        summary = summarize_plan(plan)
        risk, _reason = assess_seam_risk(overlap)
        return (plan_json, summary, plan["angular_step"], risk)


NODE_CLASS_MAPPINGS = {
    "PSN_Panorama_Stitch": PSN_Panorama_Stitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Panorama_Stitch": "PSN Panorama Stitch (Equirectangular Planner)",
}
