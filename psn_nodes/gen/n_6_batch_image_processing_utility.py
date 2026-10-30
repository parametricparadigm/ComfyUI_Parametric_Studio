"""ParametricStudio - Batch Image Processing Utility.

Applies a predefined sequence of image filters to a whole batch of images
(ComfyUI IMAGE tensors, float32 [B, H, W, C] in 0..1) in one pass.

The filter chain is given as a JSON string, e.g.:

    '[{"name": "blur", "radius": 2}, {"name": "sharpen"}, {"name": "brightness", "value": 0.1}]'

Supported filters (all pure torch, CPU friendly, no in-place mutation):

    blur        - separable box blur, params: radius (int, default 1)
    sharpen     - unsharp mask, params: amount (float, default 1.0), radius (int, default 1)
    brightness  - additive brightness, params: value (float, default 0.0)
    contrast    - contrast around 0.5, params: value (float, default 1.0)
    saturate    - saturation, params: value (float, default 1.0)
    invert      - invert colors, no params
    gamma       - gamma correction, params: gamma (float, default 1.0)
    grayscale   - luminance to all channels, no params
    threshold   - binary threshold, params: level (float, default 0.5)
    flip_h      - horizontal flip, no params
    flip_v      - vertical flip, no params
    rotate90    - rotate 90 deg, params: times (int, default 1, 1..3)

The `parallel` flag controls whether the whole batch is processed as one
tensor op (vectorised, the fast path) or image-by-image in a Python loop
(the serial path).  Both paths produce identical results.
"""

import json
import math

import torch

CAT = "ParametricStudio/Batch"


