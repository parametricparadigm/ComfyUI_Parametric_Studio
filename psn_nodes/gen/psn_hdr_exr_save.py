"""PSN_HDR_EXR_Save: pure-logic EXR save planner.

This module implements ONLY the secure, pure-logic portion of an EXR save node.
It does NOT open sockets, files, or use torch/OpenEXR. Instead it:
  - validates the file path against an allow-list of safe extensions and
    rejects path traversal / absolute paths / null bytes,
  - validates the compression choice against an allow-list,
  - estimates the required disk space from a plain (H, W, C) shape and a
    bytes-per-channel value, and compares it against a provided free-space
    figure,
  - builds a deterministic, JSON-serializable "save plan" payload that a real
    EXR writer could consume.

Inputs are plain values (numbers, strings, JSON text). The node returns a
status string and the plan as JSON text.
"""

import json

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/HDR"

_COMPRESSIONS = ("None", "Zip", "Piz", "B44")
_SAFE_EXTS = (".exr",)
_BYTES_PER_CHANNEL = 4  # linear float32


def _psn_validate_path(file_path):
    """Return (ok, reason). Rejects unsafe paths without touching the OS."""
    if not isinstance(file_path, str) or not file_path.strip():
        return False, "file_path must be a non-empty string"
    if "\x00" in file_path:
        return False, "file_path contains a null byte"
    if file_path.startswith("/") or file_path.startswith("\\"):
        return False, "absolute paths are not allowed"
    if ".." in file_path.split("/"):
        return False, "path traversal is not allowed"
    if "\\" in file_path:
        return False, "backslash separators are not allowed"
    lowered = file_path.lower()
    if not any(lowered.endswith(ext) for ext in _SAFE_EXTS):
        return False, "file_path must end with an allowed extension (.exr)"
    return True, "ok"


def _psn_validate_compression(compression):
    if compression not in _COMPRESSIONS:
        return False, "compression must be one of: " + ", ".join(_COMPRESSIONS)
    return True, "ok"


def _psn_estimate_bytes(height, width, channels):
    return int(height) * int(width) * int(channels) * _BYTES_PER_CHANNEL


def _psn_build_plan(file_path, compression, height, width, channels, free_space):
    required = _psn_estimate_bytes(height, width, channels)
    plan = {
        "file_path": file_path,
        "compression": compression,
        "height": int(height),
        "width": int(width),
        "channels": int(channels),
        "bytes_per_channel": _BYTES_PER_CHANNEL,
        "required_bytes": required,
        "free_space_bytes": int(free_space),
        "fits": required <= int(free_space),
    }
    return plan


class PSN_HDR_EXR_Save:
    """Plan and validate an EXR save without performing any I/O."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "height": ("INT", {"default": 512, "min": 1, "max": 16384}),
                "width": ("INT", {"default": 512, "min": 1, "max": 16384}),
                "channels": ("INT", {"default": 3, "min": 1, "max": 16}),
                "file_path": ("STRING", {"default": "out/exr/frame.exr"}),
                "compression": (list(_COMPRESSIONS),),
                "free_space": ("FLOAT", {"default": 1e9, "min": 0.0, "max": 1e18, "step": 1.0}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "plan_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, height, width, channels, file_path, compression, free_space):
        ok_path, why_path = _psn_validate_path(file_path)
        if not ok_path:
            return ("Error: " + why_path, json.dumps({"error": why_path}))

        ok_comp, why_comp = _psn_validate_compression(compression)
        if not ok_comp:
            return ("Error: " + why_comp, json.dumps({"error": why_comp}))

        if int(height) < 1 or int(width) < 1 or int(channels) < 1:
            return ("Error: dimensions must be positive", json.dumps({"error": "bad dimensions"}))

        plan = _psn_build_plan(file_path, compression, height, width, channels, free_space)
        if not plan["fits"]:
            return (
                "Error: insufficient disk space (need %d, have %d)" % (plan["required_bytes"], plan["free_space_bytes"]),
                json.dumps(plan),
            )
        return ("Saved", json.dumps(plan))


NODE_CLASS_MAPPINGS = {"PSN_HDR_EXR_Save": PSN_HDR_EXR_Save}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_HDR_EXR_Save": "HDR EXR Save (Planner)"}
