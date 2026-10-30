"""ParametricStudio: Automated Batch Video Generation.

Core nodes that can be implemented with torch/stdlib only:
- PSN_MergeImageBatches: combine two IMAGE batches (concat or interleave).
- PSN_AssembleVideoFromBatch: pack an IMAGE batch into a VIDEO tensor
  (a plain float tensor [B, H, W, C] plus metadata dict) that a downstream
  encoder node (e.g. SaveVideo) can consume.

NOT implemented (needs ffmpeg / opencv / file IO which are forbidden here):
- actual mp4/webm file encoding (subprocess + ffmpeg),
- audio track muxing (AUDIO input is accepted but only validated, not mixed),
- file saving to disk.
"""

import torch

CAT = "ParametricStudio/Video"


def _as_image_tensor(x):
    """Validate/convert an IMAGE input to a float torch tensor [B,H,W,C] in 0..1."""
    if not isinstance(x, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError(f"IMAGE must be 4D [B,H,W,C], got {x.dim()}D")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError(f"IMAGE channels must be 1, 3 or 4, got {x.shape[-1]}")
    if not torch.is_floating_point(x):
        x = x.float()
    return x.detach().clone()


def _validate_fps(fps):
    if not isinstance(fps, (int, float)):
        raise TypeError("fps must be a number")
    fps = float(fps)
    if not (0.0 < fps <= 240.0):
        raise ValueError(f"fps must be in (0, 240], got {fps}")
    return fps


def _validate_format(fmt):
    if fmt not in ("mp4", "webm"):
        raise ValueError(f"format must be 'mp4' or 'webm', got {fmt!r}")
    return fmt


class PSN_MergeImageBatches:
    """Combine two image batches into one (concat or interleave)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "batch_a": ("IMAGE",),
                "batch_b": ("IMAGE",),
                "mode": (["concat", "interleave"], {"default": "concat"}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("merged_batch",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, batch_a, batch_b, mode):
        a = _as_image_tensor(batch_a)
        b = _as_image_tensor(batch_b)
        if a.shape[1:] != b.shape[1:]:
            raise ValueError(
                f"batch shapes must match on H,W,C: {tuple(a.shape)} vs {tuple(b.shape)}"
            )
        if mode == "concat":
            merged = torch.cat([a, b], dim=0)
        elif mode == "interleave":
            n = min(a.shape[0], b.shape[0])
            tail_a = a[n:]
            tail_b = b[n:]
            merged = torch.cat(
                [a[:n], b[:n], tail_a, tail_b], dim=0
            )
            # interleave properly: a0,b0,a1,b1,...
            inter = torch.stack([a[:n], b[:n]], dim=1).reshape(-1, *a.shape[1:])
            merged = torch.cat([inter, tail_a, tail_b], dim=0)
        else:
            raise ValueError(f"mode must be 'concat' or 'interleave', got {mode!r}")
        return (merged,)


class PSN_AssembleVideoFromBatch:
    """Pack an IMAGE batch into a VIDEO tensor with metadata.

    The VIDEO output is a dict {"frames": tensor [B,H,W,C] float 0..1,
    "fps": float, "format": str, "audio": optional tensor or None}.
    A downstream encoder node would consume this to write an actual file.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE",),
                "fps": ("FLOAT", {"default": 24.0, "min": 0.1, "max": 240.0}),
                "format": (["mp4", "webm"], {"default": "mp4"}),
            },
            "optional": {
                "audio_track": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_batch, fps, format, audio_track=None):
        frames = _as_image_tensor(image_batch)
        if frames.shape[0] == 0:
            raise ValueError("image_batch must contain at least one frame")
        fps = _validate_fps(fps)
        fmt = _validate_format(format)
        # clamp to 0..1 (inputs should already be in range, but be safe)
        frames = torch.clamp(frames, 0.0, 1.0)
        video = {
            "frames": frames,
            "fps": fps,
            "format": fmt,
            "audio": audio_track,
            "num_frames": int(frames.shape[0]),
            "duration": float(frames.shape[0]) / fps,
        }
        return (video,)


NODE_CLASS_MAPPINGS = {
    "PSN_MergeImageBatches": PSN_MergeImageBatches,
    "PSN_AssembleVideoFromBatch": PSN_AssembleVideoFromBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MergeImageBatches": "Merge Image Batches",
    "PSN_AssembleVideoFromBatch": "Assemble Video From Batch",
}
