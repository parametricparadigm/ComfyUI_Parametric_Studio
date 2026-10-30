"""PSN_Fast_Attention_Patch: pure-logic planning and validation for patching a model's
attention to a faster kernel (flash / sage / sdpa / auto).

This module does NOT import torch, flash_attn, sageattention, or any ComfyUI internals,
and performs no file/network/OS access. It only computes a deterministic patch plan
(backend selection, capability gating, fallback reason, and a JSON-serializable
payload describing the intended replacement of scaled_dot_product_attention).

The node takes plain values (strings, booleans, numbers, JSON text) and returns plain
values (strings, booleans, numbers, JSON text). A real ComfyUI/torch implementation
would consume the returned plan to actually swap the attention function pointer.
"""

import json

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Attention"

# Allowed backends, in priority order for 'auto' resolution.
_BACKENDS = ("auto", "flash", "sage", "sdpa")

# Minimum compute capability (sm_XX) required per backend.
# flash: sm_80 (Ampere) and up; sage: sm_80 and up; sdpa: sm_50 and up (broad).
_MIN_SM = {
    "flash": 80,
    "sage": 80,
    "sdpa": 50,
}

# Backends that require an optional third-party package to be importable.
_OPTIONAL_PKG = {
    "flash": "flash_attn",
    "sage": "sageattention",
    "sdpa": None,
}


def _normalize_backend(backend):
    """Return a normalized backend string or raise ValueError for unknown values."""
    if not isinstance(backend, str):
        raise ValueError("backend must be a string")
    b = backend.strip().lower()
    if b not in _BACKENDS:
        raise ValueError("backend must be one of %s" % (", ".join(_BACKENDS)))
    return b


def _sm_ok(sm, backend):
    """True if the given compute capability meets the backend minimum."""
    if backend not in _MIN_SM:
        return False
    try:
        sm_val = int(sm)
    except (TypeError, ValueError):
        return False
    return sm_val >= _MIN_SM[backend]


def _pkg_available(pkg, available_packages):
    """Check whether an optional package is present in the provided availability map."""
    if pkg is None:
        return True
    if not isinstance(available_packages, dict):
        return False
    return bool(available_packages.get(pkg, False))


def resolve_backend(requested, sm, available_packages):
    """Resolve the effective backend given the request, GPU capability, and package map.

    Returns (backend, reason) where backend is one of flash/sage/sdpa (never 'auto')
    and reason is a human-readable explanation. Falls back to sdpa when possible.
    """
    requested = _normalize_backend(requested)
    avail = available_packages if isinstance(available_packages, dict) else {}

    if requested != "auto":
        # Explicit request: honor it if feasible, else fall back to sdpa.
        if _sm_ok(sm, requested) and _pkg_available(_OPTIONAL_PKG[requested], avail):
            return requested, "explicit backend '%s' is available and supported" % requested
        if _sm_ok(sm, "sdpa"):
            return "sdpa", "requested '%s' unavailable (sm=%s, pkg=%s); fell back to sdpa" % (
                requested, sm, _OPTIONAL_PKG[requested])
        return "sdpa", "no backend feasible (sm=%s); using sdpa as last resort" % sm

    # Auto: pick the best available in priority order flash -> sage -> sdpa.
    for cand in ("flash", "sage", "sdpa"):
        if _sm_ok(sm, cand) and _pkg_available(_OPTIONAL_PKG[cand], avail):
            return cand, "auto selected '%s' (sm=%s)" % (cand, sm)
    return "sdpa", "auto: no accelerated backend feasible (sm=%s); using sdpa" % sm


def build_patch_plan(backend, sm, available_packages, head_dim, batch_size, seq_len):
    """Build a deterministic, JSON-serializable patch plan.

    Returns a dict with keys: backend, requested, sm, feasible, reason,
    target_function, replacement, head_dim, batch_size, seq_len, memory_estimate_mb.
    """
    requested = _normalize_backend(backend)
    resolved, reason = resolve_backend(requested, sm, available_packages)

    # Memory estimate: attention matrix is batch * heads * seq * seq * dtype_bytes.
    # We approximate heads from head_dim and a nominal model width; keep it simple.
    try:
        hd = int(head_dim)
        bs = int(batch_size)
        sl = int(seq_len)
    except (TypeError, ValueError):
        hd, bs, sl = 0, 0, 0
    if hd <= 0 or bs <= 0 or sl <= 0:
        mem_mb = 0.0
    else:
        # Assume 16 heads and fp16 (2 bytes) for a rough estimate.
        heads = 16
        mem_bytes = bs * heads * sl * sl * 2
        mem_mb = round(mem_bytes / (1024.0 * 1024.0), 3)

    plan = {
        "backend": resolved,
        "requested": requested,
        "sm": sm,
        "feasible": _sm_ok(sm, resolved),
        "reason": reason,
        "target_function": "torch.nn.functional.scaled_dot_product_attention",
        "replacement": {
            "flash": "flash_attn.flash_attn_func",
            "sage": "sageattention.sage_attention",
            "sdpa": "torch.nn.functional.scaled_dot_product_attention",
        }[resolved],
        "head_dim": hd,
        "batch_size": bs,
        "seq_len": sl,
        "memory_estimate_mb": mem_mb,
    }
    return plan


class PSN_Fast_Attention_Patch:
    """Plans a fast-attention kernel patch (flash/sage/sdpa/auto) for a model.

    Pure-logic node: validates inputs, resolves the best feasible backend given GPU
    compute capability and optional package availability, and emits a JSON patch plan.
    No torch/GPU/ComfyUI internals are touched here.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "backend": (list(_BACKENDS), {"default": "auto"}),
                "sm": ("INT", {"default": 80, "min": 0, "max": 120, "step": 1}),
            },
            "optional": {
                "available_packages": ("STRING", {"default": "{}", "multiline": False}),
                "head_dim": ("INT", {"default": 64, "min": 1, "max": 512, "step": 1}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 1024, "step": 1}),
                "seq_len": ("INT", {"default": 1024, "min": 1, "max": 65536, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("patch_plan_json", "feasible", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, backend, sm, available_packages="{}", head_dim=64, batch_size=1, seq_len=1024):
        # Parse the optional package availability map from JSON text.
        try:
            avail = json.loads(available_packages) if available_packages else {}
            if not isinstance(avail, dict):
                avail = {}
        except (ValueError, TypeError):
            avail = {}

        plan = build_patch_plan(backend, sm, avail, head_dim, batch_size, seq_len)
        plan_json = json.dumps(plan, sort_keys=True)
        return (plan_json, bool(plan["feasible"]), plan["reason"])


NODE_CLASS_MAPPINGS = {
    "PSN_Fast_Attention_Patch": PSN_Fast_Attention_Patch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Fast_Attention_Patch": "Fast Attention Patch (Plan)",
}
