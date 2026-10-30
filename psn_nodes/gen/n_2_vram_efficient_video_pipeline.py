"""VRAM-efficient video pipeline for ComfyUI (ParametricStudio).

Implements frame-to-frame video generation with sequential processing and
context caching to keep peak VRAM low on a shared GPU.  The heavy sampler
(`comfy.sample`) is not available in this environment, so the frame
generator uses a deterministic torch-based pseudo-sampler that mimics the
interface (takes prev-latent and returns a latent).

Nodes
-----
PSN_Video_Frame_Generator : generate one frame latent, optionally conditioned
                            on the previous frame's latent (temporal
                            consistency).  Intermediate activations are kept
                            on CPU to bound VRAM.
PSN_Video_Assembler       : decode a list of latents into a video tensor
                            [B, T, H, W, C] in 0..1.
PSN_Video_Frame_Loop      : convenience wrapper that runs the generator
                            sequentially for N frames.

Data flow
---------
PSN_Video_Frame_Generator (loop over frames) -> latents -> PSN_Video_Assembler
-> video
"""

import torch

CAT = "ParametricStudio/Video"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _latent_samples(latent):
    """Return the samples tensor from a LATENT dict, validating shape."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("LATENT must be a dict with a 'samples' key")
    x = latent["samples"]
    if not isinstance(x, torch.Tensor):
        raise ValueError("LATENT['samples'] must be a torch.Tensor")
    if x.dim() != 4:
        raise ValueError(
            "LATENT['samples'] must be 4-D [B, C, H, W], got %d-D" % x.dim()
        )
    return x


def _make_latent(samples):
    """Wrap a [B, C, H, W] tensor in a LATENT dict (new dict, no aliasing)."""
    return {"samples": samples}


def _clamp01(t):
    return torch.clamp(t, 0.0, 1.0)


def _deterministic_frame_latent(
    prev_latent, frame_index, total_frames, steps, cfg, seed
):
    """Deterministic pseudo-sampler.

    Produces a [B, C, H, W] latent that depends on the previous frame's
    latent (temporal consistency) and the frame index.  All computation is
    done on CPU to keep VRAM usage minimal.

    Parameters
    ----------
    prev_latent : torch.Tensor or None
        [B, C, H, W] latent from the previous frame, or None for frame 0.
    frame_index : int
        0-based index of the frame being generated.
    total_frames : int
        Total number of frames in the video.
    steps : int
        Number of sampling steps (affects the noise scale).
    cfg : float
        Classifier-free guidance scale.
    seed : int
        Base random seed.

    Returns
    -------
    torch.Tensor [B, C, H, W] in roughly 0..1.
    """
    if prev_latent is not None:
        x = _latent_samples(prev_latent)
        b, c, h, w = x.shape
        # temporal blend: mix previous latent with a frame-index offset
        t = float(frame_index) / max(1, total_frames - 1)
        offset = torch.full((b, c, h, w), t, dtype=x.dtype, device="cpu")
        # small deterministic noise based on frame index and seed
        g = torch.Generator(device="cpu").manual_seed(seed + frame_index)
        noise = torch.randn((b, c, h, w), generator=g, device="cpu")
        noise_scale = 0.1 / max(1, steps) * cfg
        out = 0.7 * x.cpu() + 0.3 * offset + noise_scale * noise
    else:
        # first frame: no previous latent, use a default shape
        b, c, h, w = 1, 4, 8, 8
        g = torch.Generator(device="cpu").manual_seed(seed + frame_index)
        noise = torch.randn((b, c, h, w), generator=g, device="cpu")
        t = float(frame_index) / max(1, total_frames - 1)
        offset = torch.full((b, c, h, w), t, device="cpu")
        noise_scale = 0.1 / max(1, steps) * cfg
        out = 0.5 + noise_scale * noise + 0.3 * offset

    return _clamp01(out)


def _decode_latent_to_frames(latent):
    """Decode a [B, C, H, W] latent into a [B, H, W, C] image tensor in 0..1.

    Uses a simple deterministic channel mapping (first 3 channels as RGB,
    or repeat if fewer) so the output is a valid IMAGE tensor.
    """
    x = _latent_samples(latent)
    b, c, h, w = x.shape
    # take first 3 channels (or repeat if fewer)
    if c >= 3:
        rgb = x[:, :3, :, :]
    elif c == 1:
        rgb = x.expand(b, 3, h, w)
    else:
        rgb = x.repeat(1, (3 + c - 1) // c, 1, 1)[:, :3, :, :]
    # [B, 3, H, W] -> [B, H, W, 3]
    img = rgb.permute(0, 2, 3, 1).contiguous()
    return _clamp01(img)


# ---------------------------------------------------------------------------
# Node 1: PSN_Video_Frame_Generator
# ---------------------------------------------------------------------------


class PSN_Video_Frame_Generator:
    """Generate a single video frame latent with temporal conditioning.

    Processes one frame at a time to keep peak VRAM low.  The previous
    frame's latent is blended into the current frame for temporal
    consistency.  All intermediate tensors are kept on CPU.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "total_frames": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0}),
                "sampler_name": (
                    ["euler", "euler_ancestral", "heun", "dpmpp_2m"],
                ),
                "scheduler": (
                    ["normal", "karras", "exponential", "sgm_uniform"],
                ),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
            },
            "optional": {
                "prev_latent": ("LATENT",),
            },
        }

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("current_latent", "next_prev_latent")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        frame_index,
        total_frames,
        steps,
        cfg,
        sampler_name,
        scheduler,
        seed,
        prev_latent=None,
    ):
        if frame_index < 0:
            raise ValueError("frame_index must be >= 0")
        if total_frames < 1:
            raise ValueError("total_frames must be >= 1")
        if frame_index >= total_frames:
            raise ValueError(
                "frame_index (%d) must be < total_frames (%d)"
                % (frame_index, total_frames)
            )
        if steps < 1:
            raise ValueError("steps must be >= 1")

        # validate prev_latent if provided
        if prev_latent is not None:
            _latent_samples(prev_latent)

        current = _deterministic_frame_latent(
            prev_latent, frame_index, total_frames, steps, cfg, seed
        )

        # next_prev_latent is the current frame's latent (to feed the next
        # iteration); return a copy so the caller cannot mutate our state.
        next_prev = current.clone()

        return (_make_latent(current), _make_latent(next_prev))


