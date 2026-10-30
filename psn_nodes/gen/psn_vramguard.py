"""PSN_VRAMGuard: Pre-flight VRAM safety check.

This module implements the pure-logic, secure-by-design part of a VRAM guard.
It does NOT import torch, does NOT query the GPU, and does NOT perform any
file/network/OS access. Instead, it accepts plain numeric inputs (allocated
bytes, reserved bytes, total bytes, required GB, batch size) and applies the
same decision rule the spec describes:

    If (allocated + required_gb * 1e9) > total_memory * 0.9 -> unsafe (OOM risk)

The ComfyUI node wrapper (PSN_VRAMGuard) takes these values as inputs so the
caller (or an upstream node that actually queries torch.cuda) can feed them in.
This keeps the node testable without a GPU and safe by design.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/VRAM"

# Safety margin: we consider VRAM "full" at 90% of total.
_SAFETY_FRACTION = 0.9
# Minimum batch size we allow (0 is meaningless for a batch).
_MIN_BATCH_SIZE = 1
# Maximum batch size we will consider (guards against absurd inputs).
_MAX_BATCH_SIZE = 10_000
# Minimum required GB (negative or zero is meaningless).
_MIN_REQUIRED_GB = 0.0
# Maximum required GB we will consider (guards against absurd inputs).
_MAX_REQUIRED_GB = 1e6


def _validate_inputs(required_gb, current_batch_size, allocated_bytes,
                     reserved_bytes, total_bytes):
    """Validate all numeric inputs. Returns (ok, reason)."""
    # required_gb
    if not isinstance(required_gb, (int, float)) or isinstance(required_gb, bool):
        return False, "required_gb must be a number"
    if required_gb < _MIN_REQUIRED_GB:
        return False, "required_gb must be >= 0"
    if required_gb > _MAX_REQUIRED_GB:
        return False, "required_gb exceeds maximum allowed"

    # current_batch_size
    if not isinstance(current_batch_size, int) or isinstance(current_batch_size, bool):
        return False, "current_batch_size must be an integer"
    if current_batch_size < _MIN_BATCH_SIZE:
        return False, "current_batch_size must be >= 1"
    if current_batch_size > _MAX_BATCH_SIZE:
        return False, "current_batch_size exceeds maximum allowed"

    # allocated_bytes, reserved_bytes, total_bytes
    for name, val in (("allocated_bytes", allocated_bytes),
                      ("reserved_bytes", reserved_bytes),
                      ("total_bytes", total_bytes)):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            return False, f"{name} must be a number"
        if val < 0:
            return False, f"{name} must be >= 0"

    if total_bytes <= 0:
        return False, "total_bytes must be > 0"

    if allocated_bytes > total_bytes:
        return False, "allocated_bytes cannot exceed total_bytes"

    if reserved_bytes > total_bytes:
        return False, "reserved_bytes cannot exceed total_bytes"

    return True, "ok"


def _check_vram(required_gb, current_batch_size, allocated_bytes,
                reserved_bytes, total_bytes):
    """Core VRAM check. Returns (safe, message)."""
    ok, why = _validate_inputs(required_gb, current_batch_size,
                               allocated_bytes, reserved_bytes, total_bytes)
    if not ok:
        return False, f"Invalid input: {why}"

    required_bytes = required_gb * 1e9
    projected = allocated_bytes + required_bytes
    limit = total_bytes * _SAFETY_FRACTION

    if projected > limit:
        headroom = limit - projected
        return False, (
            f"OOM risk: projected {projected:.3e} bytes exceeds "
            f"90% limit {limit:.3e} bytes by {-headroom:.3e} bytes "
            f"(allocated={allocated_bytes:.3e}, required={required_bytes:.3e}, "
            f"total={total_bytes:.3e}, batch={current_batch_size})"
        )

    headroom = limit - projected
    return True, (
        f"Safe: projected {projected:.3e} bytes is within "
        f"90% limit {limit:.3e} bytes (headroom={headroom:.3e} bytes, "
        f"batch={current_batch_size})"
    )


class PSN_VRAMGuard:
    """Pre-flight VRAM safety check.

    Inputs are plain numbers so this node is pure-logic and testable without
    a GPU. An upstream node (or the user) should supply the actual
    torch.cuda.memory_allocated(), torch.cuda.memory_reserved(), and
    torch.cuda.get_device_properties(0).total_memory values.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "required_gb": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.1}),
                "current_batch_size": ("INT", {"default": 1, "min": 1, "max": 10000}),
                "allocated_bytes": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e18, "step": 1.0}),
                "reserved_bytes": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e18, "step": 1.0}),
                "total_bytes": ("FLOAT", {"default": 24e9, "min": 1.0, "max": 1e18, "step": 1.0}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("safe", "message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, required_gb, current_batch_size, allocated_bytes,
            reserved_bytes, total_bytes):
        safe, message = _check_vram(required_gb, current_batch_size,
                                    allocated_bytes, reserved_bytes,
                                    total_bytes)
        return (safe, message)


NODE_CLASS_MAPPINGS = {
    "PSN_VRAMGuard": PSN_VRAMGuard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAMGuard": "VRAM Guard (Pre-flight Check)",
}
