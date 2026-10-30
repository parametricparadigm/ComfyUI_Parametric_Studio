"""HYMotion -> SCAIL pose conversion (pure-logic, secure-by-design).

This module converts HYMotion motion data (per-frame rotations + translations)
into a SCAIL-compatible pose sequence. It performs bone mapping and a
coordinate-system transform (HYMotion is right-handed, SCAIL is left-handed).

Per project rules this is the PURE-LOGIC part only: it takes plain values
(numbers, strings, JSON text) and returns plain values (a JSON text pose
sequence plus a conversion log). It does NOT open sockets, read files, use the
network, or import torch/comfy/numpy/scipy. The SCAIL configuration is supplied
as JSON text (not a file path) so no file/OS access is required.
"""

import json
import math

CAT = "ParametricStudio/Motion"

# Bone mapping: HYMotion bone name -> SCAIL bone name.
BONE_MAP = {
    "Hips": "Hips",
    "Spine": "Spine",
    "Chest": "Chest",
    "Neck": "Neck",
    "Head": "Head",
    "LeftShoulder": "LeftShoulder",
    "RightShoulder": "RightShoulder",
    "LeftArm": "LeftArm",
    "RightArm": "RightArm",
    "LeftForeArm": "LeftForeArm",
    "RightForeArm": "RightForeArm",
    "LeftHand": "LeftHand",
    "RightHand": "RightHand",
    "LeftUpLeg": "LeftUpLeg",
    "RightUpLeg": "RightUpLeg",
    "LeftLeg": "LeftLeg",
    "RightLeg": "RightLeg",
    "LeftFoot": "LeftFoot",
    "RightFoot": "RightFoot",
    "LeftToeBase": "LeftToeBase",
    "RightToeBase": "RightToeBase",
}

# Coordinate transform: HYMotion (right-handed) -> SCAIL (left-handed).
# Flip the Y axis (up) to convert handedness; X and Z are preserved.
_AXIS_FLIP = (1.0, -1.0, 1.0)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value):
    return _is_number(value) and math.isfinite(value)


def _is_vec3(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(_is_finite_number(v) for v in value)
    )


def _is_quat(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(_is_finite_number(v) for v in value)
    )


def _normalize_quat(quat):
    x, y, z, w = quat
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm == 0:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / norm, y / norm, z / norm, w / norm)


def _quat_conjugate(quat):
    x, y, z, w = quat
    return (-x, -y, -z, w)


def _quat_multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _transform_point(point, quat):
    """Rotate a point by a quaternion (pure math, no numpy)."""
    x, y, z = point
    qx, qy, qz, qw = quat
    # t = 2 * cross(q.xyz, p)
    tx = 2.0 * (qy * z - qz * y)
    ty = 2.0 * (qz * x - qx * z)
    tz = 2.0 * (qx * y - qy * x)
    # p' = p + w*t + cross(q.xyz, t)
    cx = qy * tz - qz * ty
    cy = qz * tx - qx * tz
    cz = qx * ty - qy * tx
    return (
        x + qw * tx + cx,
        y + qw * ty + cy,
        z + qw * tz + cz,
    )


def _flip_axis(point):
    return (
        point[0] * _AXIS_FLIP[0],
        point[1] * _AXIS_FLIP[1],
        point[2] * _AXIS_FLIP[2],
    )


def _transform_position(position, rotation):
    """Rotate the position by the frame rotation, then flip to SCAIL space."""
    rotated = _transform_point(position, rotation)
    return _flip_axis(rotated)


def _transform_rotation(rotation):
    """Mirror a rotation quaternion for the Y-axis flip (left-handed)."""
    x, y, z, w = rotation
    return (x, -y, z, w)


