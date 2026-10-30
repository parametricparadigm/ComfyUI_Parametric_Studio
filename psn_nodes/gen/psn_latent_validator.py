"""PSN_Latent_Validator: validates latent tensor metadata (shape/dtype) without touching GPU tensors.

This module implements the pure-logic, secure-by-design portion of a latent validator.
Because the spec depends on torch/ComfyUI tensor internals, this node operates on
*plain metadata* (a JSON text describing the latent: dims, channels, dtype) rather than
on actual tensors. It never imports torch, opens sockets, or performs file/network I/O.

Inputs are plain values (strings/ints/floats/JSON text). The node:
  - parses a latent metadata JSON string,
  - checks that the tensor is 4-dimensional (B, C, H, W),
  - optionally checks the channel count against an expected value,
  - optionally checks the dtype against an allow-list,
  - returns the (validated) metadata string, a boolean is_valid, and a reason string.

If the metadata is malformed or the checks fail, is_valid is False and a reason is
provided. A strict mode can raise ValueError on failure.
"""

import json

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Latent"

# Allow-list of acceptable latent dtypes (pure strings, no torch).
ALLOWED_DTYPES = ("float16", "bfloat16", "float32", "float64")

# Expected number of dimensions for a latent tensor (B, C, H, W).
EXPECTED_DIMS = 4


def _parse_latent_meta(latent_meta):
    """Parse a latent metadata JSON string into a dict.

    Accepts either a JSON string or an already-parsed dict. Returns a dict with
    keys: dims (list[int]), channels (int, optional), dtype (str, optional).
    Raises ValueError on malformed input.
    """
    if isinstance(latent_meta, dict):
        data = latent_meta
    elif isinstance(latent_meta, str):
        try:
            data = json.loads(latent_meta)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("latent_meta is not valid JSON: %s" % exc)
    else:
        raise ValueError("latent_meta must be a JSON string or dict")

    if not isinstance(data, dict):
        raise ValueError("latent_meta JSON must be an object")

    dims = data.get("dims")
    if dims is None:
        raise ValueError("latent_meta missing 'dims'")
    if not isinstance(dims, (list, tuple)):
        raise ValueError("latent_meta 'dims' must be a list of ints")
    for d in dims:
        if not isinstance(d, int) or isinstance(d, bool):
            raise ValueError("latent_meta 'dims' entries must be ints")
        if d < 0:
            raise ValueError("latent_meta 'dims' entries must be non-negative")

    channels = data.get("channels")
    if channels is not None:
        if not isinstance(channels, int) or isinstance(channels, bool):
            raise ValueError("latent_meta 'channels' must be an int")
        if channels < 0:
            raise ValueError("latent_meta 'channels' must be non-negative")

    dtype = data.get("dtype")
    if dtype is not None and not isinstance(dtype, str):
        raise ValueError("latent_meta 'dtype' must be a string")

    return {
        "dims": list(dims),
        "channels": channels,
        "dtype": dtype,
    }


def _validate_latent(meta, expected_channels=None, allowed_dtypes=ALLOWED_DTYPES):
    """Validate parsed latent metadata.

    Returns (is_valid, reason).
    """
    dims = meta["dims"]
    if len(dims) != EXPECTED_DIMS:
        return False, "expected %d dims (B,C,H,W), got %d" % (EXPECTED_DIMS, len(dims))

    for i, d in enumerate(dims):
        if d <= 0:
            return False, "dim %d must be positive, got %d" % (i, d)

    if expected_channels is not None:
        if not isinstance(expected_channels, int) or isinstance(expected_channels, bool):
            return False, "expected_channels must be an int"
        if expected_channels < 0:
            return False, "expected_channels must be non-negative"
        channels = meta["channels"]
        if channels is None:
            return False, "channels not provided but expected_channels was set"
        if channels != expected_channels:
            return False, "channels mismatch: expected %d, got %d" % (expected_channels, channels)

    dtype = meta["dtype"]
    if dtype is not None:
        if dtype not in allowed_dtypes:
            return False, "dtype %r not in allow-list %s" % (dtype, list(allowed_dtypes))

    return True, "ok"


class PSN_LatentValidator:
    """Validate latent tensor metadata (dims, channels, dtype) before processing."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent_meta": ("STRING", {"default": '{"dims": [1, 4, 64, 64], "channels": 4, "dtype": "float16"}', "multiline": True}),
            },
            "optional": {
                "expected_channels": ("INT", {"default": -1, "min": -1, "max": 1024, "step": 1}),
                "strict": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("latent_meta", "is_valid", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent_meta, expected_channels=-1, strict=False):
        try:
            meta = _parse_latent_meta(latent_meta)
        except ValueError as exc:
            reason = "parse error: %s" % exc
            if strict:
                raise ValueError(reason)
            return (latent_meta, False, reason)

        # expected_channels of -1 means "not provided".
        ec = None if expected_channels is None or expected_channels < 0 else expected_channels
        is_valid, reason = _validate_latent(meta, expected_channels=ec)

        if not is_valid and strict:
            raise ValueError(reason)

        # Return the canonical JSON form of the validated metadata.
        out_meta = json.dumps(meta, sort_keys=True)
        return (out_meta, is_valid, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_LatentValidator": PSN_LatentValidator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LatentValidator": "PSN Latent Validator",
}
