"""PSN Fast Preview Pipeline with TAESD (pure-logic, secure-by-design).

This module implements the *planning / validation / metadata* layer of a
"Fast Preview Pipeline with TAESD" node.  The actual TAESD decode requires
``torch`` and ComfyUI model objects, which are intentionally NOT imported
here.  Instead, the node:

* validates the requested latent channel count against the TAESD allow-list
  (SD 4-ch, SDXL 4-ch, SD3 16-ch, Flux 16-ch);
* validates that the supplied model descriptor is a TAESD variant (not a
  standard VAE);
* computes a deterministic preview-resolution plan (downscale factor,
  target width/height, estimated VRAM savings) from the latent shape;
* emits a structured JSON payload that a downstream GPU worker could consume.

All public functions accept plain Python values (numbers, strings, JSON
text) and return plain values.  No sockets, no file I/O, no subprocess,
no torch, no comfy imports.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/Preview"

# Latent channel counts that TAESD is known to support.
_TAESD_SUPPORTED_CHANNELS = (4, 16)

# Downscale factor applied to the latent spatial dims to produce the
# low-res preview.  2 means the preview image is half the spatial size
# of what a full decode would produce.
_PREVIEW_DOWNSCALE = 2

# Minimum spatial dimension (in pixels) for the preview output.
_MIN_PREVIEW_DIM = 64

# Maximum spatial dimension (in pixels) for the preview output.
_MAX_PREVIEW_DIM = 1024

# Estimated VRAM multiplier: TAESD uses roughly this fraction of the
# VRAM of a standard VAE decode.
_TAESD_VRAM_RATIO = 0.15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_channels(channels):
    """Return (ok, reason) for a latent channel count."""
    if not isinstance(channels, int) or isinstance(channels, bool):
        return False, "channels must be an integer"
    if channels <= 0:
        return False, "channels must be positive"
    if channels not in _TAESD_SUPPORTED_CHANNELS:
        return False, (
            "TAESD does not support {}-channel latents; "
            "supported: {}".format(channels, list(_TAESD_SUPPORTED_CHANNELS))
        )
    return True, "ok"


def _validate_model_descriptor(model_name, model_type):
    """Return (ok, reason) for a model descriptor.

    ``model_name`` is a free-form string (e.g. "taesd.safetensors").
    ``model_type`` should be the string "taesd" for a TAESD variant.
    """
    if not isinstance(model_name, str) or not model_name.strip():
        return False, "model_name must be a non-empty string"
    if not isinstance(model_type, str):
        return False, "model_type must be a string"
    mt = model_type.strip().lower()
    if mt != "taesd":
        return False, (
            "model_type '{}' is not a TAESD variant; "
            "a standard VAE cannot be used for fast preview".format(model_type)
        )
    # Heuristic: the file name should contain "taesd" (case-insensitive).
    if "taesd" not in model_name.lower():
        return False, (
            "model_name '{}' does not appear to be a TAESD model "
            "(expected 'taesd' in the name)".format(model_name)
        )
    return True, "ok"


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _compute_preview_plan(latent_w, latent_h, channels):
    """Compute the preview resolution plan.

    Returns a dict with keys:
        preview_w, preview_h, downscale, est_vram_ratio, est_time_factor
    """
    # Latent spatial dims are typically 1/8 of image dims for SD/SDXL.
    # We work in latent space and then scale.
    dw = _clamp(latent_w // _PREVIEW_DOWNSCALE, _MIN_PREVIEW_DIM // 8, _MAX_PREVIEW_DIM // 8)
    dh = _clamp(latent_h // _PREVIEW_DOWNSCALE, _MIN_PREVIEW_DIM // 8, _MAX_PREVIEW_DIM // 8)

    # Convert back to image-space estimate (x8).
    preview_w = _clamp(dw * 8, _MIN_PREVIEW_DIM, _MAX_PREVIEW_DIM)
    preview_h = _clamp(dh * 8, _MIN_PREVIEW_DIM, _MAX_PREVIEW_DIM)

    # Round to multiples of 8 for alignment.
    preview_w = (preview_w // 8) * 8
    preview_h = (preview_h // 8) * 8

    return {
        "preview_w": preview_w,
        "preview_h": preview_h,
        "downscale": _PREVIEW_DOWNSCALE,
        "est_vram_ratio": _TAESD_VRAM_RATIO,
        "est_time_factor": 0.1,  # roughly 10x faster than full VAE
    }


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_TAESD_Preview_Decode:
    """Plan and validate a TAESD fast-preview decode.

    Pure-logic node: validates inputs, computes a preview resolution plan,
    and emits a JSON payload describing the decode request.  The actual
    GPU decode is performed by a downstream worker that consumes this
    payload.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_channels": ("INT", {"default": 4, "min": 1, "max": 64, "step": 1}),
                "latent_width": ("INT", {"default": 64, "min": 8, "max": 512, "step": 8}),
                "latent_height": ("INT", {"default": 64, "min": 8, "max": 512, "step": 8}),
                "model_name": ("STRING", {"default": "taesd.safetensors"}),
                "model_type": (["taesd", "standard_vae", "other"], {"default": "taesd"}),
            },
            "optional": {
                "extra_config": ("STRING", {"default": "{}", "multiline": True}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("valid", "preview_plan_json", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent_channels, latent_width, latent_height,
            model_name, model_type, extra_config=None):
        # --- validate channels ---
        ok_ch, why_ch = _validate_channels(latent_channels)
        if not ok_ch:
            return (False, "{}", why_ch)

        # --- validate model ---
        ok_model, why_model = _validate_model_descriptor(model_name, model_type)
        if not ok_model:
            return (False, "{}", why_model)

        # --- validate spatial dims ---
        if not isinstance(latent_width, int) or isinstance(latent_width, bool) or latent_width < 8:
            return (False, "{}", "latent_width must be an integer >= 8")
        if not isinstance(latent_height, int) or isinstance(latent_height, bool) or latent_height < 8:
            return (False, "{}", "latent_height must be an integer >= 8")

        # --- parse optional extra config ---
        extra = {}
        if extra_config is not None and isinstance(extra_config, str) and extra_config.strip():
            try:
                parsed = json.loads(extra_config)
                if isinstance(parsed, dict):
                    extra = parsed
                else:
                    return (False, "{}", "extra_config must be a JSON object")
            except (json.JSONDecodeError, ValueError):
                return (False, "{}", "extra_config is not valid JSON")

        # --- compute plan ---
        plan = _compute_preview_plan(latent_width, latent_height, latent_channels)

        payload = {
            "operation": "taesd_preview_decode",
            "model_name": model_name,
            "model_type": "taesd",
            "latent": {
                "channels": latent_channels,
                "width": latent_width,
                "height": latent_height,
            },
            "preview": plan,
            "quality": "low",
            "extra": extra,
        }

        plan_json = json.dumps(payload, sort_keys=True)
        return (True, plan_json, "ok")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_TAESD_Preview_Decode": PSN_TAESD_Preview_Decode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TAESD_Preview_Decode": "TAESD Fast Preview Decode (Plan)",
}
