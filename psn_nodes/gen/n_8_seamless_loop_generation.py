"""ParametricStudio - Seamless Loop Generation.

Two nodes:
  * PSN_LoopPreparer  - blends the last N frames with the first N frames so the
                        video can be played as a seamless loop.
  * PSN_LoopAssembler - trims / repeats the prepared batch so that the output
                        contains exactly ``loop_length`` frames.

Both nodes operate on ComfyUI IMAGE tensors (float, [B, H, W, C], 0..1) and
never modify their inputs in place.
"""

import torch

CAT = "ParametricStudio/Loop"


def _as_image(x):
    """Validate and return a float tensor of shape [B, H, W, C]."""
    if not isinstance(x, torch.Tensor):
        raise TypeError("IMAGE input must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError(f"IMAGE must be 4-D [B,H,W,C], got {x.dim()}-D")
    if x.shape[-1] not in (1, 3, 4):
        raise ValueError(f"last dim must be 1/3/4 channels, got {x.shape[-1]}")
    if x.shape[0] < 1:
        raise ValueError("batch size must be >= 1")
    return x.float()


def _clamp01(t):
    return t.clamp_(0.0, 1.0)


def _blend_weights(n, blend):
    """Return per-frame weights for the cross-fade region.

    For frame index i in [0, n):
      * i < n - blend: weight 1.0 (keep original)
      * i >= n - blend: linear ramp from 0 -> 1 (blend with the tail)
    """
    w = torch.ones(n, dtype=torch.float32)
    if blend > 0:
        for i in range(n - blend, n):
            t = (i - (n - blend)) / max(blend - 1, 1)
            w[i] = t
    return w


class PSN_LoopPreparer:
    """Blend the last N frames with the first N frames for a seamless loop."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "loop_length": ("INT", {"default": 16, "min": 2, "max": 4096}),
                "blend_frames": ("INT", {"default": 4, "min": 0, "max": 1024}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, loop_length, blend_frames):
        x = _as_image(image)
        b, h, w, c = x.shape
        n = int(loop_length)
        blend = int(blend_frames)
        if n < 2:
            raise ValueError("loop_length must be >= 2")
        if blend < 0:
            raise ValueError("blend_frames must be >= 0")
        blend = min(blend, n - 1)

        # Take the first n frames (or wrap around if the batch is shorter).
        if b >= n:
            head = x[:n]
        else:
            reps = (n + b - 1) // b
            head = x.repeat(reps, 1, 1, 1)[:n]

        # Cross-fade: for the last `blend` frames, mix with the corresponding
        # frames from the start of the loop so the tail flows into the head.
        out = head.clone()
        if blend > 0:
            tail = head[-blend:]
            head_part = head[:blend]
            w = _blend_weights(n, blend)
            ramp = w[n - blend:]
            for i in range(blend):
                # weight of the *head* frame in the mix
                a = ramp[i]
                out[n - blend + i] = a * head_part[i] + (1.0 - a) * tail[i]
        return (_clamp01(out),)


class PSN_LoopAssembler:
    """Assemble the final seamless loop of exactly ``loop_length`` frames."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "loop_length": ("INT", {"default": 16, "min": 1, "max": 4096}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, loop_length):
        x = _as_image(image)
        b = x.shape[0]
        n = int(loop_length)
        if n < 1:
            raise ValueError("loop_length must be >= 1")
        if b >= n:
            out = x[:n].clone()
        else:
            reps = (n + b - 1) // b
            out = x.repeat(reps, 1, 1, 1)[:n]
        return (_clamp01(out),)


NODE_CLASS_MAPPINGS = {
    "PSN_LoopPreparer": PSN_LoopPreparer,
    "PSN_LoopAssembler": PSN_LoopAssembler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LoopPreparer": "Loop Preparer (Seamless Blend)",
    "PSN_LoopAssembler": "Loop Assembler (Seamless)",
}
