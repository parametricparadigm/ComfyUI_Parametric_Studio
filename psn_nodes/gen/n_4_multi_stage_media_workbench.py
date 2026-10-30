"""Multi-Stage Media Workbench for ComfyUI (ParametricStudio).

Chains image / video / audio processing stages inside a single graph.

Implemented with torch (CPU) + stdlib only.  The heavy dependencies listed
in the idea spec (Pillow, librosa) are NOT used: audio is represented as a
plain float tensor [B, T] in 0..1 and video as a float tensor [B, F, H, W, C]
in 0..1.  No real model inference (upscale / color-grade / audio-sync) is
performed; the built-in stages are deterministic, lightweight transforms that
stand in for the real operations so the orchestration, type conversion and
logging logic can be exercised end to end.
"""

import json

import torch

CAT = "ParametricStudio/MediaWorkbench"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_image(x):
    return isinstance(x, torch.Tensor) and x.dim() == 4 and x.shape[-1] in (1, 3, 4)


def _is_video(x):
    return isinstance(x, torch.Tensor) and x.dim() == 5 and x.shape[-1] in (1, 3, 4)


def _is_audio(x):
    return isinstance(x, torch.Tensor) and x.dim() == 2


def _asset_kind(x):
    if _is_image(x):
        return "IMAGE"
    if _is_video(x):
        return "VIDEO"
    if _is_audio(x):
        return "AUDIO"
    return "UNKNOWN"


def _clone(x):
    if isinstance(x, torch.Tensor):
        return x.detach().clone()
    return x


def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


# ---------------------------------------------------------------------------
# built-in stage transforms (deterministic stand-ins, no models)
# ---------------------------------------------------------------------------


def _stage_upscale(x, params):
    """Nearest-neighbour spatial upscale of IMAGE [B,H,W,C] or VIDEO [B,F,H,W,C]."""
    factor = int(params.get("factor", 2))
    if factor < 1:
        factor = 1
    if _is_image(x):
        b, h, w, c = x.shape
        flat = x.reshape(b, c, h, w)
        flat = torch.nn.functional.interpolate(flat, scale_factor=factor, mode="nearest")
        b2, c2, h2, w2 = flat.shape
        return _clamp01(flat.permute(0, 2, 3, 1).reshape(b2, h2, w2, c2))
    if _is_video(x):
        b, f, h, w, c = x.shape
        flat = x.reshape(b * f, c, h, w)
        flat = torch.nn.functional.interpolate(flat, scale_factor=factor, mode="nearest")
        b2, c2, h2, w2 = flat.shape
        return _clamp01(flat.permute(0, 2, 3, 1).reshape(b, f, h2, w2, c2))
    raise ValueError("upscale stage requires IMAGE or VIDEO input")


def _stage_color_grade(x, params):
    """Simple brightness/contrast grade on IMAGE or VIDEO."""
    brightness = float(params.get("brightness", 0.0))
    contrast = float(params.get("contrast", 1.0))
    if _is_image(x):
        return _clamp01((x - 0.5) * contrast + 0.5 + brightness)
    if _is_video(x):
        return _clamp01((x - 0.5) * contrast + 0.5 + brightness)
    raise ValueError("color_grade stage requires IMAGE or VIDEO input")


def _stage_normalize(x, params):
    """Rescale asset to 0..1 (idempotent clamp)."""
    return _clamp01(x)


def _stage_audio_sync(x, params):
    """Stand-in audio sync: resample audio [B,T] to a target length by
    linear interpolation (no librosa)."""
    if not _is_audio(x):
        raise ValueError("audio_sync stage requires AUDIO input")
    target = int(params.get("target_length", x.shape[-1]))
    if target < 1:
        target = 1
    b, t = x.shape
    if t == 1:
        out = x.expand(b, target).clone()
    else:
        pos = torch.linspace(0.0, t - 1, target)
        idx = pos.long().clamp(0, t - 1).unsqueeze(0).expand(b, target)
        out = x.gather(1, idx)
    return _clamp01(out)


def _stage_video_to_image(x, params):
    """Take the first frame of a VIDEO [B,F,H,W,C] -> IMAGE [B,H,W,C]."""
    if not _is_video(x):
        raise ValueError("video_to_image stage requires VIDEO input")
    return _clamp01(x[:, 0, :, :, :])


def _stage_image_to_video(x, params):
    """Repeat an IMAGE [B,H,W,C] into a VIDEO [B,F,H,W,C]."""
    if not _is_image(x):
        raise ValueError("image_to_video stage requires IMAGE input")
    frames = int(params.get("frames", 4))
    if frames < 1:
        frames = 1
    return _clamp01(x.unsqueeze(1).expand(x.shape[0], frames, x.shape[1], x.shape[2], x.shape[3]).clone())


