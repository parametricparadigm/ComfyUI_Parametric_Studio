"""
PSN Technical Schematic Overlay nodes.

This module implements the pure-logic, secure-by-design parts of the
"Technical Schematic Overlay" spec. Because the spec requires GPU/torch/
ComfyUI internals and image libraries (Pillow, OpenCV) which are not allowed
here, these nodes operate on plain values (numbers, strings, JSON text) and
produce the *payload* that a downstream image-processing stage would consume.

- PSN_Schematic_Overlay: validates overlay parameters and emits a JSON
  payload describing the overlay (type, color, opacity, grid spec).
- PSN_Schematic_Annotation: validates annotation parameters and emits a JSON
  payload describing the text label and leader line.

No sockets, no file/OS access, no eval/exec, no torch/comfy imports.
"""

import json
import math

CAT = "ParametricStudio/Schematic"

# Allowed overlay types (allow-list)
_OVERLAY_TYPES = ("blueprint", "wireframe", "grid")

# Allowed color formats: hex (#RRGGBB or #RGB) or named colors from a small set
_NAMED_COLORS = (
    "white", "black", "red", "green", "blue", "yellow", "cyan",
    "magenta", "orange", "purple", "gray", "grey",
)


def _validate_hex_color(color):
    """Return True if color is a valid hex color string (#RGB or #RRGGBB)."""
    if not isinstance(color, str):
        return False
    c = color.strip()
    if not c.startswith("#"):
        return False
    body = c[1:]
    if len(body) not in (3, 6):
        return False
    for ch in body:
        if ch not in "0123456789abcdefABCDEF":
            return False
    return True


def _normalize_color(color):
    """Normalize a color string to a canonical form, or raise ValueError."""
    if not isinstance(color, str):
        raise ValueError("line_color must be a string")
    c = color.strip()
    if c in _NAMED_COLORS:
        return c
    if _validate_hex_color(c):
        # Expand #RGB to #RRGGBB
        body = c[1:]
        if len(body) == 3:
            body = "".join(ch * 2 for ch in body)
        return "#" + body.lower()
    raise ValueError(
        "line_color must be a named color (%s) or hex (#RGB/#RRGGBB)"
        % ", ".join(_NAMED_COLORS)
    )


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _build_overlay_payload(overlay_type, line_color, opacity):
    """Build the overlay payload dict. Raises ValueError on bad input."""
    if overlay_type not in _OVERLAY_TYPES:
        raise ValueError("overlay_type must be one of %s" % (list(_OVERLAY_TYPES),))
    color = _normalize_color(line_color)
    if not isinstance(opacity, (int, float)):
        raise ValueError("opacity must be a number")
    opacity = float(opacity)
    if math.isnan(opacity) or math.isinf(opacity):
        raise ValueError("opacity must be finite")
    opacity = _clamp(opacity, 0.0, 1.0)

    payload = {
        "node": "PSN_Schematic_Overlay",
        "overlay_type": overlay_type,
        "line_color": color,
        "opacity": round(opacity, 4),
    }

    # Type-specific parameters
    if overlay_type == "blueprint":
        payload["invert_colors"] = True
        payload["grid"] = {"enabled": True, "spacing_px": 32, "line_width": 1}
    elif overlay_type == "wireframe":
        payload["edge_detection"] = {"enabled": True, "method": "canny",
                                     "low_threshold": 50, "high_threshold": 150}
    elif overlay_type == "grid":
        payload["grid"] = {"enabled": True, "spacing_px": 32, "line_width": 1}

    return payload


def _build_annotation_payload(text, position_x, position_y, font_size):
    """Build the annotation payload dict. Raises ValueError on bad input."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if len(text) == 0:
        raise ValueError("text must be non-empty")
    if len(text) > 512:
        raise ValueError("text must be at most 512 characters")

    for name, val in (("position_x", position_x), ("position_y", position_y)):
        if not isinstance(val, (int, float)):
            raise ValueError("%s must be a number" % name)
        val = float(val)
        if math.isnan(val) or math.isinf(val):
            raise ValueError("%s must be finite" % name)

    if not isinstance(font_size, int):
        raise ValueError("font_size must be an integer")
    if font_size < 1 or font_size > 512:
        raise ValueError("font_size must be between 1 and 512")

    payload = {
        "node": "PSN_Schematic_Annotation",
        "text": text,
        "position": {"x": round(float(position_x), 4),
                     "y": round(float(position_y), 4)},
        "font_size": font_size,
        "leader_line": {"enabled": True, "style": "straight"},
    }
    return payload


class PSN_Schematic_Overlay:
    """
    Validates schematic overlay parameters and emits a JSON payload describing
    the overlay to apply (blueprint / wireframe / grid). The actual pixel
    manipulation is performed by a downstream image-processing stage.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "overlay_type": (list(_OVERLAY_TYPES),),
                "line_color": ("STRING", {"default": "#0000FF"}),
                "opacity": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0,
                                      "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("overlay_payload",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, overlay_type, line_color, opacity):
        payload = _build_overlay_payload(overlay_type, line_color, opacity)
        return (json.dumps(payload, sort_keys=True),)


class PSN_Schematic_Annotation:
    """
    Validates annotation parameters and emits a JSON payload describing a text
    label with a leader line. The actual text rendering is performed by a
    downstream image-processing stage.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "Label", "multiline": True}),
                "position_x": ("FLOAT", {"default": 100.0, "min": -1e9,
                                         "max": 1e9, "step": 0.1}),
                "position_y": ("FLOAT", {"default": 100.0, "min": -1e9,
                                         "max": 1e9, "step": 0.1}),
                "font_size": ("INT", {"default": 16, "min": 1, "max": 512}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("annotation_payload",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, text, position_x, position_y, font_size):
        payload = _build_annotation_payload(text, position_x, position_y, font_size)
        return (json.dumps(payload, sort_keys=True),)


NODE_CLASS_MAPPINGS = {
    "PSN_Schematic_Overlay": PSN_Schematic_Overlay,
    "PSN_Schematic_Annotation": PSN_Schematic_Annotation,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Schematic_Overlay": "PSN Schematic Overlay",
    "PSN_Schematic_Annotation": "PSN Schematic Annotation",
}
