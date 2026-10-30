"""PSN_Nvidia_VFX_Upscale — pure-logic planning/validation for NVIDIA VFX upscale.

This node does NOT touch a GPU, torch, or the nvidia-vfx CUDA extension.
It only performs the secure-by-design, pure-Python parts of the workflow:
  * validating the requested SCALE and VFX_MODEL against an allow-list,
  * computing the target output dimensions from an input (width, height),
  * producing a deterministic, JSON-serializable "plan" payload that a
    downstream GPU executor (out of scope here) could consume.

Inputs are plain values (ints, strings, JSON text). No sockets, no file/OS
access, no subprocess, no eval/exec, no torch/comfy imports.
"""

import json

# Allow-list of VFX models we are willing to plan for. Anything else is
# rejected so a caller cannot smuggle in an arbitrary model name.
_ALLOWED_VFX_MODELS = ("rtx_video_sr", "rtx_video_sr_hdr", "rtx_video_sr_low_mem")

# Scale bounds: 1x (no-op) up to 8x. Keeps the plan sane and bounded.
_MIN_SCALE = 1
_MAX_SCALE = 8

# Maximum input dimension we are willing to plan for (guards against absurd
# payloads that would overflow a downstream executor).
_MAX_INPUT_DIM = 16384

CAT = "ParametricStudio/NvidiaVFX"


def _validate_scale(scale):
    """Return (ok, reason, normalized_scale)."""
    if not isinstance(scale, int) or isinstance(scale, bool):
        return False, "scale must be an integer", None
    if scale < _MIN_SCALE or scale > _MAX_SCALE:
        return False, "scale must be between %d and %d" % (_MIN_SCALE, _MAX_SCALE), None
    return True, "ok", scale


def _validate_model(model):
    """Return (ok, reason, normalized_model)."""
    if not isinstance(model, str):
        return False, "vfx_model must be a string", None
    m = model.strip()
    if m not in _ALLOWED_VFX_MODELS:
        return False, "vfx_model not in allow-list: %s" % (m,), None
    return True, "ok", m


def _validate_dims(width, height):
    """Return (ok, reason, w, h)."""
    for name, v in (("width", width), ("height", height)):
        if not isinstance(v, int) or isinstance(v, bool):
            return False, "%s must be an integer" % name, None, None
        if v <= 0:
            return False, "%s must be positive" % name, None, None
        if v > _MAX_INPUT_DIM:
            return False, "%s exceeds max %d" % (name, _MAX_INPUT_DIM), None, None
    return True, "ok", width, height


def build_upscale_plan(width, height, scale, vfx_model):
    """Pure-logic plan builder. Returns (ok, reason, plan_dict_or_None)."""
    ok, why, s = _validate_scale(scale)
    if not ok:
        return False, why, None
    ok, why, m = _validate_model(vfx_model)
    if not ok:
        return False, why, None
    ok, why, w, h = _validate_dims(width, height)
    if not ok:
        return False, why, None

    out_w = w * s
    out_h = h * s
    plan = {
        "op": "nvidia_vfx_upscale",
        "vfx_model": m,
        "scale": s,
        "input": {"width": w, "height": h},
        "output": {"width": out_w, "height": out_h},
        "device": "cuda",
        "accelerator": "blackwell",
    }
    return True, "ok", plan


class PSN_Nvidia_VFX_Upscale:
    """Plan an NVIDIA VFX (RTX Video SR) upscale.

    Accepts plain values describing the input image geometry plus the desired
    scale and model. Emits a validated plan (JSON text) and the computed
    output dimensions. The actual GPU work is intentionally out of scope.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 512, "min": 1, "max": _MAX_INPUT_DIM, "step": 1}),
                "height": ("INT", {"default": 512, "min": 1, "max": _MAX_INPUT_DIM, "step": 1}),
                "scale": ("INT", {"default": 2, "min": _MIN_SCALE, "max": _MAX_SCALE, "step": 1}),
                "vfx_model": (list(_ALLOWED_VFX_MODELS),),
            },
            "optional": {
                "image_json": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "INT", "INT")
    RETURN_NAMES = ("ok", "plan_json", "out_width", "out_height")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, scale, vfx_model, image_json=""):
        # If an image_json payload is supplied, prefer its dimensions when it
        # is valid JSON with integer width/height; otherwise fall back to the
        # explicit width/height inputs. This keeps the node usable both as a
        # pure planner and as a thin wrapper over a serialized image header.
        w, h = width, height
        if image_json:
            try:
                data = json.loads(image_json)
            except (ValueError, TypeError):
                data = None
            if isinstance(data, dict):
                cand_w = data.get("width")
                cand_h = data.get("height")
                if isinstance(cand_w, int) and not isinstance(cand_w, bool) \
                        and isinstance(cand_h, int) and not isinstance(cand_h, bool):
                    w, h = cand_w, cand_h

        ok, why, plan = build_upscale_plan(w, h, scale, vfx_model)
        if not ok:
            return (False, json.dumps({"ok": False, "reason": why}), 0, 0)
        return (True, json.dumps(plan), plan["output"]["width"], plan["output"]["height"])


NODE_CLASS_MAPPINGS = {
    "PSN_Nvidia_VFX_Upscale": PSN_Nvidia_VFX_Upscale,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Nvidia_VFX_Upscale": "NVIDIA VFX Upscale (Plan)",
}