STAGE_REGISTRY = {
    "upscale": _stage_upscale,
    "color_grade": _stage_color_grade,
    "normalize": _stage_normalize,
    "audio_sync": _stage_audio_sync,
    "video_to_image": _stage_video_to_image,
    "image_to_video": _stage_image_to_video,
}


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_MediaStageOrchestrator:
    """Execute a JSON-defined sequence of processing stages on a media asset.

    ``stage_config`` is a JSON string: a list of stage objects, each with a
    ``name`` (a key of the built-in stage registry) and optional ``params``.
    The asset is passed through the stages in order; the log records the
    kind of the asset before and after each stage.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stage_config": ("STRING", {"default": "[]", "multiline": True}),
                "input_asset": ("IMAGE,VIDEO,AUDIO",),
            }
        }

    RETURN_TYPES = ("IMAGE,VIDEO,AUDIO", "STRING")
    RETURN_NAMES = ("processed_asset", "stage_log")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, stage_config, input_asset):
        if not isinstance(input_asset, torch.Tensor):
            raise ValueError("input_asset must be a torch tensor (IMAGE/VIDEO/AUDIO)")

        try:
            config = json.loads(stage_config) if isinstance(stage_config, str) else stage_config
        except json.JSONDecodeError as exc:
            raise ValueError("stage_config is not valid JSON: %s" % exc)

        if not isinstance(config, list):
            raise ValueError("stage_config must be a JSON list of stage objects")

        asset = _clone(input_asset)
        log_lines = []
        for i, stage in enumerate(config):
            if not isinstance(stage, dict):
                raise ValueError("stage %d must be an object with a 'name'" % i)
            name = stage.get("name")
            if name not in STAGE_REGISTRY:
                raise ValueError("unknown stage name: %r" % (name,))
            params = stage.get("params", {}) or {}
            before = _asset_kind(asset)
            asset = STAGE_REGISTRY[name](asset, params)
            after = _asset_kind(asset)
            log_lines.append("stage %d: %s (%s -> %s)" % (i, name, before, after))

        return (asset, "\n".join(log_lines))


class PSN_AsTypeConverter:
    """Convert a media asset to a target type (IMAGE / VIDEO / AUDIO).

    Conversions are lossy stand-ins:
      * IMAGE -> VIDEO: repeat the image into ``frames`` frames.
      * VIDEO -> IMAGE: take the first frame.
      * IMAGE/AUDIO -> AUDIO: flatten the spatial channels into a 1-D signal.
      * AUDIO -> IMAGE: render the waveform as a single-channel image.
      * AUDIO -> VIDEO: render the waveform as a single-frame video.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_data": ("IMAGE,VIDEO,AUDIO",),
                "target_type": ("IMAGE,VIDEO,AUDIO",),
            },
            "optional": {
                "frames": ("INT", {"default": 4, "min": 1, "max": 256}),
            },
        }

    RETURN_TYPES = ("IMAGE,VIDEO,AUDIO",)
    RETURN_NAMES = ("converted_data",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, input_data, target_type, frames=4):
        if not isinstance(input_data, torch.Tensor):
            raise ValueError("input_data must be a torch tensor")
        if target_type not in ("IMAGE", "VIDEO", "AUDIO"):
            raise ValueError("target_type must be IMAGE, VIDEO or AUDIO")

        src = _asset_kind(input_data)
        x = _clone(input_data)

        if src == target_type:
            return (_clamp01(x),)

        if src == "IMAGE":
            if target_type == "VIDEO":
                n = max(1, int(frames))
                return (_clamp01(x.unsqueeze(1).expand(x.shape[0], n, x.shape[1], x.shape[2], x.shape[3]).clone()),)
            if target_type == "AUDIO":
                b, h, w, c = x.shape
                return (_clamp01(x.reshape(b, h * w * c)),)

        if src == "VIDEO":
            if target_type == "IMAGE":
                return (_clamp01(x[:, 0, :, :, :]),)
            if target_type == "AUDIO":
                b, f, h, w, c = x.shape
                return (_clamp01(x.reshape(b, f * h * w * c)),)

        if src == "AUDIO":
            b, t = x.shape
            if target_type == "IMAGE":
                # render waveform as a 1-channel image of height 1
                return (_clamp01(x.unsqueeze(1).unsqueeze(3)),)
            if target_type == "VIDEO":
                return (_clamp01(x.unsqueeze(1).unsqueeze(2).unsqueeze(4)),)

        raise ValueError("cannot convert UNKNOWN asset to %s" % target_type)


NODE_CLASS_MAPPINGS = {
    "PSN_MediaStageOrchestrator": PSN_MediaStageOrchestrator,
    "PSN_AsTypeConverter": PSN_AsTypeConverter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MediaStageOrchestrator": "Media Stage Orchestrator",
    "PSN_AsTypeConverter": "Asset Type Converter",
}
