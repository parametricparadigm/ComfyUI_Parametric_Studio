"""PSN_Attention_Style_Patch: pure-logic payload builder for an attention style patch.

This module implements ONLY the secure, pure-Python part of the spec. The real
attention hook requires torch/GPU and is out of scope here. Instead, this node
validates the style vector and strength, and emits a deterministic JSON payload
describing the patch (op, vector, strength, checksum) that a downstream
torch-based hook could consume. It never touches tensors, sockets, files, or
the network.
"""

import json
import hashlib

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Attention"

# Allowed operations for the patch.
_OPS = ("add", "scale_add")

# Bounds for strength to keep the bias sane.
_STRENGTH_MIN = -1e9
_STRENGTH_MAX = 1e9

# Maximum number of components in a style vector we will accept.
_MAX_DIM = 4096


def _validate_vector(style_vector):
    """Validate a style vector given as a JSON list of numbers.

    Returns (ok, vector, reason).
    """
    if not isinstance(style_vector, str):
        return False, None, "style_vector must be a JSON string"
    try:
        data = json.loads(style_vector)
    except (ValueError, TypeError):
        return False, None, "style_vector is not valid JSON"
    if not isinstance(data, list):
        return False, None, "style_vector must be a JSON array"
    if len(data) == 0:
        return False, None, "style_vector must not be empty"
    if len(data) > _MAX_DIM:
        return False, None, "style_vector exceeds max dimension %d" % _MAX_DIM
    for i, v in enumerate(data):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False, None, "style_vector[%d] is not a number" % i
        if v != v:  # NaN
            return False, None, "style_vector[%d] is NaN" % i
    return True, data, "ok"


def _validate_strength(strength):
    """Validate strength. Returns (ok, value, reason)."""
    if isinstance(strength, bool) or not isinstance(strength, (int, float)):
        return False, None, "strength must be a number"
    if strength != strength:  # NaN
        return False, None, "strength is NaN"
    if strength < _STRENGTH_MIN or strength > _STRENGTH_MAX:
        return False, None, "strength out of bounds"
    return True, float(strength), "ok"


def _checksum(op, vector, strength):
    """Deterministic checksum of the patch payload."""
    payload = json.dumps({"op": op, "vector": vector, "strength": strength},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class PSN_Attention_Style_Patch:
    """Builds a validated attention style patch payload (pure logic, no torch)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style_vector": ("STRING", {"default": "[0.1, -0.2, 0.3]",
                                            "multiline": True}),
                "strength": ("FLOAT", {"default": 0.5,
                                       "min": _STRENGTH_MIN,
                                       "max": _STRENGTH_MAX,
                                       "step": 0.001}),
                "op": (list(_OPS),),
            },
            "optional": {
                "model_tag": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("patch_payload", "valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, style_vector, strength, op, model_tag=""):
        ok_v, vector, why_v = _validate_vector(style_vector)
        if not ok_v:
            return ("", False, why_v)
        ok_s, s_val, why_s = _validate_strength(strength)
        if not ok_s:
            return ("", False, why_s)
        if op not in _OPS:
            return ("", False, "op not in allow-list")
        payload = {
            "op": op,
            "vector": vector,
            "strength": s_val,
            "model_tag": model_tag,
            "checksum": _checksum(op, vector, s_val),
        }
        return (json.dumps(payload, sort_keys=True), True, "ok")


NODE_CLASS_MAPPINGS = {"PSN_Attention_Style_Patch": PSN_Attention_Style_Patch}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Attention_Style_Patch": "Attention Style Patch"}
