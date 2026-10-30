"""PSN_BatchSeedGenerator: generates a deterministic list of integer seeds for batch processing.

This module is pure Python standard library only. It does not import torch, ComfyUI,
or perform any network, file, or OS access. It exposes a single ComfyUI-style node
that takes plain integer values and returns a list of integers (INT_LIST).

The node computes seeds as: seed_i = base_seed + i * offset, for i in range(count).
If offset is 0, all seeds will be identical to base_seed (deterministic, but not unique).
"""

from typing import List

# ComfyUI-style type alias for a list of integers
INT_LIST = "INT_LIST"

CAT = "ParametricStudio/Seeds"


class PSN_BatchSeedGenerator:
    """Generates a list of seeds based on a base seed and an offset."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "count": ("INT", {"default": 1, "min": 0, "max": 10000, "step": 1}),
                "base_seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1, "step": 1}),
                "offset": ("INT", {"default": 1, "min": -2**31, "max": 2**31 - 1, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = (INT_LIST,)
    RETURN_NAMES = ("seeds",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, count: int, base_seed: int, offset: int) -> tuple:
        """
        Generate a list of `count` seeds starting from `base_seed`,
        each subsequent seed incremented by `offset`.

        Args:
            count: Number of seeds to generate. Must be >= 0.
            base_seed: The starting seed value.
            offset: The step between consecutive seeds.

        Returns:
            A tuple containing a single list of integers.
        """
        # Clamp count to non-negative
        if count < 0:
            count = 0

        seeds: List[int] = []
        for i in range(count):
            seeds.append(base_seed + i * offset)

        return (seeds,)


NODE_CLASS_MAPPINGS = {
    "PSN_BatchSeedGenerator": PSN_BatchSeedGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_BatchSeedGenerator": "PSN Batch Seed Generator",
}
