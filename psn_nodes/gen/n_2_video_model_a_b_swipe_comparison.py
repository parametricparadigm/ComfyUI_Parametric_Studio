"""
PSN Video A/B Swipe Comparison nodes.

This module implements the pure-logic, secure-by-design portion of a video
A/B swipe comparison workflow. Because the full spec requires GPU/torch/ComfyUI
internals (VIDEO tensors, IMAGE outputs, Pillow compositing), this module
implements ONLY the pure-logic parts:

  * PSN_Video_A_B_Loader  - validates two video descriptors (frame count,
    resolution), decides whether video_b must be resized to match video_a,
    and packages them into a synchronized pair (a plain dict).
  * PSN_Video_Swipe_Preview - given a synced pair, a frame index and a
    split_position in [0.0, 1.0], computes the pixel column at which the
    left (Video A) region ends and the right (Video B) region begins, and
    returns a plain description of the composite layout (no actual pixel
    compositing, which would require torch/numpy/Pillow).

All functions and node wrappers take plain values (numbers, strings, dicts,
JSON text) and return plain values. No sockets, no file/OS access, no
network, no subprocess, no eval/exec, no torch/comfy imports.
"""

import json

CAT = "ParametricStudio/Video"

# Sentinel type names used in RETURN_TYPES. These are plain strings so the
# module stays importable without ComfyUI.
PSN_VIDEO_PAIR = "PSN_VIDEO_PAIR"
IMAGE = "IMAGE"
STRING = "STRING"
BOOLEAN = "BOOLEAN"
INT = "INT"
FLOAT = "FLOAT"
DICT = "DICT"
ANY = "ANY"


def _psn_validate_video_descriptor(video, name):
    """Validate a plain video descriptor dict.

    A video descriptor is a plain dict with keys:
      - "frame_count": positive int
      - "width": positive int
      - "height": positive int
      - "channels": positive int (default 3)
      - "name": optional string label

    Returns (ok, error_message, normalized_descriptor).
    """
    if not isinstance(video, dict):
        return False, "%s: video descriptor must be a dict" % name, None

    frame_count = video.get("frame_count")
    width = video.get("width")
    height = video.get("height")
    channels = video.get("channels", 3)

    if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
        return False, "%s: frame_count must be a positive integer" % name, None
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        return False, "%s: width must be a positive integer" % name, None
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        return False, "%s: height must be a positive integer" % name, None
    if not isinstance(channels, int) or isinstance(channels, bool) or channels <= 0:
        return False, "%s: channels must be a positive integer" % name, None

    label = video.get("name", name)
    if not isinstance(label, str):
        label = str(label)

    normalized = {
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "channels": channels,
        "name": label,
    }
    return True, "", normalized


def _psn_build_synced_pair(video_a, video_b, resized_b):
    """Build the synchronized pair dict from two normalized descriptors."""
    return {
        "video_a": video_a,
        "video_b": video_b,
        "resized_b": resized_b,
        "frame_count": video_a["frame_count"],
        "width": video_a["width"],
        "height": video_a["height"],
        "channels": video_a["channels"],
    }


def _psn_compute_split_column(split_position, width):
    """Compute the integer column index where the left region ends.

    split_position in [0.0, 1.0]. The left region covers columns
    [0, split_column) and the right region covers [split_column, width).
    split_column is clamped to [0, width].
    """
    if width <= 0:
        return 0
    if split_position <= 0.0:
        return 0
    if split_position >= 1.0:
        return width
    col = int(round(split_position * width))
    if col < 0:
        col = 0
    if col > width:
        col = width
    return col


