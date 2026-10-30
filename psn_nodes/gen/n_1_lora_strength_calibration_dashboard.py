"""
PSN LoRA Strength Calibration Dashboard (pure-logic core).

This module implements the *logic* of a LoRA strength calibration dashboard
without any GPU, torch, ComfyUI, or image I/O. It provides:

1. PSN_LoRA_Sweep_Config: validates and packages a sweep configuration,
   computing the list of strength values to test.
2. PSN_LoRA_Grid_Generator: given a sweep config and grid dimensions,
   produces a list of cell descriptors (strength, row, col, metadata string)
   that a downstream GPU node would use to actually generate images.
3. PSN_LoRA_Grid_Assembler: given a list of cell descriptors and grid
   dimensions, computes the final grid layout (dimensions, label positions)
   that a downstream image-stitching node would use.

All functions take plain values (numbers, strings, lists) and return plain
values. No sockets, no file access, no eval/exec, no torch.
"""

from psn import expr, orchestration as _orch

class _AnyType(str):
    """ComfyUI wildcard socket type: compares equal to every type."""
    def __ne__(self, other): return False
ANY = _AnyType("*")


CAT = "ParametricStudio/LoRA"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_strength_range(strength_min, strength_max):
    """Validate that strength_min <= strength_max and both are finite."""
    if not isinstance(strength_min, (int, float)):
        raise ValueError("strength_min must be a number")
    if not isinstance(strength_max, (int, float)):
        raise ValueError("strength_max must be a number")
    if strength_min > strength_max:
        raise ValueError("strength_min must be <= strength_max")
    if strength_min != strength_min or strength_max != strength_max:  # NaN check
        raise ValueError("strength values must not be NaN")
    return True


def _compute_strength_values(strength_min, strength_max, steps):
    """
    Compute the list of strength values for the sweep.
    steps is the number of distinct strength values to generate.
    If steps == 1, return [strength_min].
    Otherwise, linearly interpolate from strength_min to strength_max.
    """
    if not isinstance(steps, int):
        raise ValueError("steps must be an integer")
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if steps == 1:
        return [float(strength_min)]
    delta = (float(strength_max) - float(strength_min)) / (steps - 1)
    return [float(strength_min) + i * delta for i in range(steps)]


def _validate_grid_dims(grid_cols, grid_rows):
    """Validate grid dimensions are positive integers."""
    if not isinstance(grid_cols, int) or grid_cols < 1:
        raise ValueError("grid_cols must be a positive integer")
    if not isinstance(grid_rows, int) or grid_rows < 1:
        raise ValueError("grid_rows must be a positive integer")
    return True


def _build_metadata(strength, row, col, seed, prompt):
    """Build a metadata string for a grid cell."""
    return (
        f"strength={strength:.4f} row={row} col={col} "
        f"seed={seed} prompt={prompt!r}"
    )


# ---------------------------------------------------------------------------
# Node 1: PSN_LoRA_Sweep_Config
# ---------------------------------------------------------------------------

class PSN_LoRA_Sweep_Config:
    """
    Defines the parameter space for a LoRA strength sweep.
    Validates inputs and computes the list of strength values.
    Outputs a sweep_config dict that downstream nodes consume.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "strength_min": ("FLOAT", {"default": 0.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "strength_max": ("FLOAT", {"default": 1.0, "min": -1e9, "max": 1e9, "step": 0.001}),
                "steps": ("INT", {"default": 5, "min": 1, "max": 1000}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1}),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "lora_model": (ANY,),
                "checkpoint": (ANY,),
                "vae": (ANY,),
            },
        }

    RETURN_TYPES = ("PSN_SWEEP_CONFIG",)
    RETURN_NAMES = ("sweep_config",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, strength_min, strength_max, steps, seed, prompt, negative_prompt,
            lora_model=None, checkpoint=None, vae=None):
        _validate_strength_range(strength_min, strength_max)
        strength_values = _compute_strength_values(strength_min, strength_max, steps)
        sweep_config = {
            "strength_min": float(strength_min),
            "strength_max": float(strength_max),
            "steps": int(steps),
            "strength_values": strength_values,
            "seed": int(seed),
            "prompt": str(prompt),
            "negative_prompt": str(negative_prompt),
            "lora_model": lora_model,
            "checkpoint": checkpoint,
            "vae": vae,
        }
        return (sweep_config,)


# ---------------------------------------------------------------------------
# Node 2: PSN_LoRA_Grid_Generator
# ---------------------------------------------------------------------------

class PSN_LoRA_Grid_Generator:
    """
    Given a sweep config and grid dimensions, produces a list of cell
    descriptors. Each descriptor contains the strength value, row, col,
    and a metadata string. A downstream GPU node would use these to
    actually run the KSampler for each cell.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sweep_config": ("PSN_SWEEP_CONFIG",),
                "grid_cols": ("INT", {"default": 3, "min": 1, "max": 50}),
                "grid_rows": ("INT", {"default": 3, "min": 1, "max": 50}),
            },
        }

    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("cell_descriptors", "metadata_list")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sweep_config, grid_cols, grid_rows):
        _validate_grid_dims(grid_cols, grid_rows)
        if not isinstance(sweep_config, dict):
            raise ValueError("sweep_config must be a dict")
        if "strength_values" not in sweep_config:
            raise ValueError("sweep_config missing 'strength_values'")
        if "seed" not in sweep_config:
            raise ValueError("sweep_config missing 'seed'")
        if "prompt" not in sweep_config:
            raise ValueError("sweep_config missing 'prompt'")

        strength_values = sweep_config["strength_values"]
        seed = sweep_config["seed"]
        prompt = sweep_config["prompt"]

        total_cells = grid_cols * grid_rows
        if len(strength_values) < total_cells:
            # Cycle through strength values if there are more cells than values
            pass

        cell_descriptors = []
        metadata_list = []
        for idx in range(total_cells):
            row = idx // grid_cols
            col = idx % grid_cols
            strength = strength_values[idx % len(strength_values)]
            meta = _build_metadata(strength, row, col, seed, prompt)
            cell_descriptors.append({
                "strength": strength,
                "row": row,
                "col": col,
                "index": idx,
            })
            metadata_list.append(meta)

        return (cell_descriptors, metadata_list)


