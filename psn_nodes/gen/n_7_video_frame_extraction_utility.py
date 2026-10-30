"""ParametricStudio - Video Frame Extraction Utility.

Extracts specific frames from a video batch (IMAGE tensor [B,H,W,C])
for analysis or as input for subsequent image-based pipelines.
"""

import torch

CAT = "ParametricStudio/Video"


def _as_tensor(x):
    if isinstance(x, torch.Tensor):
        return x
    raise TypeError("expected a torch.Tensor")


def _validate_image(img):
    t = _as_tensor(img)
    if t.dim() != 4:
        raise ValueError(f"IMAGE must be 4D [B,H,W,C], got {t.dim()}D")
    if t.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE last dim must be 1/3/4 channels, got {t.shape[-1]}")
    if not torch.is_floating_point(t):
        raise TypeError("IMAGE must be a floating point tensor")
    return t


def _parse_indices(frame_indices, n_frames):
    """Parse frame_indices (int, list/tuple, or comma string) into a list of ints.

    Negative indices wrap from the end. Out-of-range values raise ValueError.
    Duplicates are preserved (order kept, no dedup) so the caller can request
    the same frame twice if needed.
    """
    if isinstance(frame_indices, str):
        parts = [p.strip() for p in frame_indices.split(",") if p.strip()]
        if not parts:
            raise ValueError("frame_indices string is empty")
        raw = [int(p) for p in parts]
    elif isinstance(frame_indices, (list, tuple)):
        raw = [int(p) for p in frame_indices]
    elif isinstance(frame_indices, (int,)) and not isinstance(frame_indices, bool):
        raw = [int(frame_indices)]
    else:
        raise TypeError("frame_indices must be int, list/tuple of int, or comma string")

    if not raw:
        raise ValueError("frame_indices must contain at least one index")

    out = []
    for i in raw:
        if i < -n_frames or i >= n_frames:
            raise ValueError(f"frame index {i} out of range for {n_frames} frames")
        out.append(i % n_frames)
    return out


def _build_info(indices, n_frames, fps):
    parts = [f"extracted={len(indices)}", f"total={n_frames}", f"indices={indices}"]
    if fps is not None:
        parts.append(f"fps={fps}")
        if fps > 0:
            times = [i / fps for i in indices]
            parts.append(f"times={[round(t, 4) for t in times]}")
    return " | ".join(parts)


class PSN_Video_Frame_Extract:
    """Extract specific frames from a video batch (IMAGE [B,H,W,C]).

    Returns the selected frames as a new IMAGE tensor plus a STRING with
    metadata (indices, count, optional fps/timestamps).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "frame_indices": ("INT", {"default": 0, "min": 0, "max": 4096}),
            },
            "optional": {
                "fps": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 240.0}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "frame_info")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, frame_indices, fps=0.0):
        img = _validate_image(image)
        n = img.shape[0]
        if n == 0:
            raise ValueError("image batch is empty (B=0)")

        # ComfyUI passes a single INT for the INT widget; allow list/tuple/string
        # for programmatic use. A plain int means "that one frame".
        if isinstance(frame_indices, (list, tuple, str)):
            idx = _parse_indices(frame_indices, n)
        else:
            idx = _parse_indices([int(frame_indices)], n)

        # Build a gather index tensor and index_select (no in-place mutation).
        idx_t = torch.tensor(idx, dtype=torch.long, device=img.device)
        selected = img.index_select(0, idx_t).contiguous()

        info = _build_info(idx, n, fps if fps and fps > 0 else None)
        return (selected, info)


NODE_CLASS_MAPPINGS = {
    "PSN_Video_Frame_Extract": PSN_Video_Frame_Extract,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Frame_Extract": "Video Frame Extract (ParametricStudio)",
}
