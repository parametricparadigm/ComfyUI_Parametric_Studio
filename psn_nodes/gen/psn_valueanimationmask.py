"""PSN_ValueAnimationMask: Creates masks that react to value animation (brightness or color changes).

This module implements the pure-logic portion of the ValueAnimationMask node.
Since the original spec requires torch for GPU tensor operations, this implementation
works with plain Python lists representing pixel data (no torch, no ComfyUI imports).

Data representation:
- video: list of frames, where each frame is a list of rows, each row is a list of
  pixels, and each pixel is a list of channel values (e.g., [R, G, B] or [L]).
- value_mask: list of frames, where each frame is a list of rows, each row is a list
  of 0.0 or 1.0 values indicating whether the pixel exceeded the threshold.

The node analyzes pixel values across frames and generates masks based on changes
relative to a threshold. For "brightness" mode, it computes the mean of all channels
per pixel. For "color" mode, it computes the maximum channel deviation from the mean
(saturation-like measure).

Inputs:
- video (list): batch of frames as nested lists of pixel channel values
- value_type (str): "brightness" or "color"
- threshold (float): threshold for mask activation

Outputs:
- value_mask (list): batch of masks as nested lists of 0.0/1.0 values
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Video"

# Allowed value types
_VALUE_TYPES = ["brightness", "color"]


def _compute_brightness(pixel):
    """Compute brightness (mean of all channels) for a single pixel.

    Args:
        pixel: list of channel values (e.g., [R, G, B])

    Returns:
        float: mean of all channel values
    """
    if not pixel:
        return 0.0
    return sum(pixel) / len(pixel)


def _compute_color_deviation(pixel):
    """Compute color deviation (max deviation from mean) for a single pixel.

    This measures how 'colorful' a pixel is by looking at the maximum
    deviation of any channel from the mean channel value.

    Args:
        pixel: list of channel values (e.g., [R, G, B])

    Returns:
        float: maximum absolute deviation from the mean
    """
    if not pixel:
        return 0.0
    mean_val = sum(pixel) / len(pixel)
    max_dev = 0.0
    for ch in pixel:
        dev = abs(ch - mean_val)
        if dev > max_dev:
            max_dev = dev
    return max_dev


def _analyze_frame(frame, value_type):
    """Analyze a single frame and return a 2D list of value metrics.

    Args:
        frame: list of rows, each row is a list of pixels (each pixel is a list of channels)
        value_type: "brightness" or "color"

    Returns:
        list: 2D list of float values (one per pixel)
    """
    if value_type == "brightness":
        func = _compute_brightness
    elif value_type == "color":
        func = _compute_color_deviation
    else:
        raise ValueError("value_type must be 'brightness' or 'color'")

    result = []
    for row in frame:
        result_row = []
        for pixel in row:
            result_row.append(func(pixel))
        result.append(result_row)
    return result


def _apply_threshold(values_2d, threshold):
    """Apply threshold to a 2D list of values, producing a binary mask.

    Args:
        values_2d: 2D list of float values
        threshold: float threshold

    Returns:
        list: 2D list of 0.0 or 1.0 values
    """
    mask = []
    for row in values_2d:
        mask_row = []
        for val in row:
            mask_row.append(1.0 if val >= threshold else 0.0)
        mask.append(mask_row)
    return mask


class PSN_ValueAnimationMask:
    """Creates masks that react to value animation (brightness or color changes).

    Analyzes pixel values across frames and generates masks based on changes
    relative to a threshold. Works with plain Python lists representing pixel data.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("LIST", {"default": []}),
                "value_type": (_VALUE_TYPES,),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("value_mask",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video, value_type, threshold):
        """Analyze video frames and generate value-based masks.

        Args:
            video: list of frames; each frame is a list of rows; each row is a list
                   of pixels; each pixel is a list of channel values (floats 0.0-1.0)
            value_type: "brightness" or "color"
            threshold: float threshold for mask activation

        Returns:
            tuple: (value_mask,) where value_mask is a list of frames; each frame is
                   a list of rows; each row is a list of 0.0 or 1.0 values
        """
        # Validate value_type
        if value_type not in _VALUE_TYPES:
            raise ValueError("value_type must be one of: {}".format(_VALUE_TYPES))

        # Validate threshold
        if not isinstance(threshold, (int, float)):
            raise TypeError("threshold must be a number")
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        # Validate video structure
        if not isinstance(video, list):
            raise TypeError("video must be a list of frames")

        value_mask = []
        for frame in video:
            if not isinstance(frame, list):
                raise TypeError("each frame must be a list of rows")
            frame_values = _analyze_frame(frame, value_type)
            frame_mask = _apply_threshold(frame_values, threshold)
            value_mask.append(frame_mask)

        return (value_mask,)


NODE_CLASS_MAPPINGS = {
    "PSN_ValueAnimationMask": PSN_ValueAnimationMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ValueAnimationMask": "Value Animation Mask",
}
