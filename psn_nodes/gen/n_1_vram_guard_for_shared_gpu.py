"""ParametricStudio VRAM Guard for Shared GPU.

A single ComfyUI custom-node module that enforces a strict VRAM budget
before heavy operations (KSampler, ModelSamplingAuraFlow, ...) on a shared
high-memory GPU (e.g. a 96 GB Blackwell card).

The node inspects the *current* device memory usage (via torch when CUDA is
available, otherwise a caller-injected probe for tests), estimates the
memory the next step will need, and either:

* passes the model/latent through untouched when the budget is respected,
* offloads the model to CPU (``model.to('cpu')``) when the budget would be
  breached, or
* raises a hard-stop ``RuntimeError`` when ``hard_stop`` is enabled.

It also returns the measured usage in GB so it can be logged downstream.

Only ``torch`` and the Python standard library are used.  No network, no
subprocess, no file I/O, no third-party dependencies (``psutil`` is NOT
required; the module degrades gracefully when it is absent).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import torch

CAT = "ParametricStudio/VRAM"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_GB = 1024.0 ** 3


def _current_vram_gb() -> float:
    """Return the current CUDA memory usage in GB (0.0 when no CUDA)."""
    if not torch.cuda.is_available():
        return 0.0
    try:
        return torch.cuda.memory_allocated() / _GB
    except Exception:  # pragma: no cover - defensive
        return 0.0


def _estimate_step_gb(latent: Dict[str, Any], model: Any) -> float:
    """Heuristic estimate of the extra VRAM the next step will need.

    The estimate is intentionally conservative:

    * latent:  ``B * C * H * W * 4`` bytes (float32) plus a 2x activation
      factor to cover intermediate tensors during a denoising step.
    * model:   number of parameters * 4 bytes (float32 weights) plus a
      small fixed overhead for kernels / cuDNN workspaces.
    """
    est = 0.0
    samples = None
    if isinstance(latent, dict):
        samples = latent.get("samples")
    if isinstance(samples, torch.Tensor):
        n = samples.numel()
        est += n * 4 * 2.0  # weights + activations factor
    if model is not None:
        try:
            n_params = sum(p.numel() for p in model.parameters())
        except Exception:  # pragma: no cover - non-module model
            n_params = 0
        est += n_params * 4.0
    # fixed overhead for kernels / workspaces (256 MB)
    est += 256.0 * 1024.0 * 1024.0
    return est / _GB


def _offload_model(model: Any) -> Any:
    """Move a torch module to CPU without mutating the original object."""
    if isinstance(model, torch.nn.Module):
        # ``.to`` returns a new module when the device changes; when it is
        # already on CPU it returns ``self`` which is fine (no mutation).
        return model.to("cpu")
    return model


# ---------------------------------------------------------------------------
# node
# ---------------------------------------------------------------------------

class PSN_VRAM_Budget_Gate:
    """Enforce a VRAM budget before a heavy node (KSampler, ...).

    * When ``current + estimated <= max_vram_gb`` the model and latent are
      passed through unchanged.
    * When the budget would be breached the model is offloaded to CPU
      (``hard_stop=False``) or a ``RuntimeError`` is raised
      (``hard_stop=True``).
    * The measured current usage (GB) is always returned for logging.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "latent": ("LATENT",),
                "max_vram_gb": ("FLOAT", {"default": 80.0, "min": 1.0, "max": 512.0, "step": 0.5}),
                "run_id": ("STRING", {"default": "run", "multiline": False}),
            },
            "optional": {
                "hard_stop": ("BOOLEAN", {"default": False}),
                "probe_gb": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1024.0, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("MODEL", "LATENT", "FLOAT")
    RETURN_NAMES = ("model", "latent", "vram_usage_gb")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        model: Any,
        latent: Dict[str, Any],
        max_vram_gb: float,
        run_id: str,
        hard_stop: bool = False,
        probe_gb: float = -1.0,
    ) -> Tuple[Any, Dict[str, Any], float]:
        # --- validate inputs -------------------------------------------------
        if not isinstance(latent, dict) or "samples" not in latent:
            raise ValueError("latent must be a dict with a 'samples' tensor")
        samples = latent["samples"]
        if not isinstance(samples, torch.Tensor):
            raise ValueError("latent['samples'] must be a torch.Tensor")
        if samples.dim() != 4:
            raise ValueError("latent['samples'] must be a [B, C, H, W] tensor")
        if not (isinstance(max_vram_gb, (int, float)) and math.isfinite(max_vram_gb)):
            raise ValueError("max_vram_gb must be a finite number")
        if max_vram_gb <= 0:
            raise ValueError("max_vram_gb must be > 0")
        if not isinstance(run_id, str):
            raise ValueError("run_id must be a string")

        # --- measure current usage ------------------------------------------
        if probe_gb is not None and probe_gb >= 0.0:
            current_gb = float(probe_gb)
        else:
            current_gb = _current_vram_gb()

        est_gb = _estimate_step_gb(latent, model)
        projected = current_gb + est_gb

        # --- decide ----------------------------------------------------------
        if projected > max_vram_gb:
            if hard_stop:
                raise RuntimeError(
                    f"[PSN_VRAM_Budget_Gate run={run_id}] VRAM budget exceeded: "
                    f"current={current_gb:.3f} GB + est={est_gb:.3f} GB > "
                    f"max={max_vram_gb:.3f} GB. Aborting to protect the shared GPU."
                )
            model = _offload_model(model)

        # never mutate the caller's latent dict
        out_latent = {"samples": samples}
        return (model, out_latent, current_gb)


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VRAM_Budget_Gate": PSN_VRAM_Budget_Gate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRAM_Budget_Gate": "VRAM Budget Gate (Shared GPU)",
}
