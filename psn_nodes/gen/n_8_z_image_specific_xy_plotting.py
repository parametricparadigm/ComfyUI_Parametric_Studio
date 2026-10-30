"""
PSN Z-Image Specific XY Plotting (pure-logic core).

This module implements the configuration, validation, and matrix-generation
logic for Z-Image specific XY plotting. It does NOT perform GPU inference,
image generation, or file I/O. Instead, it provides:

- Parameter validation and allow-listing for Z-Image specific parameters.
- Parsing of comma-separated value strings into typed lists.
- Generation of a parameter matrix (list of label strings) for the plot grid.
- A config dict that downstream (GPU) nodes can consume.

The node classes follow the ComfyUI custom node conventions but operate on
plain Python values only.
"""

from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAT = "ParametricStudio/ZImagePlot"

# Parameters that are valid for Z-Image plotting
_ZIMAGE_PARAMS = ("steps", "cfg", "guidance")

# Z-Image specific defaults applied when z_image_specific is True
_ZIMAGE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "steps": {"min": 1, "max": 100, "default": 20},
    "cfg": {"min": 1.0, "max": 30.0, "default": 5.0},
    "guidance": {"min": 0.0, "max": 10.0, "default": 2.0},
}

# When z_image_specific is False, we allow a broader range
_GENERIC_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "steps": {"min": 1, "max": 200, "default": 20},
    "cfg": {"min": 0.0, "max": 100.0, "default": 7.0},
    "guidance": {"min": 0.0, "max": 20.0, "default": 2.0},
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_values(raw: str, param: str, z_image_specific: bool) -> List[Any]:
    """
    Parse a comma-separated string of values for the given parameter.
    Returns a list of ints or floats depending on the parameter type.
    Raises ValueError if any value is out of range or not parseable.
    """
    if not raw or not raw.strip():
        raise ValueError(f"Values string for '{param}' is empty.")

    defaults = _ZIMAGE_DEFAULTS if z_image_specific else _GENERIC_DEFAULTS
    bounds = defaults.get(param)
    if bounds is None:
        raise ValueError(f"Unknown parameter: {param}")

    min_val = bounds["min"]
    max_val = bounds["max"]

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError(f"No valid values found for '{param}'.")

    is_int_param = (param == "steps")
    result: List[Any] = []
    for part in parts:
        try:
            if is_int_param:
                val = int(part)
            else:
                val = float(part)
        except ValueError:
            raise ValueError(f"Cannot parse '{part}' as a number for '{param}'.")

        if val < min_val or val > max_val:
            raise ValueError(
                f"Value {val} for '{param}' is out of range [{min_val}, {max_val}]."
            )
        result.append(val)

    return result


def _build_param_matrix(
    x_param: str,
    x_values: List[Any],
    y_param: str,
    y_values: List[Any],
) -> List[str]:
    """
    Build a list of label strings representing each cell in the XY grid.
    Each label is formatted as 'x_param=x_val, y_param=y_val'.
    The grid is row-major: for each y value, iterate over all x values.
    """
    matrix: List[str] = []
    for y_val in y_values:
        for x_val in x_values:
            label = f"{x_param}={x_val}, {y_param}={y_val}"
            matrix.append(label)
    return matrix


# ---------------------------------------------------------------------------
# Node 1: PSN_ZImage_Plot_Config
# ---------------------------------------------------------------------------

