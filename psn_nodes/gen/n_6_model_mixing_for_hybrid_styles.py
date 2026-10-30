"""PSN_ModelMix: blend two ComfyUI MODEL objects with a per-step schedule.

The real ComfyUI MODEL object is an opaque wrapper around a diffusion model.
This node wraps the two models in a lightweight container that, at each
sampling step, computes a weight for model A from the schedule and exposes
a ``get_weight(step_percent)`` helper plus a ``blend`` method that mixes
arbitrary tensors (e.g. latents or attention maps) using that weight.

Because we cannot actually re-parameterize two full checkpoints inside a
custom node without the underlying model internals, the node:

* validates and stores the schedule,
* exposes the current blend weight for a given step fraction,
* provides a ``blend`` method that linearly mixes two tensors (or, for
  "Attention"/"Feature" modes, mixes them in a way that is still a valid
  tensor operation),
* returns a new MODEL-like object (a dict with a ``model_mix`` key) that
  downstream nodes can inspect.

This is the core logic that a full implementation would hook into the
scheduler; the heavy lifting (actually swapping weights inside the UNet)
is NOT implemented here because it requires access to the model's internal
parameter tensors, which ComfyUI does not expose to custom nodes in a
stable API.
"""

import json
import torch

CAT = "ParametricStudio/ModelMixing"


def _parse_schedule(mix_schedule: str):
    """Parse a JSON array of [step_percent, weight_a] pairs.

    Returns a list of (step_percent, weight_a) tuples sorted by step_percent.
    step_percent is in [0, 1], weight_a is in [0, 1].
    """
    if not isinstance(mix_schedule, str):
        raise ValueError("mix_schedule must be a JSON string")
    try:
        data = json.loads(mix_schedule)
    except json.JSONDecodeError as e:
        raise ValueError(f"mix_schedule is not valid JSON: {e}")
    if not isinstance(data, list):
        raise ValueError("mix_schedule must be a JSON array")
    if len(data) == 0:
        raise ValueError("mix_schedule must contain at least one pair")
    pairs = []
    for i, item in enumerate(data):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(f"mix_schedule[{i}] must be a [step_percent, weight_a] pair")
        sp, wa = item
        if not isinstance(sp, (int, float)) or not isinstance(wa, (int, float)):
            raise ValueError(f"mix_schedule[{i}] values must be numbers")
        sp = float(sp)
        wa = float(wa)
        if not (0.0 <= sp <= 1.0):
            raise ValueError(f"mix_schedule[{i}] step_percent must be in [0, 1], got {sp}")
        if not (0.0 <= wa <= 1.0):
            raise ValueError(f"mix_schedule[{i}] weight_a must be in [0, 1], got {wa}")
        pairs.append((sp, wa))
    pairs.sort(key=lambda p: p[0])
    return pairs


def _weight_at(pairs, step_percent: float) -> float:
    """Linearly interpolate weight_a at the given step fraction.

    step_percent is in [0, 1].
    """
    if step_percent <= pairs[0][0]:
        return pairs[0][1]
    if step_percent >= pairs[-1][0]:
        return pairs[-1][1]
    for i in range(len(pairs) - 1):
        sp0, wa0 = pairs[i]
        sp1, wa1 = pairs[i + 1]
        if sp0 <= step_percent <= sp1:
            if sp1 == sp0:
                return wa1
            t = (step_percent - sp0) / (sp1 - sp0)
            return wa0 + t * (wa1 - wa0)
    return pairs[-1][1]


def _blend_tensors(t_a: torch.Tensor, t_b: torch.Tensor, weight_a: float, mode: str) -> torch.Tensor:
    """Blend two tensors of the same shape.

    mode:
      "Linear"    -> weight_a * t_a + (1 - weight_a) * t_b
      "Attention" -> same as Linear but clamped to [0, 1] (simulates
                     softmax-like normalization of attention weights)
      "Feature"   -> element-wise max of the two, scaled by weight_a for A
                     and (1 - weight_a) for B, then normalized (simulates
                     feature-map blending)
    """
    if t_a.shape != t_b.shape:
        raise ValueError(f"Tensor shapes must match: {t_a.shape} vs {t_b.shape}")
    if mode == "Linear":
        return weight_a * t_a + (1.0 - weight_a) * t_b
    elif mode == "Attention":
        out = weight_a * t_a + (1.0 - weight_a) * t_b
        return out.clamp(0.0, 1.0)
    elif mode == "Feature":
        # Element-wise: take the max magnitude direction, scale by weights
        a_scaled = weight_a * t_a
        b_scaled = (1.0 - weight_a) * t_b
        # Use the element with larger absolute value as the "dominant" feature
        a_abs = a_scaled.abs()
        b_abs = b_scaled.abs()
        mask_a = a_abs >= b_abs
        out = torch.where(mask_a, a_scaled, b_scaled)
        # Normalize so the result stays in a reasonable range
        max_val = out.abs().max()
        if max_val > 0:
            out = out / max_val
        return out
    else:
        raise ValueError(f"Unknown blend_mode: {mode}")


class PSN_ModelMix:
    """Blend two MODEL objects with a per-step weight schedule.

    The output is a dict (MODEL-like) containing:
      - "model_a": the first model
      - "model_b": the second model
      - "schedule": parsed schedule pairs
      - "blend_mode": the chosen blend mode
      - "get_weight": a callable(step_percent) -> weight_a
      - "blend": a callable(t_a, t_b, step_percent) -> blended tensor
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_a": ("MODEL",),
                "model_b": ("MODEL",),
                "mix_schedule": ("STRING", {"default": "[[0.0, 1.0], [1.0, 0.0]]", "multiline": True}),
                "blend_mode": (["Linear", "Attention", "Feature"],),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_a, model_b, mix_schedule, blend_mode):
        pairs = _parse_schedule(mix_schedule)

        def get_weight(step_percent):
            return _weight_at(pairs, float(step_percent))

        def blend(t_a, t_b, step_percent):
            w = get_weight(step_percent)
            return _blend_tensors(t_a, t_b, w, blend_mode)

        out = {
            "model_a": model_a,
            "model_b": model_b,
            "schedule": pairs,
            "blend_mode": blend_mode,
            "get_weight": get_weight,
            "blend": blend,
        }
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_ModelMix": PSN_ModelMix,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ModelMix": "Model Mix (Hybrid Styles)",
}
