"""ParametricStudio - Multi-Reference Video Scheduler (idea 10).

Splits a long video prompt into planned segments and assigns a subset of
reference images to each segment based on keyword matching. A second node
adjusts the per-reference influence weight to prevent over-fitting.

Implemented with torch (CPU) and the Python standard library only. No heavy
models, no network, no file I/O.
"""

import re
import torch

CAT = "ParametricStudio/Storyboard"

# Custom data type name used in RETURN_TYPES. ComfyUI treats unknown type
# strings as opaque pass-through values, so we pass plain Python dicts.
PSN_STORYBOARD_DATA = "PSN_STORYBOARD_DATA"

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "is", "are", "was", "were", "be", "being", "it",
    "its", "this", "that", "these", "those", "then", "than", "so", "as", "into",
    "over", "under", "after", "before", "while", "during", "when", "where",
}


def _tokenize(text):
    """Lowercase word tokens, length >= 3, minus stopwords."""
    out = []
    for tok in re.findall(r"[a-zA-Z][a-zA-Z']*", text or ""):
        w = tok.lower()
        if len(w) >= 3 and w not in _STOPWORDS:
            out.append(w)
    return out


def _split_sentences(text):
    """Split on sentence boundaries, keeping order."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _validate_image(img, idx):
    """Validate one IMAGE tensor; return a shallow copy (never in place)."""
    if not torch.is_tensor(img):
        raise ValueError(f"reference_images[{idx}] is not a torch tensor")
    if img.dim() != 4 or img.shape[0] != 1 or img.shape[-1] not in (1, 3, 4):
        raise ValueError(
            f"reference_images[{idx}] must be [1,H,W,C] with C in (1,3,4), got {tuple(img.shape)}"
        )
    if img.min() < -1e-6 or img.max() > 1 + 1e-6:
        raise ValueError(f"reference_images[{idx}] values must be in 0..1")
    return img.clone()


def _build_segments(long_prompt, segment_duration):
    """Split prompt into sentences, group into segments of given duration.

    Returns list of dicts: {index, start, end, text, tokens}.
    """
    sentences = _split_sentences(long_prompt)
    if not sentences:
        return []
    # Each sentence is one "beat" of 1.0 time unit; segment_duration groups
    # ceil(1/segment_duration) sentences per segment (min 1 sentence).
    per_seg = max(1, int(round(1.0 / max(segment_duration, 1e-6))))
    segments = []
    for i in range(0, len(sentences), per_seg):
        chunk = sentences[i:i + per_seg]
        text = " ".join(chunk)
        segments.append({
            "index": len(segments),
            "start": round(i * segment_duration, 6),
            "end": round((i + len(chunk)) * segment_duration, 6),
            "text": text,
            "tokens": _tokenize(text),
        })
    return segments


def _match_references(segments, ref_keywords):
    """Assign reference indices to each segment by keyword overlap.

    ref_keywords: list of token lists, one per reference image.
    A reference is assigned to a segment if any of its keywords appear in
    the segment tokens. If no reference matches a segment, all references
    are assigned (fallback) so the segment is never empty.
    """
    for seg in segments:
        seg_tokens = set(seg["tokens"])
        matched = []
        for ridx, kws in enumerate(ref_keywords):
            if any(k in seg_tokens for k in kws):
                matched.append(ridx)
        if not matched:
            matched = list(range(len(ref_keywords)))
        seg["reference_indices"] = matched
    return segments


class PSN_MultiRefScheduler:
    """Split a long prompt into segments and assign reference images by keyword."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "long_prompt": ("STRING", {"default": "", "multiline": True}),
                "reference_images": ("IMAGE",),
                "reference_keywords": ("STRING", {"default": "", "multiline": True}),
                "segment_duration": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 60.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = (PSN_STORYBOARD_DATA,)
    RETURN_NAMES = ("segment_plan",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, long_prompt, reference_images, reference_keywords, segment_duration):
        if not isinstance(long_prompt, str) or not long_prompt.strip():
            raise ValueError("long_prompt must be a non-empty string")
        if not torch.is_tensor(reference_images):
            raise ValueError("reference_images must be a torch tensor [B,H,W,C]")
        if reference_images.dim() != 4 or reference_images.shape[0] < 1:
            raise ValueError(f"reference_images must be [B,H,W,C] with B>=1, got {tuple(reference_images.shape)}")
        if reference_images.shape[-1] not in (1, 3, 4):
            raise ValueError(f"reference_images last dim must be 1,3 or 4, got {reference_images.shape[-1]}")
        if reference_images.min() < -1e-6 or reference_images.max() > 1 + 1e-6:
            raise ValueError("reference_images values must be in 0..1")
        if not isinstance(reference_keywords, str):
            raise ValueError("reference_keywords must be a string")
        if segment_duration <= 0:
            raise ValueError("segment_duration must be > 0")

        n_refs = reference_images.shape[0]
        # Parse keywords: one line per reference, comma-separated words.
        lines = [ln.strip() for ln in reference_keywords.splitlines() if ln.strip()]
        if len(lines) > n_refs:
            raise ValueError(f"reference_keywords has {len(lines)} lines but only {n_refs} reference images")
        ref_keywords = []
        for i in range(n_refs):
            line = lines[i] if i < len(lines) else ""
            kws = _tokenize(line)
            ref_keywords.append(kws)

        segments = _build_segments(long_prompt, segment_duration)
        if not segments:
            raise ValueError("long_prompt produced no segments")
        _match_references(segments, ref_keywords)

        # Build output plan: list of dicts (PSN_STORYBOARD_DATA).
        plan = []
        for seg in segments:
            plan.append({
                "segment_index": seg["index"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "reference_indices": list(seg["reference_indices"]),
                "reference_weights": [1.0] * len(seg["reference_indices"]),
            })
        return (plan,)


class PSN_RefWeightAdjuster:
    """Scale per-reference weights in a segment plan to prevent over-fitting."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "segment_plan": (PSN_STORYBOARD_DATA,),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = (PSN_STORYBOARD_DATA,)
    RETURN_NAMES = ("weighted_plan",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, segment_plan, strength):
        if not isinstance(segment_plan, (list, tuple)):
            raise ValueError("segment_plan must be a list of segment dicts")
        if not isinstance(strength, (int, float)) or not (0.0 <= float(strength) <= 2.0):
            raise ValueError("strength must be a number in [0, 2]")
        s = float(strength)
        out = []
        for i, seg in enumerate(segment_plan):
            if not isinstance(seg, dict):
                raise ValueError(f"segment_plan[{i}] is not a dict")
            new_seg = dict(seg)  # shallow copy, never mutate input
            weights = seg.get("reference_weights", [])
            if not isinstance(weights, (list, tuple)):
                raise ValueError(f"segment_plan[{i}].reference_weights must be a list")
            new_weights = [max(0.0, min(2.0, float(w) * s)) for w in weights]
            new_seg["reference_weights"] = new_weights
            out.append(new_seg)
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_MultiRefScheduler": PSN_MultiRefScheduler,
    "PSN_RefWeightAdjuster": PSN_RefWeightAdjuster,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MultiRefScheduler": "Multi-Reference Video Scheduler",
    "PSN_RefWeightAdjuster": "Reference Weight Adjuster",
}
