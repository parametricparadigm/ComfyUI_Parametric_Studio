"""
PSN FBX-to-Video Motion Transfer (pure-logic core).

This module implements the *secure, pure-Python* portion of the FBX-to-Video
Motion Transfer workflow. It does NOT load FBX files, does NOT touch the file
system, does NOT import torch/numpy/opencv, and does NOT open sockets.

Instead it provides:
  * PSN_FBX_Pose_Extractor  - validates an FBX *payload* (JSON text describing
    frames and bone positions), validates a bone->keypoint mapping, and projects
    3D bone positions into 2D OpenPose keypoints using a simple perspective
    projection. It returns the projected keypoints and a reason string.
  * PSN_Pose_Video_Driver   - validates that a pose-frame payload and a
    reference-image payload are compatible (same frame count, sane dimensions)
    and produces a deterministic "latent plan" (a JSON string describing the
    video latent that a downstream GPU node would build).

All inputs are plain values (strings, numbers, JSON text). The module is
self-contained and uses only the Python standard library.
"""

import json
import math

CAT = "ParametricStudio/MotionTransfer"

# OpenPose 18-keypoint skeleton (standard ordering).
OPENPOSE_KEYPOINTS = [
    "nose", "neck", "R_shoulder", "R_elbow", "R_wrist",
    "L_shoulder", "L_elbow", "L_wrist",
    "R_hip", "R_knee", "R_ankle",
    "L_hip", "L_knee", "L_ankle",
    "R_eye", "L_eye", "R_ear", "L_ear",
]

# Default camera parameters for the 3D->2D projection.
_DEFAULT_FOCAL = 500.0
_DEFAULT_CX = 256.0
_DEFAULT_CY = 256.0
_DEFAULT_Z = 1000.0
_DEFAULT_FRAME_W = 512
_DEFAULT_FRAME_H = 512


def _safe_json_loads(text, what):
    """Parse JSON text defensively; raise ValueError on failure."""
    if not isinstance(text, str):
        raise ValueError(f"{what} must be a JSON string, got {type(text).__name__}")
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid JSON for {what}: {exc}") from exc


def _validate_bone_mapping(bone_mapping_text):
    """
    Validate the bone->keypoint mapping.

    Accepts a JSON object mapping 3D bone names (strings) to OpenPose keypoint
    indices (int in [0, 17]) or keypoint names (strings from OPENPOSE_KEYPOINTS).
    Returns a dict {bone_name: keypoint_index}.
    """
    raw = _safe_json_loads(bone_mapping_text, "bone_mapping")
    if not isinstance(raw, dict):
        raise ValueError("bone_mapping must be a JSON object")
    mapping = {}
    for bone, target in raw.items():
        if not isinstance(bone, str) or not bone:
            raise ValueError(f"bone name must be a non-empty string, got {bone!r}")
        if isinstance(target, bool):
            raise ValueError(f"keypoint for {bone!r} must be an int or string, not bool")
        if isinstance(target, int):
            if not (0 <= target < len(OPENPOSE_KEYPOINTS)):
                raise ValueError(f"keypoint index {target} out of range for bone {bone!r}")
            mapping[bone] = target
        elif isinstance(target, str):
            if target not in OPENPOSE_KEYPOINTS:
                raise ValueError(f"unknown keypoint name {target!r} for bone {bone!r}")
            mapping[bone] = OPENPOSE_KEYPOINTS.index(target)
        else:
            raise ValueError(f"keypoint for {bone!r} must be an int or string, got {type(target).__name__}")
    return mapping


def _project_point(x, y, z, focal, cx, cy, z_cam):
    """
    Simple perspective projection of a 3D point (x, y, z) into 2D pixel coords.
    z_cam is the camera distance along the z-axis.
    """
    dz = z_cam - z
    if dz <= 1e-6:
        # Point at or behind the camera; clamp to avoid division by zero.
        dz = 1e-6
    px = cx + (x / dz) * focal
    py = cy - (y / dz) * focal  # flip y so up is positive
    return px, py


