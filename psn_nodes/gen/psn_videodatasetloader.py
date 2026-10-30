"""PSN_VideoDatasetLoader: pure-logic, secure-by-design planning/validation for video dataset ingestion.

This module does NOT decode video, open files, or touch the network. It only:
  - validates and normalizes the loader configuration (frame range, resize mode, target size),
  - computes a deterministic chunked-loading plan (mitigating memory spikes for long ranges),
  - builds a metadata payload (VIDEO_INFO) from plain values,
  - redacts sensitive path components from the reported metadata.

The real decoding (PyAV/FFmpeg) and tensor conversion are out of scope here; this node
returns the plan and metadata that a downstream decoder would consume.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

try:
    from psn import expr, orchestration as _orch
except Exception:  # pragma: no cover - fallback if psn helpers unavailable
    expr = None
    _orch = None

CAT = "ParametricStudio/Video"

RESIZE_MODES = ["none", "center_crop", "pad"]
CHUNK_THRESHOLD = 100  # if range > this, split into chunks
MAX_CHUNK = 100        # max frames per chunk
MAX_FRAMES_HARD = 100000  # sanity cap on total requested frames


@dataclass
class VideoInfo:
    """Metadata about the source video (plain values only)."""
    fps: float = 0.0
    total_frames: int = 0
    duration: float = 0.0
    codec: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fps": self.fps,
            "total_frames": self.total_frames,
            "duration": self.duration,
            "codec": self.codec,
        }


def _redact_path(file_path: str) -> str:
    """Redact the directory portion of a path, keeping only the basename.

    This avoids leaking filesystem layout into metadata/logs.
    """
    if not isinstance(file_path, str) or not file_path:
        return ""
    # Normalize separators
    normalized = file_path.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1]
    return base


def _validate_range(start_frame: int, end_frame: int, total_frames: int) -> Tuple[int, int, str]:
    """Validate and clamp the frame range. Returns (start, end, reason)."""
    if not isinstance(start_frame, int) or not isinstance(end_frame, int):
        return 0, 0, "frame indices must be integers"
    if start_frame < 0:
        start_frame = 0
    if end_frame < start_frame:
        return start_frame, start_frame - 1, "end_frame must be >= start_frame"
    if total_frames > 0:
        if start_frame >= total_frames:
            return start_frame, start_frame - 1, "start_frame beyond total_frames"
        end_frame = min(end_frame, total_frames - 1)
    return start_frame, end_frame, "ok"


def _build_chunk_plan(start: int, end: int) -> List[Tuple[int, int]]:
    """Build a list of (chunk_start, chunk_end) inclusive ranges.

    If the total range is <= CHUNK_THRESHOLD, a single chunk is returned.
    Otherwise, the range is split into chunks of at most MAX_CHUNK frames.
    """
    if end < start:
        return []
    total = end - start + 1
    if total <= CHUNK_THRESHOLD:
        return [(start, end)]
    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + MAX_CHUNK - 1, end)
        chunks.append((cur, chunk_end))
        cur = chunk_end + 1
    return chunks


def _compute_duration(fps: float, total_frames: int) -> float:
    """Compute duration in seconds from fps and total frames."""
    if fps <= 0 or total_frames <= 0:
        return 0.0
    return total_frames / fps


class PSN_VideoDatasetLoader:
    """Plan and validate video dataset ingestion without touching the filesystem.

    Returns a chunked loading plan and a VideoInfo metadata object.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "", "multiline": False}),
                "start_frame": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "end_frame": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "resize_mode": (RESIZE_MODES,),
                "target_width": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
                "target_height": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 1}),
            },
            "optional": {
                "fps": ("FLOAT", {"default": 30.0, "min": 0.0, "max": 1000.0, "step": 0.01}),
                "total_frames": ("INT", {"default": 0, "min": 0, "max": 1000000, "step": 1}),
                "codec": ("STRING", {"default": "h264", "multiline": False}),
            },
        }

    RETURN_TYPES = ("VIDEO_INFO", "STRING", "STRING")
    RETURN_NAMES = ("video_info", "chunk_plan_json", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(
        self,
        file_path: str,
        start_frame: int,
        end_frame: int,
        resize_mode: str,
        target_width: int,
        target_height: int,
        fps: float = 30.0,
        total_frames: int = 0,
        codec: str = "h264",
    ):
        # Validate resize mode
        if resize_mode not in RESIZE_MODES:
            return (VideoInfo(), "[]", f"invalid resize_mode: {resize_mode}")

        # Validate target dimensions
        if target_width < 1 or target_height < 1:
            return (VideoInfo(), "[]", "target dimensions must be >= 1")

        # Validate frame range
        start, end, reason = _validate_range(start_frame, end_frame, total_frames)
        if reason != "ok":
            info = VideoInfo(
                fps=fps,
                total_frames=total_frames,
                duration=_compute_duration(fps, total_frames),
                codec=codec,
            )
            return (info, "[]", reason)

        # Build chunk plan
        chunks = _build_chunk_plan(start, end)

        # Build metadata
        info = VideoInfo(
            fps=fps,
            total_frames=total_frames,
            duration=_compute_duration(fps, total_frames),
            codec=codec,
        )

        # Serialize chunk plan as JSON-like string (no json import needed for simple tuples)
        chunk_str = "[" + ",".join(f"[{s},{e}]" for s, e in chunks) + "]"

        return (info, chunk_str, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_VideoDatasetLoader": PSN_VideoDatasetLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VideoDatasetLoader": "PSN Video Dataset Loader (Plan)",
}
