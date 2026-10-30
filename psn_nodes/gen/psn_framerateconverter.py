"""PSN_FramerateConverter: pure-logic framerate conversion planning and payload formatting.

This module implements the secure, pure-logic portion of a framerate conversion node.
It does NOT perform any network I/O, file access, or GPU operations. Instead, it:
- Validates source and target FPS values
- Computes the frame count mapping between source and target framerates
- Formats a JSON payload that a backend API would accept for the conversion job
- Provides a deterministic frame-index mapping (which source frames map to which target frames)

The actual IMAGE tensor conversion would be handled by a backend service; this node
produces the conversion plan and payload that such a service would consume.
"""

import json
import math

CAT = "ParametricStudio/Video"


def _validate_fps(fps, name="fps"):
    """Validate that fps is a positive finite number."""
    if not isinstance(fps, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(fps).__name__}")
    if isinstance(fps, float) and (math.isnan(fps) or math.isinf(fps)):
        raise ValueError(f"{name} must be a finite number, got {fps}")
    if fps <= 0:
        raise ValueError(f"{name} must be positive, got {fps}")
    return float(fps)


def _compute_frame_mapping(source_fps, target_fps, source_frame_count):
    """Compute which source frame index maps to each target frame index.

    Uses nearest-neighbor sampling: for each target frame t, the corresponding
    source frame is round(t * source_fps / target_fps), clamped to valid range.

    Returns a list of source frame indices (one per target frame).
    """
    if source_frame_count <= 0:
        return []
    ratio = source_fps / target_fps
    target_frame_count = max(1, int(round(source_frame_count * target_fps / source_fps)))
    mapping = []
    for t in range(target_frame_count):
        src_idx = int(round(t * ratio))
        src_idx = max(0, min(src_idx, source_frame_count - 1))
        mapping.append(src_idx)
    return mapping


def _build_payload(source_fps, target_fps, source_frame_count, job_id=""):
    """Build a JSON-serializable payload for the backend conversion API."""
    mapping = _compute_frame_mapping(source_fps, target_fps, source_frame_count)
    target_frame_count = len(mapping)
    payload = {
        "job_id": job_id,
        "operation": "framerate_convert",
        "source_fps": source_fps,
        "target_fps": target_fps,
        "source_frame_count": source_frame_count,
        "target_frame_count": target_frame_count,
        "frame_mapping": mapping,
        "method": "nearest_neighbor",
    }
    return payload


class PSN_FramerateConverter:
    """Converts video framerate by computing a frame mapping and building a backend payload.

    Pure-logic node: no network, no file I/O, no GPU. Produces the conversion plan
    (frame index mapping) and a JSON payload string that a backend service would use
    to perform the actual tensor resampling.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_fps": ("FLOAT", {"default": 30.0, "min": 0.001, "max": 1000.0, "step": 0.001}),
                "target_fps": ("FLOAT", {"default": 60.0, "min": 0.001, "max": 1000.0, "step": 0.001}),
                "source_frame_count": ("INT", {"default": 30, "min": 1, "max": 100000, "step": 1}),
            },
            "optional": {
                "job_id": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("payload_json", "frame_mapping_json", "target_frame_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, source_fps, target_fps, source_frame_count, job_id=""):
        """Compute the framerate conversion plan and return payload + mapping.

        Args:
            source_fps: Input video framerate (positive float).
            target_fps: Desired output framerate (positive float).
            source_frame_count: Number of frames in the input video batch.
            job_id: Optional identifier for the conversion job.

        Returns:
            Tuple of (payload_json, frame_mapping_json, target_frame_count).
        """
        src = _validate_fps(source_fps, "source_fps")
        tgt = _validate_fps(target_fps, "target_fps")

        if not isinstance(source_frame_count, int) or source_frame_count < 1:
            raise ValueError(f"source_frame_count must be a positive integer, got {source_frame_count}")

        mapping = _compute_frame_mapping(src, tgt, source_frame_count)
        payload = _build_payload(src, tgt, source_frame_count, job_id)

        payload_json = json.dumps(payload, separators=(",", ":"))
        mapping_json = json.dumps(mapping, separators=(",", ":"))
        target_frame_count = len(mapping)

        return (payload_json, mapping_json, target_frame_count)


NODE_CLASS_MAPPINGS = {
    "PSN_FramerateConverter": PSN_FramerateConverter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FramerateConverter": "Framerate Converter (Plan)",
}
