"""ParametricStudio - Batch Scene Generation Queue.

Defines named scenes and automatically renders combinations for rapid
iteration.  Two nodes are provided:

* ``PSN_SceneQueueBuilder`` - combines a base prompt with a JSON list of
  scene variants and produces a flat list of full prompts.
* ``PSN_BatchExecutor`` - loops through the queue and produces one small
  placeholder IMAGE per prompt (deterministic, CPU, torch).

Data flow::

    PSN_SceneQueueBuilder -> PSN_BatchExecutor

Only ``torch`` (CPU) and the Python standard library are used.  No network,
no subprocess, no file I/O, no model weights.
"""

from __future__ import annotations

import json
import math

import torch

CAT = "ParametricStudio/SceneQueue"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _hash_prompt(prompt: str) -> int:
    """Deterministic 32-bit hash of a prompt string (stable across runs)."""
    h = 2166136261
    for ch in prompt:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _make_placeholder_image(prompt: str, height: int, width: int, channels: int) -> torch.Tensor:
    """Create a small deterministic placeholder IMAGE tensor [1,H,W,C] in 0..1.

    The image is a smooth gradient whose phase is derived from the prompt
    hash, so different prompts produce visibly different images while the
    whole thing stays fully deterministic and CPU-only.
    """
    h = _hash_prompt(prompt)
    phase = (h % 360) * math.pi / 180.0
    yy, xx = torch.meshgrid(
        torch.linspace(0.0, 1.0, height),
        torch.linspace(0.0, 1.0, width),
        indexing="ij",
    )
    base = 0.5 + 0.5 * torch.sin(2.0 * math.pi * (xx + yy) + phase)
    img = base.unsqueeze(-1).expand(1, height, width, channels).clone()
    # per-channel slight variation
    for c in range(channels):
        img[..., c] = _clamp01(0.85 + 0.15 * math.sin(phase + c)) * img[..., c]
    return img.clamp(0.0, 1.0)


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_SceneQueueBuilder:
    """Combine a base prompt with a JSON list of scene variants.

    ``scene_variants`` is a JSON string that must decode to a list of
    strings (or a single string).  Each variant is appended to
    ``base_prompt`` to form a full prompt.  The output is a flat
    ``LIST[STRING]`` of full prompts ready for generation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_prompt": ("STRING", {"default": "a detailed scene, 8k"}),
                "scene_variants": (
                    "STRING",
                    {
                        "default": '["a forest at dawn", "a city at night", "a beach at sunset"]',
                        "multiline": True,
                    },
                ),
            },
            "optional": {
                "separator": ("STRING", {"default": ", ", "multiline": False}),
            },
        }

    RETURN_TYPES = ("LIST[STRING]",)
    RETURN_NAMES = ("queue_items",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, base_prompt: str, scene_variants: str, separator: str = ", ") -> tuple:
        base = (base_prompt or "").strip()
        raw = (scene_variants or "").strip()
        if not raw:
            raise ValueError("scene_variants must be a non-empty JSON list of strings")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"scene_variants is not valid JSON: {exc}") from exc

        if isinstance(data, str):
            data = [data]
        if not isinstance(data, list):
            raise ValueError("scene_variants must decode to a JSON list of strings")
        if not data:
            raise ValueError("scene_variants list must not be empty")

        items = []
        for i, v in enumerate(data):
            if not isinstance(v, str):
                raise ValueError(f"scene_variants[{i}] must be a string, got {type(v).__name__}")
            v = v.strip()
            if not v:
                raise ValueError(f"scene_variants[{i}] is an empty string")
            full = f"{base}{separator}{v}" if base else v
            items.append(full)
        return (items,)


class PSN_BatchExecutor:
    """Loop through a queue of prompts and produce one placeholder IMAGE per item.

    This is a CPU-only, deterministic stand-in for a real sampler loop.  Each
    prompt is turned into a small gradient image whose appearance depends on
    the prompt hash, so different prompts yield different images.  The output
    is a ``LIST[IMAGE]`` (one ``[1,H,W,C]`` tensor per prompt).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "queue_items": ("LIST[STRING]",),
            },
            "optional": {
                "height": ("INT", {"default": 32, "min": 8, "max": 512}),
                "width": ("INT", {"default": 32, "min": 8, "max": 512}),
                "channels": ("INT", {"default": 3, "min": 1, "max": 4}),
            },
        }

    RETURN_TYPES = ("LIST[IMAGE]",)
    RETURN_NAMES = ("batch_results",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, queue_items, height: int = 32, width: int = 32, channels: int = 3) -> tuple:
        if queue_items is None:
            raise ValueError("queue_items must not be None")
        if not isinstance(queue_items, (list, tuple)):
            raise ValueError("queue_items must be a list of strings")
        if len(queue_items) == 0:
            raise ValueError("queue_items must not be empty")
        for i, p in enumerate(queue_items):
            if not isinstance(p, str):
                raise ValueError(f"queue_items[{i}] must be a string, got {type(p).__name__}")
            if not p.strip():
                raise ValueError(f"queue_items[{i}] is an empty string")

        results = []
        for p in queue_items:
            img = _make_placeholder_image(p, height, width, channels)
            results.append(img)
        return (results,)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_SceneQueueBuilder": PSN_SceneQueueBuilder,
    "PSN_BatchExecutor": PSN_BatchExecutor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SceneQueueBuilder": "PSN Scene Queue Builder",
    "PSN_BatchExecutor": "PSN Batch Executor",
}
