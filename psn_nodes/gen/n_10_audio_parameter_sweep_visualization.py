"""
PSN Audio Parameter Sweep Visualization (pure-logic core).

This module implements the *pure-logic, secure-by-design* portion of the
"Audio Parameter Sweep Visualization" spec. It does NOT generate audio,
render images, or touch the GPU. Instead it provides:

  * PSN_Audio_Sweep_Config   - validates and normalizes the sweep parameter
                               space (x/y param + comma-separated value lists).
  * PSN_Audio_Sweep_Plan     - expands the validated config into an ordered
                               list of (param, value) combinations and emits
                               human-readable metadata labels.
  * PSN_Audio_Waveform_Layout - computes the grid geometry (cols/rows/cells)
                               and per-cell pixel rectangles for a waveform
                               grid, given a clip count and target canvas size.

All functions take plain values (numbers, strings) and return plain values
(numbers, strings, tuples, lists, dicts). No torch, no ComfyUI, no network,
no file/OS access, no eval/exec.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUDIO_PARAMS = ("steps", "cfg", "duration")

# Sensible per-parameter bounds used for validation.
_PARAM_BOUNDS = {
    "steps": (1, 10000),
    "cfg": (0.0, 100.0),
    "duration": (0.01, 600.0),
}

# Default canvas size for the waveform grid (pixels).
_DEFAULT_CANVAS_W = 1024
_DEFAULT_CANVAS_H = 1024
_DEFAULT_COLS = 4
_DEFAULT_ROWS = 4
_CELL_GAP = 8  # pixels between cells


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_value_list(raw, param):
    """Parse a comma-separated string of numbers into a list of floats.

    Returns (values, error). On success error is None.
    """
    if not isinstance(raw, str):
        return None, "x_values/y_values must be a string"
    text = raw.strip()
    if not text:
        return None, "value list is empty"
    parts = [p.strip() for p in text.split(",")]
    values = []
    lo, hi = _PARAM_BOUNDS[param]
    for i, part in enumerate(parts):
        if part == "":
            return None, "empty entry in value list"
        try:
            v = float(part)
        except (ValueError, TypeError):
            return None, "non-numeric value %r at index %d" % (part, i)
        if not math.isfinite(v):
            return None, "non-finite value at index %d" % i
        if v < lo or v > hi:
            return None, "value %s out of range [%s, %s] for %s" % (
                part, lo, hi, param)
        values.append(v)
    return values, None


def _validate_param(param):
    if param not in _AUDIO_PARAMS:
        return None, "unknown parameter %r" % (param,)
    return param, None


# ---------------------------------------------------------------------------
# Node 1: PSN_Audio_Sweep_Config
# ---------------------------------------------------------------------------

class PSN_Audio_Sweep_Config:
    """Defines and validates the parameter space for an audio sweep."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x_param": (list(_AUDIO_PARAMS),),
                "x_values": ("STRING", {"default": "1,2,3"}),
                "y_param": (list(_AUDIO_PARAMS),),
                "y_values": ("STRING", {"default": "1,2,3"}),
            }
        }

    RETURN_TYPES = ("PSN_AUDIO_SWEEP_CONFIG",)
    RETURN_NAMES = ("sweep_config",)
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, x_param, x_values, y_param, y_values):
        xp, err = _validate_param(x_param)
        if err:
            raise ValueError(err)
        yp, err = _validate_param(y_param)
        if err:
            raise ValueError(err)
        xv, err = _parse_value_list(x_values, xp)
        if err:
            raise ValueError("x_values: " + err)
        yv, err = _parse_value_list(y_values, yp)
        if err:
            raise ValueError("y_values: " + err)
        config = {
            "x_param": xp,
            "x_values": xv,
            "y_param": yp,
            "y_values": yv,
        }
        return (config,)


# ---------------------------------------------------------------------------
# Node 2: PSN_Audio_Sweep_Plan
# ---------------------------------------------------------------------------