def _extract_keypoints_for_frame(frame, mapping, focal, cx, cy, z_cam, frame_w, frame_h):
    """
    Given a frame dict {bone_name: [x, y, z], ...}, project each mapped bone
    into 2D and return a list of (px, py) of length len(OPENPOSE_KEYPOINTS),
    with (0.0, 0.0) for unmapped keypoints.
    """
    kps = [(0.0, 0.0)] * len(OPENPOSE_KEYPOINTS)
    bones = frame.get("bones", frame)
    if not isinstance(bones, dict):
        raise ValueError("frame 'bones' must be a JSON object")
    for bone, pos in bones.items():
        if bone not in mapping:
            continue
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            raise ValueError(f"bone {bone!r} position must be [x, y, z], got {pos!r}")
        try:
            x, y, z = (float(pos[0]), float(pos[1]), float(pos[2]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"bone {bone!r} position must be numeric: {exc}") from exc
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            raise ValueError(f"bone {bone!r} position must be finite")
        px, py = _project_point(x, y, z, focal, cx, cy, z_cam)
        # Clamp to frame bounds.
        px = max(0.0, min(float(frame_w), px))
        py = max(0.0, min(float(frame_h), py))
        kps[mapping[bone]] = (px, py)
    return kps


def _validate_fbx_payload(fbx_payload_text, frame_rate):
    """
    Validate the FBX payload JSON. Expected shape:
      {
        "frames": [
          {"bones": {"boneA": [x, y, z], ...}},
          ...
        ]
      }
    Returns a list of frame dicts.
    """
    if not isinstance(frame_rate, int) or isinstance(frame_rate, bool):
        raise ValueError("frame_rate must be an integer")
    if frame_rate <= 0:
        raise ValueError("frame_rate must be positive")
    payload = _safe_json_loads(fbx_payload_text, "fbx_payload")
    if not isinstance(payload, dict):
        raise ValueError("fbx_payload must be a JSON object")
    frames = payload.get("frames")
    if not isinstance(frames, list):
        raise ValueError("fbx_payload must contain a 'frames' list")
    if len(frames) == 0:
        raise ValueError("fbx_payload 'frames' must not be empty")
    for i, fr in enumerate(frames):
        if not isinstance(fr, dict):
            raise ValueError(f"frame {i} must be a JSON object")
    return frames


class PSN_FBX_Pose_Extractor:
    """
    Validate an FBX payload (JSON text) and a bone->keypoint mapping, then
    project 3D bone positions into 2D OpenPose keypoints per frame.

    Pure-logic: no file I/O, no FBX parsing. The caller is expected to supply
    the extracted bone positions as JSON text.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "fbx_payload": ("STRING", {"default": '{"frames":[{"bones":{}}]}', "multiline": True}),
                "frame_rate": ("INT", {"default": 30, "min": 1, "max": 240}),
                "bone_mapping": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "focal": ("FLOAT", {"default": _DEFAULT_FOCAL, "min": 1.0, "max": 1e5, "step": 1.0}),
                "z_cam": ("FLOAT", {"default": _DEFAULT_Z, "min": 1.0, "max": 1e5, "step": 1.0}),
                "frame_width": ("INT", {"default": _DEFAULT_FRAME_W, "min": 16, "max": 4096}),
                "frame_height": ("INT", {"default": _DEFAULT_FRAME_H, "min": 16, "max": 4096}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("keypoints_json", "reason", "frame_count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, fbx_payload, frame_rate, bone_mapping,
            focal=_DEFAULT_FOCAL, z_cam=_DEFAULT_Z,
            frame_width=_DEFAULT_FRAME_W, frame_height=_DEFAULT_FRAME_H):
        try:
            frames = _validate_fbx_payload(fbx_payload, frame_rate)
            mapping = _validate_bone_mapping(bone_mapping)
            all_kps = []
            for fr in frames:
                kps = _extract_keypoints_for_frame(
                    fr, mapping, focal, _DEFAULT_CX, _DEFAULT_CY, z_cam, frame_width, frame_height
                )
                all_kps.append(kps)
        except ValueError as exc:
            return (json.dumps({"error": str(exc)}), f"validation error: {exc}", 0)

        out = {
            "frame_rate": frame_rate,
            "frame_count": len(all_kps),
            "keypoints": all_kps,
        }
        return (json.dumps(out), "ok", len(all_kps))


class PSN_Pose_Video_Driver:
    """
    Validate a pose-frame payload (JSON text of keypoints) and a reference-image
    payload (JSON text with width/height), and produce a deterministic latent
    plan (JSON string) describing the video latent a downstream GPU node would
    build. Pure-logic: no torch, no VAE, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pose_frames": ("STRING", {"default": '{"frame_count":1,"keypoints":[]}', "multiline": True}),
                "reference_image": ("STRING", {"default": '{"width":512,"height":512}', "multiline": True}),
            },
            "optional": {
                "latent_channels": ("INT", {"default": 4, "min": 1, "max": 64}),
                "latent_scale": ("FLOAT", {"default": 8.0, "min": 1.0, "max": 64.0, "step": 0.5}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("latent_plan_json", "reason", "valid")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, pose_frames, reference_image, latent_channels=4, latent_scale=8.0):
        try:
            pose = _safe_json_loads(pose_frames, "pose_frames")
            ref = _safe_json_loads(reference_image, "reference_image")
        except ValueError as exc:
            return (json.dumps({"error": str(exc)}), f"parse error: {exc}", False)

        if not isinstance(pose, dict) or not isinstance(ref, dict):
            return (json.dumps({"error": "payloads must be JSON objects"}), "payloads must be JSON objects", False)

        frame_count = pose.get("frame_count")
        if not isinstance(frame_count, int) or isinstance(frame_count, bool) or frame_count <= 0:
            return (json.dumps({"error": "pose_frames.frame_count must be a positive int"}),
                    "bad frame_count", False)

        kps = pose.get("keypoints")
        if not isinstance(kps, list) or len(kps) != frame_count:
            return (json.dumps({"error": "pose_frames.keypoints length must equal frame_count"}),
                    "keypoints length mismatch", False)

        width = ref.get("width")
        height = ref.get("height")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            return (json.dumps({"error": "reference_image width/height must be positive ints"}),
                    "bad reference dimensions", False)

        if not isinstance(latent_channels, int) or isinstance(latent_channels, bool) or latent_channels <= 0:
            return (json.dumps({"error": "latent_channels must be a positive int"}),
                    "bad latent_channels", False)
        if not isinstance(latent_scale, (int, float)) or isinstance(latent_scale, bool) or latent_scale <= 0:
            return (json.dumps({"error": "latent_scale must be a positive number"}),
                    "bad latent_scale", False)

        lw = max(1, width // int(latent_scale))
        lh = max(1, height // int(latent_scale))
        plan = {
            "frame_count": frame_count,
            "latent_channels": latent_channels,
            "latent_width": lw,
            "latent_height": lh,
            "shape": [1, latent_channels, frame_count, lh, lw],
        }
        return (json.dumps(plan), "ok", True)


NODE_CLASS_MAPPINGS = {
    "PSN_FBX_Pose_Extractor": PSN_FBX_Pose_Extractor,
    "PSN_Pose_Video_Driver": PSN_Pose_Video_Driver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FBX_Pose_Extractor": "FBX Pose Extractor (Pure Logic)",
    "PSN_Pose_Video_Driver": "Pose Video Driver (Pure Logic)",
}
