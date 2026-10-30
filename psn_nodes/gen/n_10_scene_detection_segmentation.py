"""ParametricStudio scene detection & segmentation nodes (torch CPU only)."""

import torch

CAT = "ParametricStudio/Video"


def _img(x):
    """Validate an IMAGE tensor: float [B,H,W,C] in 0..1."""
    if not isinstance(x, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError("IMAGE must be a 4D tensor [B,H,W,C]")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("IMAGE channels must be 1, 3 or 4")
    if not x.is_floating_point():
        raise TypeError("IMAGE must be a floating point tensor")
    if x.numel() and (x.min() < 0.0 or x.max() > 1.0):
        raise ValueError("IMAGE values must be in 0..1")
    return x


def _hist(frame, bins=16):
    """Normalized histogram of a single frame [H,W,C] in 0..1."""
    f = frame.reshape(-1, frame.shape[-1])
    h = torch.zeros(bins, frame.shape[-1])
    idx = (f * bins).clamp(0, bins - 1).long()
    for c in range(frame.shape[-1]):
        h[:, c] = torch.bincount(idx[:, c], minlength=bins).float()
    total = h.sum()
    if total > 0:
        h = h / total
    return h


def _frame_diff(a, b, bins=16):
    """Histogram difference between two frames (L1, 0..1 scale)."""
    return (_hist(a, bins) - _hist(b, bins)).abs().sum().item() / a.shape[-1]


class PSN_SceneDetector:
    """Detect scene changes in a video batch via histogram difference."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "threshold": ("FLOAT", {"default": 0.3, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("INT_LIST", "IMAGE")
    RETURN_NAMES = ("scene_indices", "marked_image")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, threshold):
        img = _img(image)
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise TypeError("threshold must be a number")
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("threshold must be in 0..1")

        b = img.shape[0]
        indices = []
        marked = img.clone()
        for i in range(1, b):
            d = _frame_diff(img[i - 1], img[i])
            if d >= threshold:
                indices.append(i)
                # mark the frame: bright red border overlay
                m = marked[i].clone()
                m[0:2, :, 0] = 1.0
                m[-2:, :, 0] = 1.0
                m[:, 0:2, 0] = 1.0
                m[:, -2:, 0] = 1.0
                marked[i] = m
        return (indices, marked)


class PSN_SegmentExtractor:
    """Slice a video batch into segments at scene change indices."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "scene_indices": ("INT_LIST",),
            }
        }

    RETURN_TYPES = ("IMAGE_LIST",)
    RETURN_NAMES = ("segments",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, scene_indices):
        img = _img(image)
        if not isinstance(scene_indices, (list, tuple)):
            raise TypeError("scene_indices must be a list of ints")
        b = img.shape[0]
        clean = []
        for s in scene_indices:
            if isinstance(s, bool) or not isinstance(s, int):
                raise TypeError("scene_indices entries must be ints")
            if s < 0 or s >= b:
                raise ValueError("scene index out of range")
            clean.append(s)
        clean = sorted(set(clean))

        segments = []
        start = 0
        for s in clean:
            if s > start:
                segments.append(img[start:s].clone())
            start = s
        if start < b:
            segments.append(img[start:b].clone())
        return (segments,)


NODE_CLASS_MAPPINGS = {
    "PSN_SceneDetector": PSN_SceneDetector,
    "PSN_SegmentExtractor": PSN_SegmentExtractor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SceneDetector": "PSN Scene Detector",
    "PSN_SegmentExtractor": "PSN Segment Extractor",
}
