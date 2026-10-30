"""PSN_ArchCompatibilityChecker - ComfyUI custom node.

Verifies that a submitted graph's model requirements match the loaded
model's architecture and dtype.  In a real ComfyUI environment the
``model`` input is a ComfyUI MODEL object (a dict-like wrapper around a
``torch.nn.Module``).  This module inspects the object for well-known
attributes that ComfyUI exposes (``model_config``, ``model_options``,
``model_type``, ``dtype``) and falls back to structural heuristics when
those are absent.

Only ``torch`` (CPU) and the Python standard library are used.
"""

import torch

CAT = "ParametricStudio/Model"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_DTYPE_ALIASES = {
    "fp16": torch.float16,
    "float16": torch.float16,
    "half": torch.float16,
    "fp32": torch.float32,
    "float32": torch.float32,
    "full": torch.float32,
    "bf16": torch.bfloat16,
    "bfloat16": torch.bfloat16,
}

_ARCH_ALIASES = {
    "sdxl": "sdxl",
    "sd_xl": "sdxl",
    "sd-xl": "sdxl",
    "sd15": "sd15",
    "sd_15": "sd15",
    "sd-15": "sd15",
    "sd1": "sd15",
    "sdxl-turbo": "sdxl",
    "sdxl-turbo": "sdxl",
    "sd3": "sd3",
    "sd_3": "sd3",
    "sd-3": "sd3",
    "flux": "flux",
    "flux-dev": "flux",
    "flux-schnell": "flux",
    "unknown": "unknown",
}


def _normalize_arch(name):
    """Return a canonical architecture key or 'unknown'."""
    if not isinstance(name, str):
        return "unknown"
    key = name.strip().lower()
    return _ARCH_ALIASES.get(key, key if key else "unknown")


def _normalize_dtype(name):
    """Return a torch dtype or None if unrecognised."""
    if not isinstance(name, str):
        return None
    key = name.strip().lower()
    return _DTYPE_ALIASES.get(key)


def _get_model_dtype(model):
    """Best-effort extraction of the model's dominant dtype.

    Checks, in order:
      1. ``model['model_options']['dtype']``  (ComfyUI convention)
      2. ``model['model_config']['dtype']``
      3. ``model.dtype`` attribute
      4. iterate parameters / buffers and take the most common dtype
    Returns a ``torch.dtype`` or ``None``.
    """
    # 1 & 2: dict-style ComfyUI model objects
    if isinstance(model, dict):
        opts = model.get("model_options")
        if isinstance(opts, dict) and "dtype" in opts:
            d = opts["dtype"]
            if isinstance(d, torch.dtype):
                return d
            if isinstance(d, str):
                return _normalize_dtype(d)
        cfg = model.get("model_config")
        if isinstance(cfg, dict) and "dtype" in cfg:
            d = cfg["dtype"]
            if isinstance(d, torch.dtype):
                return d
            if isinstance(d, str):
                return _normalize_dtype(d)

    # 3: direct attribute
    dt = getattr(model, "dtype", None)
    if isinstance(dt, torch.dtype):
        return dt
    if isinstance(dt, str):
        return _normalize_dtype(dt)

    # 4: scan parameters / buffers
    counts = {}
    for attr in ("parameters", "buffers"):
        fn = getattr(model, attr, None)
        if callable(fn):
            try:
                for p in fn():
                    d = p.dtype
                    counts[d] = counts.get(d, 0) + 1
            except Exception:
                pass
    if counts:
        return max(counts, key=counts.get)
    return None


def _get_model_arch(model):
    """Best-effort extraction of the model's architecture string.

    Checks, in order:
      1. ``model['model_config']['model_type']``
      2. ``model['model_config']['unet_config']['model_type']``
      3. ``model.model_type`` attribute
      4. structural heuristic (see below)
    Returns a canonical arch string (e.g. 'sdxl', 'sd15') or 'unknown'.
    """
    raw = None

    if isinstance(model, dict):
        cfg = model.get("model_config")
        if isinstance(cfg, dict):
            raw = cfg.get("model_type")
            if raw is None:
                unet = cfg.get("unet_config")
                if isinstance(unet, dict):
                    raw = unet.get("model_type")
        if raw is None:
            raw = model.get("model_type")

    if raw is None:
        raw = getattr(model, "model_type", None)

    if isinstance(raw, str) and raw.strip():
        return _normalize_arch(raw)

    # structural heuristic: look for a 'model' sub-module and inspect
    # its config / class name
    inner = model.get("model") if isinstance(model, dict) else getattr(model, "model", None)
    if inner is not None:
        cfg = getattr(inner, "config", None)
        if isinstance(cfg, dict):
            mt = cfg.get("model_type")
            if isinstance(mt, str) and mt.strip():
                return _normalize_arch(mt)
        cls_name = type(inner).__name__.lower()
        if "xl" in cls_name:
            return "sdxl"
        if "sd3" in cls_name or "sd_3" in cls_name:
            return "sd3"
        if "flux" in cls_name:
            return "flux"
        if "sd1" in cls_name or "sd_1" in cls_name:
            return "sd15"

    return "unknown"


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_ArchCompatibilityChecker:
    """Check that a loaded model matches the expected architecture and dtype."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "expected_arch": (
                    ["sdxl", "sd15", "sd3", "flux", "unknown"],
                    {"default": "sdxl"},
                ),
                "expected_dtype": (
                    ["fp16", "fp32", "bf16"],
                    {"default": "fp16"},
                ),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("IS_COMPATIBLE", "MISMATCH_DETAILS")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, expected_arch, expected_dtype):
        exp_arch = _normalize_arch(expected_arch)
        exp_dt = _normalize_dtype(expected_dtype)

        actual_arch = _get_model_arch(model)
        actual_dt = _get_model_dtype(model)

        problems = []

        # architecture check
        if exp_arch != "unknown":
            if actual_arch == "unknown":
                problems.append(
                    f"architecture: expected '{exp_arch}' but model arch is unknown"
                )
            elif actual_arch != exp_arch:
                problems.append(
                    f"architecture: expected '{exp_arch}' but got '{actual_arch}'"
                )

        # dtype check
        if exp_dt is not None:
            if actual_dt is None:
                problems.append(
                    f"dtype: expected '{expected_dtype}' but model dtype is unknown"
                )
            elif actual_dt != exp_dt:
                problems.append(
                    f"dtype: expected '{expected_dtype}' but got {actual_dt}"
                )

        details = "; ".join(problems) if problems else ""
        compatible = len(problems) == 0
        return (compatible, details)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ArchCompatibilityChecker": PSN_ArchCompatibilityChecker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ArchCompatibilityChecker": "PSN Architecture Compatibility Checker",
}
