import time

import torch

CAT = "ParametricStudio/Realtime"


def _as_image(x):
    """Coerce an input into a float torch tensor [B,H,W,C] in 0..1 (a copy, never in place)."""
    if isinstance(x, dict):
        x = x.get("samples")
    if not isinstance(x, torch.Tensor):
        raise TypeError("expected an IMAGE tensor [B,H,W,C] (or LATENT dict)")
    x = x.detach().float().clone()
    if x.dim() == 3:
        x = x.unsqueeze(0)
    if x.dim() != 4:
        raise ValueError("IMAGE must be [B,H,W,C] (or [H,W,C])")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError("last dim of IMAGE must be 1, 3 or 4 channels")
    return x


def _clamp01(x):
    return x.clamp_(0.0, 1.0)


class PSN_Realtime_Loop:
    """Emits frames from a batched frame source at a target FPS.

    The node is stateless per call: it returns the next frame of the batch
    (advancing an internal cursor) and reports whether it was the last one.
    A real-time pacing delay is applied between emissions when `pacing` is
    enabled; tests disable pacing to stay fast.
    """

    _state = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_source": ("IMAGE",),
                "fps": ("FLOAT", {"default": 30.0, "min": 0.1, "max": 240.0}),
            },
            "optional": {
                "pacing": ("BOOLEAN", {"default": False}),
                "reset": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN")
    RETURN_NAMES = ("frame", "is_last")
    FUNCTION = "run"
    CATEGORY = CAT

    @classmethod
    def _cursor(cls, key):
        return cls._state.setdefault(key, 0)

    @classmethod
    def _key(cls, frame_source):
        return id(frame_source)

    def run(self, frame_source, fps, pacing=False, reset=False):
        frames = _as_image(frame_source)
        if fps <= 0:
            raise ValueError("fps must be positive")
        key = self._key(frame_source)
        if reset:
            self._state[key] = 0
        idx = self._cursor(key)
        n = frames.shape[0]
        if idx >= n:
            # wrap around so the loop keeps emitting (real-time loop semantics)
            idx = 0
            self._state[key] = 0
        frame = _clamp01(frames[idx: idx + 1].clone())
        is_last = (idx == n - 1)
        self._state[key] = idx + 1
        if pacing and not is_last:
            time.sleep(1.0 / float(fps))
        return (frame, is_last)


class PSN_Motion_Detect:
    """Detects motion between two frames via per-pixel absolute difference.

    Produces a single-channel grayscale motion mask [B,H,W,1] in 0..1 and a
    scalar motion score (mean difference over the batch).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame": ("IMAGE",),
                "previous_frame": ("IMAGE",),
            },
            "optional": {
                "threshold": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0}),
            },
        }

    RETURN_TYPES = ("IMAGE", "FLOAT")
    RETURN_NAMES = ("motion_mask", "motion_score")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, frame, previous_frame, threshold=0.0):
        a = _as_image(frame)
        b = _as_image(previous_frame)
        if a.shape != b.shape:
            raise ValueError("frame and previous_frame must have identical shapes")
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("threshold must be in [0,1]")
        # reduce channels to a single grayscale intensity
        ga = a.mean(dim=-1, keepdim=True)
        gb = b.mean(dim=-1, keepdim=True)
        diff = (ga - gb).abs()
        motion_score = float(diff.mean().item())
        mask = (diff > threshold).float()
        return (mask, motion_score)


NODE_CLASS_MAPPINGS = {
    "PSN_Realtime_Loop": PSN_Realtime_Loop,
    "PSN_Motion_Detect": PSN_Motion_Detect,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Realtime_Loop": "Realtime Loop (FPS)",
    "PSN_Motion_Detect": "Motion Detect",
}
