"""ParametricStudio multimodal video frame analysis nodes.

Core logic implemented with torch (CPU) only:
- PSN_Scene_Transition_Detector: histogram-difference based scene change detection.
- PSN_Video_Frame_Captioner: frame selection + aggregation logic. The actual VLM
  call is NOT implemented (no llama-cpp-python / network allowed); instead the node
  accepts an optional `mock_responses` string (one response per selected frame,
  newline separated) so the aggregation pipeline can be exercised and tested.
"""

import json
import torch

CAT = "ParametricStudio/VideoAnalysis"


def _as_image_tensor(x):
    """Validate/convert input to a float torch tensor [B,H,W,C] in 0..1."""
    if not isinstance(x, torch.Tensor):
        raise TypeError("video_frames must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError("video_frames must have shape [B,H,W,C], got %s" % (tuple(x.shape),))
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("video_frames last dim must be 1, 3 or 4 channels, got %d" % x.shape[-1])
    t = x.detach().float().clone()
    return t


def _select_frames(frames, frame_interval):
    """Select every Nth frame (1-based interval). Returns (selected, indices)."""
    if frame_interval < 1:
        raise ValueError("frame_interval must be >= 1")
    n = frames.shape[0]
    idx = list(range(0, n, frame_interval))
    if not idx:
        idx = [0]
    return frames[idx], idx


def _histogram_diff(a, b, bins=16):
    """Histogram difference between two frames (H,W,C) -> scalar in [0,1].

    Uses per-channel 1D histograms over the flattened pixel values and the
    L1 distance between the two normalized histograms (sums to 1), halved so
    the maximum possible distance is 1.
    """
    a = a.reshape(-1, a.shape[-1])
    b = b.reshape(-1, b.shape[-1])
    total = 0.0
    for c in range(a.shape[-1]):
        ha = torch.histc(a[:, c], bins=bins, min=0.0, max=1.0).float()
        hb = torch.histc(b[:, c], bins=bins, min=0.0, max=1.0).float()
        sa = ha.sum()
        sb = hb.sum()
        if sa > 0:
            ha = ha / sa
        if sb > 0:
            hb = hb / sb
        total += (ha - hb).abs().sum().item()
    return total / (2.0 * a.shape[-1])


def _detect_boundaries(frames, threshold):
    """Return list of frame indices where a scene change starts (i.e. the index
    of the frame that differs from the previous one)."""
    boundaries = []
    for i in range(1, frames.shape[0]):
        d = _histogram_diff(frames[i - 1], frames[i])
        if d >= threshold:
            boundaries.append(i)
    return boundaries


def _aggregate_narrative(responses, indices, total_frames):
    """Build a continuous narrative string from per-frame responses."""
    parts = []
    for resp, idx in zip(responses, indices):
        parts.append("Frame %d: %s" % (idx, resp.strip()))
    narrative = " ".join(parts)
    if not narrative.strip():
        narrative = "(no frame descriptions available)"
    return narrative


def _key_moments(responses, indices, boundaries, total_frames):
    """Build a JSON list of {timestamp, description} for key moments.

    Key moments are the first frame, every detected scene boundary, and the
    last frame. Timestamps are expressed as frame indices (and a normalized
    0..1 position).
    """
    moments = []
    seen = set()
    ordered = [0] + [b for b in boundaries if b not in seen] + [total_frames - 1]
    for m in ordered:
        if m in seen:
            continue
        seen.add(m)
        # find the response for the closest selected frame <= m
        desc = ""
        for resp, idx in zip(responses, indices):
            if idx <= m:
                desc = resp.strip()
        moments.append({
            "frame": int(m),
            "timestamp": round(m / max(1, total_frames - 1), 4),
            "description": desc,
        })
    return json.dumps(moments)


class PSN_Scene_Transition_Detector:
    """Detect scene changes in a batch of video frames via histogram difference."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_frames": ("IMAGE",),
                "threshold": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
                "bins": ("INT", {"default": 16, "min": 4, "max": 64}),
            }
        }

    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("scene_boundaries", "boundary_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video_frames, threshold, bins):
        frames = _as_image_tensor(video_frames)
        boundaries = _detect_boundaries(frames, threshold)
        return (tuple(boundaries), json.dumps(boundaries))


class PSN_Video_Frame_Captioner:
    """Select frames by interval and aggregate per-frame descriptions into a
    narrative plus a JSON list of key moments.

    NOTE: the actual multimodal LLM call is NOT implemented (no network / no
    llama-cpp-python available in this environment). Provide `mock_responses`
    (one description per selected frame, newline separated) to drive the
    aggregation logic; when empty, placeholder descriptions are used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_frames": ("IMAGE",),
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 256}),
                "mock_responses": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("scene_description", "key_moments")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video_frames, frame_interval, mock_responses):
        frames = _as_image_tensor(video_frames)
        selected, indices = _select_frames(frames, frame_interval)
        total_frames = frames.shape[0]

        provided = [r for r in (mock_responses or "").splitlines() if r.strip() != ""]
        if len(provided) >= len(indices):
            responses = provided[:len(indices)]
        else:
            responses = list(provided) + ["(frame %d)" % i for i in indices[len(provided):]]

        boundaries = _detect_boundaries(frames, 0.35)
        narrative = _aggregate_narrative(responses, indices, total_frames)
        moments = _key_moments(responses, indices, boundaries, total_frames)
        return (narrative, moments)


NODE_CLASS_MAPPINGS = {
    "PSN_Scene_Transition_Detector": PSN_Scene_Transition_Detector,
    "PSN_Video_Frame_Captioner": PSN_Video_Frame_Captioner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Scene_Transition_Detector": "PSN Scene Transition Detector",
    "PSN_Video_Frame_Captioner": "PSN Video Frame Captioner",
}