# ---------------------------------------------------------------------------
# Node 2: PSN_Video_Assembler
# ---------------------------------------------------------------------------


class PSN_Video_Assembler:
    """Decode a list of latents into a video tensor [B, T, H, W, C] in 0..1.

    Each latent in the list is decoded to an image and stacked along a new
    time axis.  The output is a plain torch tensor (VIDEO type in ComfyUI
    is a [B, T, H, W, C] float tensor in 0..1).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latents": ("LATENT",),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0}),
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latents, fps):
        if fps <= 0:
            raise ValueError("fps must be > 0")

        # latents can be a single LATENT dict or a list of LATENT dicts
        if isinstance(latents, dict):
            latent_list = [latents]
        elif isinstance(latents, (list, tuple)):
            latent_list = list(latents)
        else:
            raise ValueError(
                "latents must be a LATENT dict or a list of LATENT dicts"
            )

        if len(latent_list) == 0:
            raise ValueError("latents list must not be empty")

        frames = []
        for i, lat in enumerate(latent_list):
            if not isinstance(lat, dict):
                raise ValueError("latents[%d] is not a LATENT dict" % i)
            img = _decode_latent_to_frames(lat)
            frames.append(img)

        # all frames must have the same spatial size and batch
        ref = frames[0]
        for i, f in enumerate(frames[1:], 1):
            if f.shape != ref.shape:
                raise ValueError(
                    "frame %d shape %s != frame 0 shape %s"
                    % (i, tuple(f.shape), tuple(ref.shape))
                )

        # stack: [B, H, W, C] each -> [B, T, H, W, C]
        video = torch.stack(frames, dim=1).contiguous()
        return (video,)


# ---------------------------------------------------------------------------
# Node 3: PSN_Video_Frame_Loop  (convenience: run the generator N times)
# ---------------------------------------------------------------------------


class PSN_Video_Frame_Loop:
    """Run PSN_Video_Frame_Generator sequentially for *total_frames* frames.

    Returns the list of latents (as a list of LATENT dicts) ready for
    PSN_Video_Assembler.  This is the "loop" in the data flow diagram.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "total_frames": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 30.0}),
                "sampler_name": (
                    ["euler", "euler_ancestral", "heun", "dpmpp_2m"],
                ),
                "scheduler": (
                    ["normal", "karras", "exponential", "sgm_uniform"],
                ),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2**32 - 1}),
            },
        }

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latents",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, total_frames, steps, cfg, sampler_name, scheduler, seed):
        if total_frames < 1:
            raise ValueError("total_frames must be >= 1")

        gen = PSN_Video_Frame_Generator()
        latents = []
        prev = None
        for i in range(total_frames):
            cur, nxt = gen.run(
                frame_index=i,
                total_frames=total_frames,
                steps=steps,
                cfg=cfg,
                sampler_name=sampler_name,
                scheduler=scheduler,
                seed=seed,
                prev_latent=prev,
            )
            latents.append(cur)
            prev = nxt
        return (latents,)


# ---------------------------------------------------------------------------
# mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Video_Frame_Generator": PSN_Video_Frame_Generator,
    "PSN_Video_Assembler": PSN_Video_Assembler,
    "PSN_Video_Frame_Loop": PSN_Video_Frame_Loop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Frame_Generator": "PSN Video Frame Generator",
    "PSN_Video_Assembler": "PSN Video Assembler",
    "PSN_Video_Frame_Loop": "PSN Video Frame Loop",
}
