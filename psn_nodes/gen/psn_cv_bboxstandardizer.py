"""PSN_CV_BBoxStandardizer: pure-logic bounding box format standardizer.

Converts bounding boxes between XYXY, XYWH, and Center formats, clamps
coordinates to the image bounds, and emits per-box spatial metadata
(area, aspect ratio, centroid) as a JSON string.

This module is pure Python standard library only. It performs no file,
network, subprocess, or GPU/torch/ComfyUI I/O. All inputs are plain
values (lists of numbers, strings, ints) and all outputs are plain
values (lists of numbers, JSON strings).
"""

import json

CAT = "ParametricStudio/CV"

_INPUT_FORMATS = ("xywh", "xyxy", "center")
_OUTPUT_FORMATS = ("xyxy", "xywh", "center")


def _is_number(value):
    """Return True if value is a real number (int/float, not bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _clamp(value, low, high):
    """Clamp value into [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _to_xyxy(box, image_width, image_height, input_fmt):
    """Convert a single box (in any supported format) to clamped XYXY.

    Returns a tuple (x1, y1, x2, y2) or raises ValueError.
    """
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError("each bbox must be a list/tuple of 4 numbers")
    if not all(_is_number(v) for v in box):
        raise ValueError("each bbox coordinate must be a number")

    x, y, w, h = (float(v) for v in box)

    if input_fmt == "xywh":
        x1 = x
        y1 = y
        x2 = x + w
        y2 = y + h
    elif input_fmt == "xyxy":
        x1 = x
        y1 = y
        x2 = w
        y2 = h
    elif input_fmt == "center":
        x1 = x - w / 2.0
        y1 = y - h / 2.0
        x2 = x + w / 2.0
        y2 = y + h / 2.0
    else:
        raise ValueError("unsupported input_format: %r" % (input_fmt,))

    x1 = _clamp(x1, 0.0, float(image_width))
    y1 = _clamp(y1, 0.0, float(image_height))
    x2 = _clamp(x2, 0.0, float(image_width))
    y2 = _clamp(y2, 0.0, float(image_height))

    # Ensure x1 <= x2 and y1 <= y2 after clamping.
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1

    return (x1, y1, x2, y2)


def _from_xyxy(xyxy, output_fmt):
    """Convert a clamped XYXY tuple to the requested output format."""
    x1, y1, x2, y2 = xyxy
    if output_fmt == "xyxy":
        return [x1, y1, x2, y2]
    if output_fmt == "xywh":
        return [x1, y1, x2 - x1, y2 - y1]
    if output_fmt == "center":
        return [(x1 + x2) / 2.0, (y1 + y2) / 2.0, x2 - x1, y2 - y1]
    raise ValueError("unsupported output_format: %r" % (output_fmt,))


def _spatial_metadata(xyxy):
    """Compute area, aspect ratio, and centroid for a clamped XYXY box."""
    x1, y1, x2, y2 = xyxy
    width = x2 - x1
    height = y2 - y1
    area = width * height
    aspect_ratio = (width / height) if height > 0 else 0.0
    centroid = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
    return {
        "area": area,
        "aspect_ratio": aspect_ratio,
        "centroid": centroid,
    }


class PSN_CV_BBoxStandardizer:
    """Standardize bounding box formats and extract spatial metadata."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bboxes": ("LIST", {"default": []}),
                "input_format": (list(_INPUT_FORMATS),),
                "output_format": (list(_OUTPUT_FORMATS),),
                "image_width": ("INT", {"default": 1024, "min": 1, "max": 100000, "step": 1}),
                "image_height": ("INT", {"default": 1024, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("standardized_bboxes", "spatial_metadata")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, bboxes, input_format, output_format, image_width, image_height):
        if not isinstance(bboxes, (list, tuple)):
            raise ValueError("bboxes must be a list of boxes")
        if input_format not in _INPUT_FORMATS:
            raise ValueError("input_format must be one of %s" % (_INPUT_FORMATS,))
        if output_format not in _OUTPUT_FORMATS:
            raise ValueError("output_format must be one of %s" % (_OUTPUT_FORMATS,))
        if not _is_number(image_width) or image_width < 1:
            raise ValueError("image_width must be a positive number")
        if not _is_number(image_height) or image_height < 1:
            raise ValueError("image_height must be a positive number")

        standardized = []
        metadata_list = []
        for box in bboxes:
            xyxy = _to_xyxy(box, image_width, image_height, input_format)
            standardized.append(_from_xyxy(xyxy, output_format))
            metadata_list.append(_spatial_metadata(xyxy))

        metadata_json = json.dumps(metadata_list, separators=(",", ":"))
        return (standardized, metadata_json)


NODE_CLASS_MAPPINGS = {
    "PSN_CV_BBoxStandardizer": PSN_CV_BBoxStandardizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_BBoxStandardizer": "CV BBox Standardizer",
}