class PSN_ZImage_Plot_Config:
    """
    Configures the Z-Image XY plot. Validates parameters and values,
    applies Z-Image specific defaults when enabled, and outputs a config
    dict along with the parsed value lists and the parameter matrix.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x_param": (list(_ZIMAGE_PARAMS),),
                "x_values": ("STRING", {"default": "10,20,30"}),
                "y_param": (list(_ZIMAGE_PARAMS),),
                "y_values": ("STRING", {"default": "1.0,2.0,3.0"}),
                "z_image_specific": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("PSN_ZIMAGE_PLOT_CONFIG", "LIST", "LIST", "LIST")
    RETURN_NAMES = ("plot_config", "x_values_parsed", "y_values_parsed", "param_matrix")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        x_param: str,
        x_values: str,
        y_param: str,
        y_values: str,
        z_image_specific: bool,
    ) -> Tuple[Dict[str, Any], List[Any], List[Any], List[str]]:
        # Validate that x_param and y_param are different (optional but sensible)
        # We allow same param but warn via reason; for now just proceed.

        x_parsed = _parse_values(x_values, x_param, z_image_specific)
        y_parsed = _parse_values(y_values, y_param, z_image_specific)

        matrix = _build_param_matrix(x_param, x_parsed, y_param, y_parsed)

        defaults = _ZIMAGE_DEFAULTS if z_image_specific else _GENERIC_DEFAULTS

        config: Dict[str, Any] = {
            "x_param": x_param,
            "x_values": x_parsed,
            "y_param": y_param,
            "y_values": y_parsed,
            "z_image_specific": z_image_specific,
            "defaults": {
                "x": defaults.get(x_param, {}),
                "y": defaults.get(y_param, {}),
            },
            "param_matrix": matrix,
            "grid_size": (len(y_parsed), len(x_parsed)),  # (rows, cols)
        }

        return (config, x_parsed, y_parsed, matrix)


# ---------------------------------------------------------------------------
# Node 2: PSN_ZImage_Grid_Generator (pure-logic stub)
# ---------------------------------------------------------------------------

class PSN_ZImage_Grid_Generator:
    """
    Pure-logic stub for the grid generator. In a full ComfyUI environment
    this would invoke Z-Image sampling. Here it validates the config and
    returns a placeholder structure representing what would be generated.
    No GPU, no model, no image data is produced.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "plot_config": ("PSN_ZIMAGE_PLOT_CONFIG",),
                "prompt": ("STRING", {"default": "a z-image test"}),
                "negative_prompt": ("STRING", {"default": ""}),
                "width": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
                "height": ("INT", {"default": 512, "min": 64, "max": 4096, "step": 64}),
            },
        }

    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("grid_placeholders", "param_matrix")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        plot_config: Dict[str, Any],
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        if not isinstance(plot_config, dict):
            raise TypeError("plot_config must be a dict.")

        matrix = plot_config.get("param_matrix", [])
        if not matrix:
            raise ValueError("plot_config has an empty param_matrix.")

        # Build placeholder entries for each cell
        placeholders: List[Dict[str, Any]] = []
        for i, label in enumerate(matrix):
            placeholders.append({
                "index": i,
                "label": label,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "z_image_specific": plot_config.get("z_image_specific", False),
            })

        return (placeholders, matrix)


# ---------------------------------------------------------------------------
# Node 3: PSN_ZImage_Grid_Visualizer (pure-logic stub)
# ---------------------------------------------------------------------------

class PSN_ZImage_Grid_Visualizer:
    """
    Pure-logic stub for the grid visualizer. In a full ComfyUI environment
    this would assemble images into a grid with labels. Here it validates
    inputs and returns a summary dict describing the grid layout.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "grid_placeholders": ("LIST",),
                "param_matrix": ("LIST",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("grid_summary",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        grid_placeholders: List[Dict[str, Any]],
        param_matrix: List[str],
    ) -> Tuple[str,]:
        if not isinstance(grid_placeholders, list):
            raise TypeError("grid_placeholders must be a list.")
        if not isinstance(param_matrix, list):
            raise TypeError("param_matrix must be a list.")

        if len(grid_placeholders) != len(param_matrix):
            raise ValueError(
                f"Length mismatch: {len(grid_placeholders)} placeholders vs {len(param_matrix)} matrix entries."
            )

        if not grid_placeholders:
            return ("Empty grid.",)

        # Determine grid dimensions from the first placeholder's config if available
        # For the summary, just report count and a few labels
        count = len(grid_placeholders)
        sample_labels = param_matrix[:4]
        summary = (
            f"Z-Image Grid: {count} cells. "
            f"Sample labels: {', '.join(sample_labels)}"
        )
        return (summary,)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_ZImage_Plot_Config": PSN_ZImage_Plot_Config,
    "PSN_ZImage_Grid_Generator": PSN_ZImage_Grid_Generator,
    "PSN_ZImage_Grid_Visualizer": PSN_ZImage_Grid_Visualizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ZImage_Plot_Config": "Z-Image Plot Config",
    "PSN_ZImage_Grid_Generator": "Z-Image Grid Generator",
    "PSN_ZImage_Grid_Visualizer": "Z-Image Grid Visualizer",
}
