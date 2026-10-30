"""PSN Smart LoRA Management – selective block loading for LoRA weights."""

import torch

CAT = "ParametricStudio/LoRA"


def _parse_blocks(blocks_to_load: str):
    """Parse a comma-separated string of block indices into a sorted list of ints."""
    if not isinstance(blocks_to_load, str):
        raise TypeError("blocks_to_load must be a string")
    parts = [p.strip() for p in blocks_to_load.split(",") if p.strip()]
    if not parts:
        raise ValueError("blocks_to_load must contain at least one block index")
    indices = []
    for p in parts:
        try:
            idx = int(p)
        except ValueError:
            raise ValueError(f"Invalid block index: {p!r}")
        if idx < 0:
            raise ValueError(f"Block index must be non-negative, got {idx}")
        indices.append(idx)
    return sorted(set(indices))


class PSN_SmartLoRALoader:
    """Load a LoRA with selective block loading to optimize VRAM usage.

    Accepts a synthetic LoRA representation (dict mapping block index -> tensor)
    and returns only the requested blocks, scaled by the given strength.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lora_path": ("STRING", {"default": ""}),
                "blocks_to_load": ("STRING", {"default": "0,1,2"}),
                "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("LOADED_LORA",)
    RETURN_NAMES = ("loaded_lora",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, lora_path: str, blocks_to_load: str, strength: float):
        """Filter LoRA weights to the specified blocks and apply strength scaling.

        In a real ComfyUI environment, `lora_path` would point to a .safetensors
        file. Here we simulate the LoRA as a dict of {block_index: tensor}.
        The caller is expected to pass the LoRA weights via the `lora_path`
        parameter as a JSON-like string, or we generate a synthetic one for
        demonstration/testing.

        Returns a dict: {"blocks": {idx: tensor}, "strength": float, "path": str}
        """
        if not isinstance(lora_path, str):
            raise TypeError("lora_path must be a string")
        if not isinstance(strength, (int, float)):
            raise TypeError("strength must be a number")

        block_indices = _parse_blocks(blocks_to_load)

        # In a real implementation we would load the safetensors file here.
        # For this self-contained module we build a synthetic LoRA so the
        # node is fully testable without external files.
        synthetic_lora = self._synthetic_lora(lora_path)

        # Filter to requested blocks
        filtered = {}
        for idx in block_indices:
            if idx in synthetic_lora:
                filtered[idx] = synthetic_lora[idx].clone() * float(strength)
            else:
                # Block not present in the LoRA – skip silently (it may not exist)
                pass

        if not filtered:
            raise ValueError(
                f"None of the requested blocks {block_indices} exist in the LoRA "
                f"(available: {sorted(synthetic_lora.keys())})"
            )

        return ({"blocks": filtered, "strength": float(strength), "path": lora_path},)

    @staticmethod
    def _synthetic_lora(lora_path: str):
        """Generate a deterministic synthetic LoRA dict for testing.

        Creates 8 blocks (0-7), each a small 4x4 tensor seeded by the path
        string so results are reproducible.
        """
        seed = sum(ord(c) for c in lora_path) % (2**31) if lora_path else 42
        g = torch.Generator().manual_seed(seed)
        lora = {}
        for i in range(8):
            lora[i] = torch.randn(4, 4, generator=g) * 0.1
        return lora


NODE_CLASS_MAPPINGS = {
    "PSN_SmartLoRALoader": PSN_SmartLoRALoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SmartLoRALoader": "Smart LoRA Loader (Selective Blocks)",
}