def _as_image(image):
    """Validate and return a float32 CPU tensor [B, H, W, C] (a copy)."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image_batch must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image_batch must have shape [B, H, W, C], got %s" % (tuple(image.shape),))
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image_batch channel count must be 1, 3 or 4, got %d" % image.shape[-1])
    if image.shape[1] < 1 or image.shape[2] < 1:
        raise ValueError("image_batch spatial size must be >= 1")
    return image.detach().to(torch.float32).clone()


def _clamp01(x):
    return torch.clamp(x, 0.0, 1.0)


def _box_blur(x, radius):
    """Separable box blur on the spatial dims of [B, H, W, C]."""
    radius = int(radius)
    if radius < 1:
        return x
    k = 2 * radius + 1
    kernel = torch.full((1, 1, k, 1), 1.0 / k, dtype=x.dtype)
    kernel_v = torch.full((1, k, 1, 1), 1.0 / k, dtype=x.dtype)
    b, h, w, c = x.shape
    # conv2d wants [B, C, H, W]; depthwise via groups=c needs [c, 1, k, 1]
    kh = torch.full((c, 1, k, 1), 1.0 / k, dtype=x.dtype)
    kv = torch.full((c, 1, 1, k), 1.0 / k, dtype=x.dtype)
    y = x.permute(0, 3, 1, 2)
    y = torch.nn.functional.pad(y, (radius, radius, radius, radius), mode="replicate")
    y = torch.nn.functional.conv2d(y, kh, groups=c)
    y = torch.nn.functional.pad(y, (radius, radius, radius, radius), mode="replicate")
    y = torch.nn.functional.conv2d(y, kv, groups=c)
    y = y[..., :h, :w]
    return y.permute(0, 2, 3, 1)


def _filter_blur(x, params):
    radius = int(params.get("radius", 1))
    return _box_blur(x, radius)


def _filter_sharpen(x, params):
    amount = float(params.get("amount", 1.0))
    radius = int(params.get("radius", 1))
    blurred = _box_blur(x, radius)
    return _clamp01(x + amount * (x - blurred))


def _filter_brightness(x, params):
    value = float(params.get("value", 0.0))
    return _clamp01(x + value)


def _filter_contrast(x, params):
    value = float(params.get("value", 1.0))
    return _clamp01((x - 0.5) * value + 0.5)


def _filter_saturate(x, params):
    value = float(params.get("value", 1.0))
    if x.shape[-1] < 3:
        return x
    rgb = x[..., :3]
    lum = rgb @ torch.tensor([0.299, 0.587, 0.114], dtype=x.dtype)
    lum = lum.unsqueeze(-1)
    out = lum + value * (rgb - lum)
    if x.shape[-1] == 4:
        return torch.cat([out, x[..., 3:4]], dim=-1)
    return out


def _filter_invert(x, params):
    return 1.0 - x


def _filter_gamma(x, params):
    gamma = float(params.get("gamma", 1.0))
    if gamma <= 0:
        raise ValueError("gamma must be > 0")
    return torch.pow(torch.clamp(x, 0.0, 1.0), 1.0 / gamma)


def _filter_grayscale(x, params):
    if x.shape[-1] < 3:
        return x
    rgb = x[..., :3]
    lum = rgb @ torch.tensor([0.299, 0.587, 0.114], dtype=x.dtype)
    lum = lum.unsqueeze(-1).expand_as(rgb)
    if x.shape[-1] == 4:
        return torch.cat([lum, x[..., 3:4]], dim=-1)
    return lum


def _filter_threshold(x, params):
    level = float(params.get("level", 0.5))
    return (x >= level).to(x.dtype)


def _filter_flip_h(x, params):
    return torch.flip(x, dims=[2])


def _filter_flip_v(x, params):
    return torch.flip(x, dims=[1])


def _filter_rotate90(x, params):
    times = int(params.get("times", 1)) % 4
    if times == 0:
        return x
    return torch.rot90(x, times, dims=(1, 2))


_FILTERS = {
    "blur": _filter_blur,
    "sharpen": _filter_sharpen,
    "brightness": _filter_brightness,
    "contrast": _filter_contrast,
    "saturate": _filter_saturate,
    "invert": _filter_invert,
    "gamma": _filter_gamma,
    "grayscale": _filter_grayscale,
    "threshold": _filter_threshold,
    "flip_h": _filter_flip_h,
    "flip_v": _filter_flip_v,
    "rotate90": _filter_rotate90,
}


def parse_filter_chain(filter_chain):
    """Parse the JSON filter chain string into a list of (name, params) tuples.

    Accepts either a JSON list of objects ({"name": ..., ...}) or a JSON list
    of plain strings (filter names without params).  Returns a list of
    (name, params_dict) with validated names.
    """
    if not isinstance(filter_chain, str):
        raise TypeError("filter_chain must be a JSON string")
    try:
        data = json.loads(filter_chain)
    except json.JSONDecodeError as e:
        raise ValueError("filter_chain is not valid JSON: %s" % e)
    if not isinstance(data, list):
        raise ValueError("filter_chain must be a JSON list of filters")
    chain = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            name, params = item, {}
        elif isinstance(item, dict):
            name = item.get("name")
            params = {k: v for k, v in item.items() if k != "name"}
            if not isinstance(name, str):
                raise ValueError("filter %d: missing 'name' string" % i)
        else:
            raise ValueError("filter %d: must be a string or object" % i)
        key = name.strip().lower()
        if key not in _FILTERS:
            raise ValueError("unknown filter %r (supported: %s)" % (name, ", ".join(sorted(_FILTERS))))
        chain.append((key, params))
    return chain


def apply_filter_chain(image, chain, parallel=True):
    """Apply a parsed filter chain to an image batch.

    image: float32 tensor [B, H, W, C] in 0..1 (not modified).
    chain: list of (name, params) from parse_filter_chain.
    parallel: if True, process the whole batch as one tensor (vectorised);
              if False, loop over images one by one (serial).
    Returns a new tensor of the same shape, values clamped to 0..1.
    """
    x = _as_image(image)
    if parallel:
        for name, params in chain:
            x = _FILTERS[name](x, params)
        return _clamp01(x)
    outs = []
    for i in range(x.shape[0]):
        y = x[i:i + 1]
        for name, params in chain:
            y = _FILTERS[name](y, params)
        outs.append(_clamp01(y))
    return torch.cat(outs, dim=0)


class PSN_Batch_Filter_Chain:
    """Apply a JSON-defined sequence of filters to a whole image batch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_batch": ("IMAGE",),
                "filter_chain": ("STRING", {"default": "[]", "multiline": True}),
                "parallel": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_batch",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_batch, filter_chain, parallel):
        chain = parse_filter_chain(filter_chain)
        out = apply_filter_chain(image_batch, chain, parallel=bool(parallel))
        return (out,)


NODE_CLASS_MAPPINGS = {
    "PSN_Batch_Filter_Chain": PSN_Batch_Filter_Chain,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Batch_Filter_Chain": "Batch Filter Chain",
}
