"""PSN_Resolution_Preset: enforce consistent dimensions and aspect ratios.

This module is pure Python standard library only. It performs no GPU/torch/ComfyUI
internals, no network, no file/OS access, and no eval/exec. It takes plain values
(integers, strings) and returns standardized integer dimensions that are multiples
of 8 (for VAE) and compatible with the selected model family.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Resolution"

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "custom"]
MODEL_TYPES = ["SDXL", "Flux", "Wan", "Custom"]

# Model-specific constraints: (min_dim, max_dim, multiple_of)
MODEL_CONSTRAINTS = {
    "SDXL": (256, 2048, 8),
    "Flux": (256, 2048, 8),
    "Wan": (256, 1024, 8),
    "Custom": (8, 4096, 8),
}

# Aspect ratio numeric values (w/h)
ASPECT_VALUES = {
    "1:1": (1, 1),
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3": (4, 3),
    "3:4": (3, 4),
}


def _round_to_multiple(value, multiple):
    """Round value to the nearest multiple, ensuring at least one multiple."""
    if value < multiple:
        return multiple
    return int(round(value / multiple)) * multiple


def _clamp(value, lo, hi):
    """Clamp value between lo and hi."""
    return max(lo, min(hi, value))


def _compute_dimensions(width, height, aspect_ratio, model_type):
    """Compute standardized dimensions.

    Returns (final_width, final_height, latent_size, reason).
    """
    if model_type not in MODEL_CONSTRAINTS:
        return (0, 0, 0, "unknown model type: %s" % model_type)

    min_dim, max_dim, multiple = MODEL_CONSTRAINTS[model_type]

    # Determine target dimensions based on aspect ratio
    if aspect_ratio == "custom":
        # Use provided width and height, but enforce constraints
        target_w = int(width)
        target_h = int(height)
    else:
        if aspect_ratio not in ASPECT_VALUES:
            return (0, 0, 0, "unknown aspect ratio: %s" % aspect_ratio)
        ar_w, ar_h = ASPECT_VALUES[aspect_ratio]
        # Use the larger of width/height as the base, scale by aspect ratio
        base = max(int(width), int(height))
        if ar_w >= ar_h:
            target_w = base
            target_h = int(round(base * ar_h / ar_w))
        else:
            target_h = base
            target_w = int(round(base * ar_w / ar_h))

    # Clamp to model constraints
    target_w = _clamp(target_w, min_dim, max_dim)
    target_h = _clamp(target_h, min_dim, max_dim)

    # Round to multiple of 8
    final_w = _round_to_multiple(target_w, multiple)
    final_h = _round_to_multiple(target_h, multiple)

    # Re-clamp after rounding (rounding could push over max)
    final_w = _clamp(final_w, min_dim, max_dim)
    final_h = _clamp(final_h, min_dim, max_dim)

    # Ensure final values are still multiples of 8
    if final_w % multiple != 0:
        final_w = _round_to_multiple(final_w, multiple)
    if final_h % multiple != 0:
        final_h = _round_to_multiple(final_h, multiple)

    latent_size = min(final_w, final_h) // multiple

    reason = "ok"
    return (final_w, final_h, latent_size, reason)


class PSN_Resolution_Preset:
    """Enforce consistent dimensions and aspect ratios across generation pipelines."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1024, "min": 8, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 8, "max": 4096, "step": 8}),
                "aspect_ratio": (ASPECT_RATIOS,),
                "model_type": (MODEL_TYPES,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("INT", "INT", "INT")
    RETURN_NAMES = ("width", "height", "latent_size")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, width, height, aspect_ratio, model_type):
        final_w, final_h, latent_size, reason = _compute_dimensions(
            width, height, aspect_ratio, model_type
        )
        return (final_w, final_h, latent_size)


NODE_CLASS_MAPPINGS = {"PSN_Resolution_Preset": PSN_Resolution_Preset}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_Resolution_Preset": "PSN Resolution Preset"}