class PSN_Video_A_B_Loader:
    """Validate two video descriptors and package them into a synced pair.

    Pure-logic stand-in for the GPU/video loader. Inputs are plain dicts
    describing each video (frame_count, width, height, channels, name).
    If the two videos have different resolutions, video_b is marked as
    needing a resize to match video_a (the actual resize would happen in a
    GPU node). Frame counts must match exactly.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_a": (DICT, {"default": {"frame_count": 10, "width": 512, "height": 512, "channels": 3, "name": "A"}}),
                "video_b": (DICT, {"default": {"frame_count": 10, "width": 512, "height": 512, "channels": 3, "name": "B"}}),
            },
            "optional": {},
        }

    RETURN_TYPES = (PSN_VIDEO_PAIR, BOOLEAN, STRING)
    RETURN_NAMES = ("synced_video_pair", "valid", "message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video_a, video_b):
        ok_a, err_a, norm_a = _psn_validate_video_descriptor(video_a, "video_a")
        if not ok_a:
            return ({}, False, err_a)

        ok_b, err_b, norm_b = _psn_validate_video_descriptor(video_b, "video_b")
        if not ok_b:
            return ({}, False, err_b)

        if norm_a["frame_count"] != norm_b["frame_count"]:
            return ({}, False, "frame_count mismatch: video_a=%d video_b=%d" % (norm_a["frame_count"], norm_b["frame_count"]))

        resized_b = (norm_a["width"] != norm_b["width"]) or (norm_a["height"] != norm_b["height"])
        pair = _psn_build_synced_pair(norm_a, norm_b, resized_b)
        if resized_b:
            msg = "video_b resized from %dx%d to %dx%d" % (norm_b["width"], norm_b["height"], norm_a["width"], norm_a["height"])
        else:
            msg = "videos synchronized, no resize needed"
        return (pair, True, msg)


class PSN_Video_Swipe_Preview:
    """Compute the swipe-composite layout for a synced video pair.

    Pure-logic stand-in for the GPU preview node. Given a synced pair
    (dict), a frame index and a split_position in [0.0, 1.0], returns a
    plain dict describing the composite: which frame index is used, the
    split column, the left/right region widths, and the source video
    labels. No actual pixel compositing is performed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "synced_video_pair": (PSN_VIDEO_PAIR, {"default": {}}),
                "split_position": (FLOAT, {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "frame_index": (INT, {"default": 0, "min": 0, "max": 1000000}),
            },
            "optional": {},
        }

    RETURN_TYPES = (DICT, BOOLEAN, STRING)
    RETURN_NAMES = ("preview_layout", "valid", "message")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, synced_video_pair, split_position, frame_index):
        if not isinstance(synced_video_pair, dict) or not synced_video_pair:
            return ({}, False, "synced_video_pair must be a non-empty dict")

        if "video_a" not in synced_video_pair or "video_b" not in synced_video_pair:
            return ({}, False, "synced_video_pair missing video_a or video_b")

        width = synced_video_pair.get("width")
        height = synced_video_pair.get("height")
        frame_count = synced_video_pair.get("frame_count")

        if not isinstance(width, int) or width <= 0:
            return ({}, False, "invalid width in synced pair")
        if not isinstance(height, int) or height <= 0:
            return ({}, False, "invalid height in synced pair")
        if not isinstance(frame_count, int) or frame_count <= 0:
            return ({}, False, "invalid frame_count in synced pair")

        if not isinstance(frame_index, int) or isinstance(frame_index, bool):
            return ({}, False, "frame_index must be an integer")
        if frame_index < 0 or frame_index >= frame_count:
            return ({}, False, "frame_index %d out of range [0, %d)" % (frame_index, frame_count))

        if not isinstance(split_position, (int, float)) or isinstance(split_position, bool):
            return ({}, False, "split_position must be a number")
        if split_position < 0.0 or split_position > 1.0:
            return ({}, False, "split_position must be in [0.0, 1.0]")

        split_col = _psn_compute_split_column(float(split_position), width)
        left_width = split_col
        right_width = width - split_col

        layout = {
            "frame_index": frame_index,
            "width": width,
            "height": height,
            "split_column": split_col,
            "left_width": left_width,
            "right_width": right_width,
            "left_source": synced_video_pair["video_a"].get("name", "A"),
            "right_source": synced_video_pair["video_b"].get("name", "B"),
            "resized_b": synced_video_pair.get("resized_b", False),
        }
        return (layout, True, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_Video_A_B_Loader": PSN_Video_A_B_Loader,
    "PSN_Video_Swipe_Preview": PSN_Video_Swipe_Preview,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_A_B_Loader": "PSN Video A/B Loader",
    "PSN_Video_Swipe_Preview": "PSN Video Swipe Preview",
}
