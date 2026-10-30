"""PSN_ClipMerger: pure-logic planning and frame-index mapping for merging video clips.

This module implements ONLY the secure, pure-Python control plane for a clip-merger
node. It does NOT touch GPU tensors, torch, ComfyUI internals, or any I/O. Instead it
validates inputs, computes the merged frame count, and produces the exact source
frame index for every output frame (including crossfade blending pairs). A downstream
GPU/torch node can consume this plan to actually blend pixels.

Inputs are plain values (lists of ints, strings, numbers). No sockets, files, network,
subprocess, eval/exec, or dunder tricks are used.
"""

import math

CAT = "ParametricStudio/Video"

_TRANSITIONS = ("cut", "crossfade")


def _validate_clips(clips):
    """Validate the list of clip frame counts. Returns (counts, error)."""
    if clips is None:
        return None, "clips must be a list of positive frame counts"
    if not isinstance(clips, (list, tuple)):
        return None, "clips must be a list of positive frame counts"
    counts = []
    for i, c in enumerate(clips):
        if isinstance(c, bool) or not isinstance(c, int):
            return None, "clip %d frame count must be an integer" % i
        if c <= 0:
            return None, "clip %d frame count must be positive" % i
        counts.append(c)
    if len(counts) == 0:
        return None, "at least one clip is required"
    return counts, None


def _validate_transition(transition, transition_frames):
    """Validate transition type and frame count. Returns (transition, frames, error)."""
    if transition not in _TRANSITIONS:
        return None, None, "transition must be one of %s" % (list(_TRANSITIONS),)
    if isinstance(transition_frames, bool) or not isinstance(transition_frames, int):
        return None, None, "transition_frames must be an integer"
    if transition_frames < 0:
        return None, None, "transition_frames must be non-negative"
    return transition, transition_frames, None


def plan_merge(clips, transition="cut", transition_frames=0):
    """Build a pure-logic merge plan.

    Returns a dict with:
      - ok: bool
      - error: str or None
      - total_frames: int
      - transition: str
      - transition_frames: int (effective, clamped)
      - segments: list of (clip_index, start_frame, end_frame_exclusive)
      - blend_map: list of (out_index, (clip_a, frame_a), (clip_b, frame_b) or None)
        For cut, blend_map entries have None for the second source.
    """
    counts, err = _validate_clips(clips)
    if err:
        return {"ok": False, "error": err}
    transition, tframes, err = _validate_transition(transition, transition_frames)
    if err:
        return {"ok": False, "error": err}

    # Effective transition frames: cannot exceed the shorter of the two adjacent clips.
    # We compute per-boundary effective frames.
    n = len(counts)
    boundary_frames = []
    for i in range(n - 1):
        if transition == "crossfade":
            bf = min(tframes, counts[i], counts[i + 1])
        else:
            bf = 0
        boundary_frames.append(bf)

    # Build segments and blend map.
    segments = []
    blend_map = []
    out_index = 0

    for i in range(n):
        start = 0
        end = counts[i]
        # If this clip is the right side of a boundary, its first bf frames are
        # blended with the previous clip's last bf frames.
        if i > 0:
            bf = boundary_frames[i - 1]
            # The previous clip's last bf frames are already emitted as part of
            # the previous segment's tail. We need to re-map: the previous clip's
            # last bf frames should NOT be emitted as standalone; instead they
            # become blend pairs. So we trim the previous segment's end.
            # We'll handle this by adjusting after the fact.
            pass

    # Simpler approach: emit frames sequentially, handling overlaps.
    # For each boundary i (between clip i and i+1), the last bf frames of clip i
    # and the first bf frames of clip i+1 are blended into bf output frames.
    # The remaining frames of each clip are emitted as single-source frames.

    segments = []
    blend_map = []
    out_index = 0

    for i in range(n):
        bf_left = boundary_frames[i - 1] if i > 0 else 0
        bf_right = boundary_frames[i] if i < n - 1 else 0

        # Frames in clip i that are NOT part of any blend:
        # - If i > 0, the first bf_left frames are blended with clip i-1's tail.
        # - If i < n-1, the last bf_right frames are blended with clip i+1's head.
        # The middle (non-blended) frames are emitted as single-source.

        # Single-source frames from clip i:
        # Start after the left-blend region, end before the right-blend region.
        single_start = bf_left
        single_end = counts[i] - bf_right
        if single_start < single_end:
            seg_start = out_index
            for f in range(single_start, single_end):
                blend_map.append((out_index, (i, f), None))
                out_index += 1
            seg_end = out_index
            segments.append((i, single_start, single_end))

        # Right-blend frames (if i < n-1): blend clip i's tail with clip i+1's head.
        if i < n - 1:
            bf = boundary_frames[i]
            for k in range(bf):
                frame_a = counts[i] - bf + k
                frame_b = k
                blend_map.append((out_index, (i, frame_a), (i + 1, frame_b)))
                out_index += 1
            # Record the blend segment for clip i's tail
            segments.append((i, counts[i] - bf, counts[i]))

    total_frames = out_index
    return {
        "ok": True,
        "error": None,
        "total_frames": total_frames,
        "transition": transition,
        "transition_frames": tframes,
        "segments": segments,
        "blend_map": blend_map,
    }


class PSN_ClipMerger:
    """Plan the merge of multiple video clips with optional crossfade transitions.

    This node performs pure-logic planning only: it validates inputs and computes
    the merged frame count and per-frame source mapping. It does not process
    actual image tensors. A downstream GPU node should use the returned plan
    to perform the actual pixel blending.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clips": ("INT", {"default": 1, "min": 1, "max": 1000, "step": 1}),
                "transition": (list(_TRANSITIONS),),
                "transition_frames": ("INT", {"default": 0, "min": 0, "max": 10000, "step": 1}),
            },
            "optional": {
                "clip_frame_counts": ("STRING", {"default": "10,10", "multiline": False}),
            },
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("total_frames", "plan_json", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, clips, transition, transition_frames, clip_frame_counts="10,10"):
        # Parse clip frame counts from a comma-separated string.
        # If clips > 1 and clip_frame_counts is provided, use it; otherwise
        # assume each clip has 1 frame (placeholder for actual IMAGE batches).
        counts = []
        if clip_frame_counts and clip_frame_counts.strip():
            parts = [p.strip() for p in clip_frame_counts.split(",") if p.strip()]
            for p in parts:
                try:
                    v = int(p)
                except ValueError:
                    return (0, "", "invalid frame count in clip_frame_counts: %s" % p)
                counts.append(v)
        else:
            counts = [1] * clips

        # If clips count is specified and differs from parsed count, use the
        # parsed count if it's valid, otherwise fall back to clips count.
        if len(counts) == 0:
            counts = [1] * clips

        plan = plan_merge(counts, transition, transition_frames)
        if not plan["ok"]:
            return (0, "", plan["error"])

        import json
        plan_json = json.dumps({
            "total_frames": plan["total_frames"],
            "transition": plan["transition"],
            "transition_frames": plan["transition_frames"],
            "segments": plan["segments"],
            "blend_map": plan["blend_map"],
        })
        return (plan["total_frames"], plan_json, "")


NODE_CLASS_MAPPINGS = {
    "PSN_ClipMerger": PSN_ClipMerger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ClipMerger": "PSN Clip Merger (Plan)",
}