# ---------------------------------------------------------------------------
# Node 3: PSN_LoRA_Grid_Assembler
# ---------------------------------------------------------------------------

class PSN_LoRA_Grid_Assembler:
    """
    Given cell descriptors, metadata, and grid dimensions, computes the
    final grid layout: overall dimensions and per-cell label positions.
    A downstream image-stitching node would use this layout to compose
    the final grid image with labels.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cell_descriptors": ("LIST",),
                "metadata_list": ("LIST",),
                "grid_cols": ("INT", {"default": 3, "min": 1, "max": 50}),
                "grid_rows": ("INT", {"default": 3, "min": 1, "max": 50}),
                "cell_width": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "cell_height": ("INT", {"default": 512, "min": 1, "max": 8192}),
                "label_font_size": ("INT", {"default": 24, "min": 1, "max": 200}),
            },
        }

    RETURN_TYPES = ("INT", "INT", "LIST")
    RETURN_NAMES = ("grid_width", "grid_height", "label_positions")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, cell_descriptors, metadata_list, grid_cols, grid_rows,
            cell_width, cell_height, label_font_size):
        _validate_grid_dims(grid_cols, grid_rows)
        if not isinstance(cell_width, int) or cell_width < 1:
            raise ValueError("cell_width must be a positive integer")
        if not isinstance(cell_height, int) or cell_height < 1:
            raise ValueError("cell_height must be a positive integer")
        if not isinstance(label_font_size, int) or label_font_size < 1:
            raise ValueError("label_font_size must be a positive integer")

        if not isinstance(cell_descriptors, list):
            raise ValueError("cell_descriptors must be a list")
        if not isinstance(metadata_list, list):
            raise ValueError("metadata_list must be a list")
        if len(cell_descriptors) != grid_cols * grid_rows:
            raise ValueError(
                f"cell_descriptors length {len(cell_descriptors)} does not match "
                f"grid size {grid_cols}x{grid_rows}={grid_cols * grid_rows}"
            )
        if len(metadata_list) != grid_cols * grid_rows:
            raise ValueError(
                f"metadata_list length {len(metadata_list)} does not match "
                f"grid size {grid_cols}x{grid_rows}={grid_cols * grid_rows}"
            )

        grid_width = grid_cols * cell_width
        grid_height = grid_rows * cell_height

        label_positions = []
        for idx, desc in enumerate(cell_descriptors):
            row = desc.get("row", idx // grid_cols)
            col = desc.get("col", idx % grid_cols)
            x = col * cell_width
            y = row * cell_height
            # Label is placed at the top-left of each cell with a small offset
            label_x = x + 4
            label_y = y + 4
            label_positions.append({
                "index": idx,
                "x": label_x,
                "y": label_y,
                "font_size": label_font_size,
                "text": metadata_list[idx] if idx < len(metadata_list) else "",
            })

        return (grid_width, grid_height, label_positions)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_LoRA_Sweep_Config": PSN_LoRA_Sweep_Config,
    "PSN_LoRA_Grid_Generator": PSN_LoRA_Grid_Generator,
    "PSN_LoRA_Grid_Assembler": PSN_LoRA_Grid_Assembler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LoRA_Sweep_Config": "LoRA Sweep Config",
    "PSN_LoRA_Grid_Generator": "LoRA Grid Generator",
    "PSN_LoRA_Grid_Assembler": "LoRA Grid Assembler",
}