def _parse_hymotion(hymotion_data):
    """Parse HYMotion data (dict or JSON text) into a normalized structure.

    Returns (frames, error). frames is a list of dicts keyed by bone name,
    each value being {"position": [x,y,z], "rotation": [x,y,z,w]}.
    """
    if isinstance(hymotion_data, str):
        try:
            data = json.loads(hymotion_data)
        except (ValueError, TypeError):
            return None, "hymotion_data JSON is not valid"
    elif isinstance(hymotion_data, dict):
        data = hymotion_data
    else:
        return None, "hymotion_data must be a dict or JSON text"

    if not isinstance(data, dict):
        return None, "hymotion_data must be an object"

    raw_frames = data.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) == 0:
        return None, "hymotion_data must contain a non-empty 'frames' list"

    frames = []
    for index, frame in enumerate(raw_frames):
        if not isinstance(frame, dict):
            return None, "frame %d is not an object" % index
        parsed_frame = {}
        for bone, pose in frame.items():
            if not isinstance(pose, dict):
                return None, "frame %d bone %r is not an object" % (index, bone)
            position = pose.get("position")
            rotation = pose.get("rotation")
            if not _is_vec3(position):
                return None, "frame %d bone %r has invalid position" % (index, bone)
            if not _is_quat(rotation):
                return None, "frame %d bone %r has invalid rotation" % (index, bone)
            parsed_frame[bone] = {
                "position": [float(v) for v in position],
                "rotation": [float(v) for v in rotation],
            }
        frames.append(parsed_frame)
    return frames, None


def _parse_scail_config(scail_config):
    """Parse SCAIL configuration (dict or JSON text).

    Returns (config, error). config is a dict with optional 'bone_map' and
    'axis_flip' overrides.
    """
    if isinstance(scail_config, str):
        try:
            config = json.loads(scail_config)
        except (ValueError, TypeError):
            return None, "scail_config JSON is not valid"
    elif isinstance(scail_config, dict):
        config = scail_config
    else:
        return None, "scail_config must be a dict or JSON text"

    if not isinstance(config, dict):
        return None, "scail_config must be an object"
    return config, None


def convert_hymotion_to_scail(hymotion_data, scail_config):
    """Convert HYMotion data to a SCAIL pose sequence.

    Returns (pose_sequence, log). pose_sequence is a dict with 'frames' and
    'bones'; log is a human-readable string. On error pose_sequence is None.
    """
    log_lines = []

    frames, err = _parse_hymotion(hymotion_data)
    if err:
        return None, "ERROR: " + err
    log_lines.append("Parsed %d HYMotion frame(s)." % len(frames))

    config, err = _parse_scail_config(scail_config)
    if err:
        return None, "ERROR: " + err
    log_lines.append("Loaded SCAIL configuration.")

    bone_map = dict(BONE_MAP)
    if isinstance(config.get("bone_map"), dict):
        for key, value in config["bone_map"].items():
            if isinstance(key, str) and isinstance(value, str):
                bone_map[key] = value
    log_lines.append("Using %d bone mapping(s)." % len(bone_map))

    scail_frames = []
    unmapped_bones = set()
    for frame in frames:
        scail_frame = {}
        for bone, pose in frame.items():
            scail_bone = bone_map.get(bone)
            if scail_bone is None:
                unmapped_bones.add(bone)
                continue
            rotation = _normalize_quat(pose["rotation"])
            scail_frame[scail_bone] = {
                "position": [round(v, 6) for v in _transform_position(pose["position"], rotation)],
                "rotation": [round(v, 6) for v in _transform_rotation(rotation)],
            }
        scail_frames.append(scail_frame)

    if unmapped_bones:
        log_lines.append("WARNING: unmapped bone(s): %s" % ", ".join(sorted(unmapped_bones)))

    pose_sequence = {
        "frames": scail_frames,
        "bones": sorted({b for f in scail_frames for b in f}),
        "frame_count": len(scail_frames),
    }
    log_lines.append("Produced SCAIL pose sequence with %d frame(s)." % len(scail_frames))
    return pose_sequence, "\n".join(log_lines)


class PSN_HYMotionToSCAIL_Convert:
    """Convert HYMotion data into a SCAIL pose sequence (bone mapping + coordinate transform)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "hymotion_data": ("HYMOTION_DATA",),
                "scail_config": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("SCAIL_POSE_SEQUENCE", "STRING")
    RETURN_NAMES = ("scail_pose_sequence", "conversion_log")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, hymotion_data, scail_config):
        pose_sequence, log = convert_hymotion_to_scail(hymotion_data, scail_config)
        if pose_sequence is None:
            return (None, log)
        return (json.dumps(pose_sequence), log)


NODE_CLASS_MAPPINGS = {
    "PSN_HYMotionToSCAIL_Convert": PSN_HYMotionToSCAIL_Convert,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_HYMotionToSCAIL_Convert": "HYMotion to SCAIL Convert",
}
