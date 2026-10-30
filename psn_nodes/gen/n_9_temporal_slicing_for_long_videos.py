"""
PSN Temporal Slicing for Long Videos (pure-logic core).

This module implements the *planning* and *blending* logic for temporal
slicing of video latents, without any GPU/torch/ComfyUI dependencies.

In a full ComfyUI environment, the actual VAE decode of each slice would
be performed on the GPU. Here we provide:

1. **PSN_Temporal_Slice_Plan** – computes the slice boundaries (start, end,
   blend_start, blend_end) for a given total frame count, slice_size, and
   overlap. This is the pure-logic part that determines how to chunk the
   temporal dimension.

2. **PSN_Temporal_Slice_Blend** – given a list of per-slice decoded frame
   values (as plain numbers or lists of numbers) and the slice plan, blends
   the overlapping regions using linear cross-fade weights and returns the
   final stitched frame sequence.

Both nodes accept and return plain Python values (ints, floats, lists,
strings) so they can be tested without torch or ComfyUI.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Temporal"


def _validate_slice_params(total_frames: int, slice_size: int, overlap: int) -> str:
    """Validate temporal slicing parameters. Returns empty string if OK, else error message."""
    if not isinstance(total_frames, int) or total_frames < 1:
        return "total_frames must be a positive integer"
    if not isinstance(slice_size, int) or slice_size < 1:
        return "slice_size must be a positive integer"
    if not isinstance(overlap, int) or overlap < 0:
        return "overlap must be a non-negative integer"
    if overlap >= slice_size:
        return "overlap must be strictly less than slice_size"
    if slice_size > total_frames:
        return "slice_size must not exceed total_frames"
    return ""


def _compute_slice_plan(total_frames: int, slice_size: int, overlap: int) -> list:
    """
    Compute the temporal slice plan.

    Returns a list of dicts, each with:
      - start: first frame index of this slice (inclusive)
      - end: last frame index of this slice (exclusive)
      - blend_start: first frame index where blending begins (inclusive), or None
      - blend_end: last frame index where blending ends (exclusive), or None

    The first slice starts at 0. Each subsequent slice starts at
    (previous_end - overlap). The last slice is clamped so it ends at
    total_frames.
    """
    slices = []
    pos = 0
    while pos < total_frames:
        end = min(pos + slice_size, total_frames)
        # Determine blend region: overlap with the *next* slice
        # blend_start is where the next slice begins (i.e., end - overlap),
        # but only if there is a next slice and overlap > 0.
        # For the current slice, the blend region is [end - overlap, end)
        # IF a next slice exists. For the last slice, no blend needed.
        next_start = end - overlap if overlap > 0 else end
        has_next = end < total_frames
        if has_next and overlap > 0:
            blend_start = max(pos, end - overlap)
            blend_end = end
        else:
            blend_start = None
            blend_end = None
        slices.append({
            "start": pos,
            "end": end,
            "blend_start": blend_start,
            "blend_end": blend_end,
        })
        if not has_next:
            break
        pos = end - overlap
    return slices


class PSN_Temporal_Slice_Plan:
    """
    Compute the temporal slice plan for decoding a long video latent in chunks.

    Inputs:
      total_frames (INT): total number of frames in the video latent.
      slice_size (INT): number of frames per slice.
      overlap (INT): number of overlapping frames between consecutive slices.

    Outputs:
      plan (STRING): JSON-encoded list of slice descriptors.
      num_slices (INT): number of slices in the plan.
      error (STRING): empty string if valid, otherwise an error message.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "total_frames": ("INT", {"default": 100, "min": 1, "max": 100000}),
                "slice_size": ("INT", {"default": 10, "min": 1, "max": 100000}),
                "overlap": ("INT", {"default": 2, "min": 0, "max": 100000}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("plan", "num_slices", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, total_frames, slice_size, overlap):
        err = _validate_slice_params(total_frames, slice_size, overlap)
        if err:
            return ("[]", 0, err)
        plan = _compute_slice_plan(total_frames, slice_size, overlap)
        import json
        return (json.dumps(plan), len(plan), "")


class PSN_Temporal_Slice_Blend:
    """
    Blend per-slice decoded frame values into a single stitched sequence.

    Each slice's decoded frames are provided as a list of numeric values
    (one value per frame, for simplicity; in practice each frame would be
    a tensor, but here we use scalars to keep it pure-Python).

    Inputs:
      slice_frames (STRING): JSON-encoded list of lists. Each inner list
        contains the decoded frame values for one slice, in order.
      total_frames (INT): total number of frames expected in the output.
      slice_size (INT): number of frames per slice (used to validate).
      overlap (INT): number of overlapping frames.

    Outputs:
      frames (STRING): JSON-encoded list of blended frame values.
      error (STRING): empty string if OK, otherwise an error message.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "slice_frames": ("STRING", {"default": "[]"}),
                "total_frames": ("INT", {"default": 100, "min": 1, "max": 100000}),
                "slice_size": ("INT", {"default": 10, "min": 1, "max": 100000}),
                "overlap": ("INT", {"default": 2, "min": 0, "max": 100000}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("frames", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, slice_frames, total_frames, slice_size, overlap):
        import json
        err = _validate_slice_params(total_frames, slice_size, overlap)
        if err:
            return ("[]", err)
        try:
            slices = json.loads(slice_frames)
        except (json.JSONDecodeError, TypeError):
            return ("[]", "slice_frames is not valid JSON")
        if not isinstance(slices, list):
            return ("[]", "slice_frames must be a JSON list")

        plan = _compute_slice_plan(total_frames, slice_size, overlap)
        if len(slices) != len(plan):
            return ("[]", f"expected {len(plan)} slices, got {len(slices)}")

        # Validate each slice has the right number of frames
        for i, (sl, desc) in enumerate(zip(slices, plan)):
            expected_len = desc["end"] - desc["start"]
            if not isinstance(sl, list) or len(sl) != expected_len:
                return ("[]", f"slice {i} must have {expected_len} frames, got {len(sl) if isinstance(sl, list) else 'non-list'}")

        # Build output array
        out = [0.0] * total_frames
        weights = [0.0] * total_frames

        for i, (sl, desc) in enumerate(zip(slices, plan)):
            start = desc["start"]
            end = desc["end"]
            blend_start = desc["blend_start"]
            blend_end = desc["blend_end"]

            for j, val in enumerate(sl):
                frame_idx = start + j
                if not isinstance(val, (int, float)):
                    return ("[]", f"slice {i} frame {j} is not numeric")
                if blend_start is not None and blend_start <= frame_idx < blend_end:
                    # Linear cross-fade: weight increases from 0 to 1 across the blend region
                    blend_len = blend_end - blend_start
                    t = (frame_idx - blend_start) / max(blend_len - 1, 1)
                    w = t  # 0 at blend_start, 1 at blend_end-1
                else:
                    w = 1.0
                out[frame_idx] += val * w
                weights[frame_idx] += w

        # Normalize by total weight
        for i in range(total_frames):
            if weights[i] > 0:
                out[i] /= weights[i]
            else:
                return ("[]", f"frame {i} has zero weight; check slice plan")

        return (json.dumps(out), "")


NODE_CLASS_MAPPINGS = {
    "PSN_Temporal_Slice_Plan": PSN_Temporal_Slice_Plan,
    "PSN_Temporal_Slice_Blend": PSN_Temporal_Slice_Blend,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Temporal_Slice_Plan": "Temporal Slice Plan",
    "PSN_Temporal_Slice_Blend": "Temporal Slice Blend",
}
