"""PSN_Batch_Calculator: pure-logic batch size optimizer for Blackwell GPU workflows.

This module implements ONLY the deterministic, secure-by-design calculation logic
for choosing an optimal image batch size from plain numeric inputs. It performs
no GPU/torch/ComfyUI work, no network, no file/OS access, and no subprocess/eval.
It is a node wrapper that takes plain values (numbers, strings) and returns
plain values (numbers, strings), suitable for being wired into a ComfyUI graph
where a VRAM monitor supplies `vram_available_gb`.

Formula:
    batch = floor((vram_available_gb - model_size_gb - safety_margin) / per_image_vram_gb)
    safety_margin = safety_margin_pct * vram_available_gb
    optimal_batch = clamp(batch, min_batch, max_batch)
    estimated_vram_usage = model_size_gb + optimal_batch * per_image_vram_gb
"""

import math

CAT = "ParametricStudio/Batch"

# Default safety margin as a fraction of available VRAM (10%).
DEFAULT_SAFETY_MARGIN_PCT = 0.10


def psn_batch_calculate(vram_available_gb, model_size_gb, per_image_vram_gb,
                        min_batch, max_batch, safety_margin_pct=DEFAULT_SAFETY_MARGIN_PCT):
    """Compute the optimal batch size and estimated VRAM usage.

    Returns a tuple (optimal_batch, estimated_vram_usage, reason).
    Raises ValueError on invalid numeric inputs.
    """
    # --- Validate numeric inputs ---
    for name, val in (("vram_available_gb", vram_available_gb),
                      ("model_size_gb", model_size_gb),
                      ("per_image_vram_gb", per_image_vram_gb),
                      ("min_batch", min_batch),
                      ("max_batch", max_batch),
                      ("safety_margin_pct", safety_margin_pct)):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValueError(f"{name} must be a number, got {type(val).__name__}")

    vram = float(vram_available_gb)
    model = float(model_size_gb)
    per_image = float(per_image_vram_gb)
    lo = int(min_batch)
    hi = int(max_batch)
    margin_pct = float(safety_margin_pct)

    # --- Validate ranges ---
    if vram < 0:
        raise ValueError("vram_available_gb must be >= 0")
    if model < 0:
        raise ValueError("model_size_gb must be >= 0")
    if per_image <= 0:
        raise ValueError("per_image_vram_gb must be > 0")
    if lo < 1:
        raise ValueError("min_batch must be >= 1")
    if hi < lo:
        raise ValueError("max_batch must be >= min_batch")
    if not (0.0 <= margin_pct < 1.0):
        raise ValueError("safety_margin_pct must be in [0, 1)")

    # --- Core calculation ---
    safety_margin = margin_pct * vram
    free_for_images = vram - model - safety_margin

    if free_for_images <= 0:
        # Not enough VRAM even for the model + margin; fall back to min_batch.
        optimal = lo
        reason = "insufficient_vram_for_model"
    else:
        raw_batch = math.floor(free_for_images / per_image)
        optimal = max(lo, min(hi, raw_batch))
        if raw_batch < lo:
            reason = "clamped_to_min"
        elif raw_batch > hi:
            reason = "clamped_to_max"
        else:
            reason = "within_range"

    estimated_vram_usage = model + optimal * per_image
    return optimal, estimated_vram_usage, reason


class PSN_Batch_Calculator:
    """Calculate the optimal image batch size from available VRAM and model size."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vram_available_gb": ("FLOAT", {"default": 24.0, "min": 0.0, "max": 1e6, "step": 0.1}),
                "model_size_gb": ("FLOAT", {"default": 6.0, "min": 0.0, "max": 1e6, "step": 0.1}),
                "per_image_vram_gb": ("FLOAT", {"default": 1.0, "min": 0.001, "max": 1e6, "step": 0.01}),
                "min_batch": ("INT", {"default": 1, "min": 1, "max": 1024}),
                "max_batch": ("INT", {"default": 8, "min": 1, "max": 1024}),
                "safety_margin_pct": ("FLOAT", {"default": DEFAULT_SAFETY_MARGIN_PCT, "min": 0.0, "max": 0.999, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("optimal_batch", "estimated_vram_usage", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, vram_available_gb, model_size_gb, per_image_vram_gb,
            min_batch, max_batch, safety_margin_pct=DEFAULT_SAFETY_MARGIN_PCT):
        optimal, est, reason = psn_batch_calculate(
            vram_available_gb, model_size_gb, per_image_vram_gb,
            min_batch, max_batch, safety_margin_pct)
        return (optimal, est, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Batch_Calculator": PSN_Batch_Calculator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Batch_Calculator": "PSN Batch Size Optimizer",
}
