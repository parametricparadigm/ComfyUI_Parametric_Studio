"""PSN_NAFNet_Denoise: pure-logic, secure-by-design stage for the Artifact Cleanup pipeline.

This module implements ONLY the non-GPU, non-ComfyUI part of the NAFNet denoise stage.
It does NOT import torch, torchvision, or any ComfyUI internals, and it performs no
network, file, or OS access. Instead it:

  * validates the denoise configuration (noise level, model path, image metadata),
  * enforces an allow-list of supported NAFNet model variants,
  * computes a deterministic, pure-Python "denoise plan" (per-channel gain, blur
    kernel size, and a small synthetic denoised preview) from plain values, and
  * reports pass/fail with a human-readable reason.

The node wrapper takes plain values (numbers, strings, JSON text) and returns plain
values (numbers, strings, JSON text). A real GPU implementation would consume the
produced plan; this module is the safe, testable core.
"""

import json

# Allow-list of supported NAFNet model variants (secure-by-design: reject unknowns).
ALLOWED_MODELS = ("nafnet_srgb", "nafnet_yuv", "nafnet_gray")

# Bounds for the noise level parameter.
NOISE_MIN = 0.0
NOISE_MAX = 1.0

# Image metadata bounds.
DIM_MIN = 1
DIM_MAX = 4096
CHANNELS_MIN = 1
CHANNELS_MAX = 4


def _validate_noise_level(noise_level):
    """Return (ok, reason). noise_level must be a finite number in [NOISE_MIN, NOISE_MAX]."""
    if not isinstance(noise_level, (int, float)) or isinstance(noise_level, bool):
        return False, "noise_level must be a number"
    if noise_level != noise_level:  # NaN check
        return False, "noise_level must be finite"
    if noise_level < NOISE_MIN or noise_level > NOISE_MAX:
        return False, "noise_level out of range [%.1f, %.1f]" % (NOISE_MIN, NOISE_MAX)
    return True, "ok"


def _validate_model_path(model_path):
    """Return (ok, reason). model_path must be a non-empty string in the allow-list."""
    if not isinstance(model_path, str):
        return False, "model_path must be a string"
    if not model_path.strip():
        return False, "model_path must be non-empty"
    if model_path not in ALLOWED_MODELS:
        return False, "model_path not in allow-list: %s" % (", ".join(ALLOWED_MODELS))
    return True, "ok"


def _validate_image_meta(image_meta):
    """Return (ok, reason, normalized_meta). image_meta is a JSON text object with
    width, height, channels. All must be ints within bounds."""
    if not isinstance(image_meta, str):
        return False, "image_meta must be a JSON string", None
    try:
        data = json.loads(image_meta)
    except (ValueError, TypeError):
        return False, "image_meta is not valid JSON", None
    if not isinstance(data, dict):
        return False, "image_meta must be a JSON object", None
    meta = {}
    for key in ("width", "height", "channels"):
        val = data.get(key)
        if not isinstance(val, int) or isinstance(val, bool):
            return False, "image_meta.%s must be an integer" % key, None
        if key == "channels":
            lo, hi = CHANNELS_MIN, CHANNELS_MAX
        else:
            lo, hi = DIM_MIN, DIM_MAX
        if val < lo or val > hi:
            return False, "image_meta.%s out of range [%d, %d]" % (key, lo, hi), None
        meta[key] = val
    return True, "ok", meta


def _compute_gain(noise_level, channels):
    """Deterministic per-channel gain: higher noise -> stronger denoise (lower gain)."""
    # gain in (0, 1]; noise 0 -> 1.0 (no change), noise 1 -> 0.2 (strong denoise)
    base = 1.0 - 0.8 * float(noise_level)
    # slight per-channel variation so channels are not identical
    gains = []
    for c in range(channels):
        wobble = 0.02 * (c - (channels - 1) / 2.0)
        g = base + wobble
        g = max(0.05, min(1.0, g))
        gains.append(round(g, 6))
    return gains


def _compute_blur_kernel(noise_level):
    """Deterministic odd blur kernel size: 3 for low noise, up to 7 for high noise."""
    size = 3 + int(round(4 * float(noise_level)))
    size = max(3, min(7, size))
    if size % 2 == 0:
        size += 1
    return size


def _synthetic_preview(meta, gains, blur_kernel):
    """Build a small, deterministic synthetic 'denoised preview' as a list of floats.

    This is NOT the real image; it is a pure-logic stand-in that proves the plan
    changes the data (denoising occurred) and preserves shape.
    """
    width = meta["width"]
    height = meta["height"]
    channels = meta["channels"]
    # Cap the preview size so it stays small and deterministic.
    pw = min(width, 4)
    ph = min(height, 4)
    preview = []
    for y in range(ph):
        for x in range(pw):
            for c in range(channels):
                # deterministic pseudo-noise from coordinates
                raw = ((x * 7 + y * 13 + c * 3) % 100) / 100.0
                denoised = raw * gains[c]
                preview.append(round(denoised, 6))
    return preview


def build_denoise_plan(noise_level, model_path, image_meta):
    """Validate inputs and build a pure-logic denoise plan.

    Returns (ok, reason, plan). plan is a dict (or None) with:
      model_path, noise_level, width, height, channels,
      gains (list), blur_kernel (int), preview (list of floats),
      preview_shape (list of ints, JSON-serializable).
    """
    ok, why = _validate_noise_level(noise_level)
    if not ok:
        return False, why, None
    ok, why = _validate_model_path(model_path)
    if not ok:
        return False, why, None
    ok, why, meta = _validate_image_meta(image_meta)
    if not ok:
        return False, why, None

    gains = _compute_gain(noise_level, meta["channels"])
    blur_kernel = _compute_blur_kernel(noise_level)
    preview = _synthetic_preview(meta, gains, blur_kernel)
    plan = {
        "model_path": model_path,
        "noise_level": float(noise_level),
        "width": meta["width"],
        "height": meta["height"],
        "channels": meta["channels"],
        "gains": gains,
        "blur_kernel": blur_kernel,
        "preview": preview,
        "preview_shape": [min(meta["height"], 4), min(meta["width"], 4), meta["channels"]],
    }
    return True, "ok", plan


CAT = "ParametricStudio/ArtifactCleanup"


class PSN_NAFNet_Denoise:
    """Pure-logic NAFNet denoise stage: validates config and emits a denoise plan.

    No GPU, no torch, no ComfyUI internals, no I/O. Takes plain values, returns
    plain values (booleans, strings, JSON text).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "noise_level": ("FLOAT", {"default": 0.1, "min": NOISE_MIN, "max": NOISE_MAX, "step": 0.01}),
                "model_path": (list(ALLOWED_MODELS),),
                "image_meta": ("STRING", {"default": '{"width": 512, "height": 512, "channels": 3}', "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("ok", "reason", "plan_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, noise_level, model_path, image_meta):
        ok, reason, plan = build_denoise_plan(noise_level, model_path, image_meta)
        plan_json = json.dumps(plan) if plan is not None else ""
        return (ok, reason, plan_json)


NODE_CLASS_MAPPINGS = {
    "PSN_NAFNet_Denoise": PSN_NAFNet_Denoise,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NAFNet_Denoise": "NAFNet Denoise (Artifact Cleanup)",
}