class PSN_Audio_Sweep_Plan:
    """Expands a sweep config into an ordered list of parameter combinations.

    Pure logic: produces the list of (param, value) pairs and a list of
    human-readable metadata labels. No audio is generated here.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sweep_config": ("PSN_AUDIO_SWEEP_CONFIG",),
            }
        }

    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("combinations", "metadata_list")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, sweep_config):
        if not isinstance(sweep_config, dict):
            raise ValueError("sweep_config must be a dict")
        for key in ("x_param", "x_values", "y_param", "y_values"):
            if key not in sweep_config:
                raise ValueError("sweep_config missing key %r" % key)
        xp = sweep_config["x_param"]
        xv = sweep_config["x_values"]
        yp = sweep_config["y_param"]
        yv = sweep_config["y_values"]
        if not isinstance(xv, (list, tuple)) or not isinstance(yv, (list, tuple)):
            raise ValueError("x_values/y_values must be lists")
        if len(xv) == 0 or len(yv) == 0:
            raise ValueError("value lists must be non-empty")

        combinations = []
        metadata_list = []
        for y_val in yv:
            for x_val in xv:
                combinations.append((xp, x_val, yp, y_val))
                metadata_list.append("%s=%s %s=%s" % (
                    xp, x_val, yp, y_val))
        return (combinations, metadata_list)


# ---------------------------------------------------------------------------
# Node 3: PSN_Audio_Waveform_Layout
# ---------------------------------------------------------------------------

class PSN_Audio_Waveform_Layout:
    """Computes the grid geometry for a waveform visualization.

    Given a number of audio clips and a target canvas size, returns the
    number of columns, rows, total cells, and a list of per-cell rectangles
    (x, y, w, h) in pixels. Pure geometry, no image rendering.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip_count": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "cols": ("INT", {"default": _DEFAULT_COLS, "min": 1, "max": 64}),
                "rows": ("INT", {"default": _DEFAULT_ROWS, "min": 1, "max": 64}),
                "canvas_w": ("INT", {"default": _DEFAULT_CANVAS_W, "min": 1, "max": 16384}),
                "canvas_h": ("INT", {"default": _DEFAULT_CANVAS_H, "min": 1, "max": 16384}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "LIST")
    RETURN_NAMES = ("cols", "rows", "total_cells", "cell_rects")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, clip_count, cols, rows, canvas_w, canvas_h):
        if clip_count < 1:
            raise ValueError("clip_count must be >= 1")
        if cols < 1 or rows < 1:
            raise ValueError("cols and rows must be >= 1")
        if canvas_w < 1 or canvas_h < 1:
            raise ValueError("canvas dimensions must be >= 1")

        total_cells = cols * rows
        if clip_count > total_cells:
            raise ValueError(
                "clip_count %d exceeds grid capacity %d (cols=%d, rows=%d)"
                % (clip_count, total_cells, cols, rows))

        cell_w = (canvas_w - (cols - 1) * _CELL_GAP) // cols
        cell_h = (canvas_h - (rows - 1) * _CELL_GAP) // rows
        if cell_w < 1:
            cell_w = 1
        if cell_h < 1:
            cell_h = 1

        cell_rects = []
        for idx in range(clip_count):
            r = idx // cols
            c = idx % cols
            x = c * (cell_w + _CELL_GAP)
            y = r * (cell_h + _CELL_GAP)
            cell_rects.append((x, y, cell_w, cell_h))

        return (cols, rows, total_cells, cell_rects)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Audio_Sweep_Config": PSN_Audio_Sweep_Config,
    "PSN_Audio_Sweep_Plan": PSN_Audio_Sweep_Plan,
    "PSN_Audio_Waveform_Layout": PSN_Audio_Waveform_Layout,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Audio_Sweep_Config": "Audio Sweep Config",
    "PSN_Audio_Sweep_Plan": "Audio Sweep Plan",
    "PSN_Audio_Waveform_Layout": "Audio Waveform Layout",
}
