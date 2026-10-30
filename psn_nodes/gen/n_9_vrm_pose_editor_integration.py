"""VRM Pose Editor Integration (pure-logic, secure-by-design).

This module implements the *logic* half of a VRM pose editor node.  It does
NOT load VRM models, render images, or touch the filesystem.  Instead it:

  * validates a VRM model path against an allow-list of safe extensions,
  * parses / validates a pose payload (JSON text) into a normalised dict,
  * applies a single edit operation (rotate or translate) to one or more
    joints,
  * produces a deterministic, hash-based "preview token" that a real
    renderer could use to look up or generate a preview image.

All public functions accept plain values (strings, numbers, dicts) and
return plain values.  No network, file, subprocess, or GPU access is
performed.
"""

import json
import hashlib
import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EDIT_MODES = ("rotate", "translate")

ALLOWED_VRM_EXTENSIONS = (".vrm", ".vrm0", ".vrm1")

# Joint names we recognise (a small, safe subset of the VRM 1.0 spec).
KNOWN_JOINTS = frozenset({
    "hips", "spine", "chest", "upperChest", "neck", "head",
    "leftShoulder", "leftArm", "leftForeArm", "leftHand",
    "rightShoulder", "rightArm", "rightForeArm", "rightHand",
    "leftUpLeg", "leftLeg", "leftFoot", "leftToes",
    "rightUpLeg", "rightLeg", "rightFoot", "rightToes",
})

# Maximum number of joints in a single pose payload.
MAX_JOINTS = 256

# Maximum absolute value for any coordinate / angle component.
MAX_COMPONENT = 1e6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_vrm_path(path):
    """Return (ok, reason).  *ok* is True when the path looks safe."""
    if not isinstance(path, str) or not path.strip():
        return False, "vrm_model_path must be a non-empty string"
    p = path.strip()
    # Reject path traversal and absolute paths (keep it simple & safe).
    if ".." in p or p.startswith("/") or p.startswith("\\"):
        return False, "vrm_model_path must not contain '..' or be absolute"
    lower = p.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_VRM_EXTENSIONS):
        return False, (
            "vrm_model_path must end with one of: "
            + ", ".join(ALLOWED_VRM_EXTENSIONS)
        )
    return True, "ok"


def _parse_pose(pose_data):
    """Parse *pose_data* (JSON text or dict) into a normalised dict.

    Returns (ok, pose_dict_or_None, reason).
    """
    if pose_data is None:
        return False, None, "pose_data is required"

    if isinstance(pose_data, dict):
        raw = pose_data
    elif isinstance(pose_data, str):
        try:
            raw = json.loads(pose_data)
        except (json.JSONDecodeError, ValueError) as exc:
            return False, None, "pose_data JSON parse error: %s" % exc
        if not isinstance(raw, dict):
            return False, None, "pose_data JSON must be an object"
    else:
        return False, None, "pose_data must be a JSON string or dict"

    joints = raw.get("joints")
    if not isinstance(joints, dict):
        return False, None, "pose_data must contain a 'joints' object"
    if len(joints) > MAX_JOINTS:
        return False, None, "too many joints (max %d)" % MAX_JOINTS

    normalised = {}
    for joint_name, joint_data in joints.items():
        if not isinstance(joint_name, str) or not joint_name:
            return False, None, "joint name must be a non-empty string"
        if joint_name not in KNOWN_JOINTS:
            return False, None, "unknown joint: %s" % joint_name
        if not isinstance(joint_data, dict):
            return False, None, "joint '%s' must be an object" % joint_name

        pos = joint_data.get("position", [0.0, 0.0, 0.0])
        rot = joint_data.get("rotation", [0.0, 0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            return False, None, "joint '%s' position must be [x,y,z]" % joint_name
        if not isinstance(rot, (list, tuple)) or len(rot) != 3:
            return False, None, "joint '%s' rotation must be [x,y,z]" % joint_name
        for label, vec in (("position", pos), ("rotation", rot)):
            for i, v in enumerate(vec):
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    return False, None, (
                        "joint '%s' %s[%d] must be a number"
                        % (joint_name, label, i)
                    )
                if abs(v) > MAX_COMPONENT:
                    return False, None, (
                        "joint '%s' %s[%d] out of range"
                        % (joint_name, label, i)
                    )
        normalised[joint_name] = {
            "position": [float(pos[0]), float(pos[1]), float(pos[2])],
            "rotation": [float(rot[0]), float(rot[1]), float(rot[2])],
        }
    return True, normalised, "ok"


def _apply_edit(pose, edit_mode, joint_name, delta):
    """Apply *edit_mode* with *delta* to *joint_name* in *pose*.

    *delta* is a 3-element list/tuple of floats.
    Returns (ok, edited_pose, reason).
    """
    if edit_mode not in EDIT_MODES:
        return False, None, "edit_mode must be one of %s" % (EDIT_MODES,)
    if not isinstance(joint_name, str) or not joint_name:
        return False, None, "joint_name must be a non-empty string"
    if joint_name not in KNOWN_JOINTS:
        return False, None, "unknown joint: %s" % joint_name
    if joint_name not in pose:
        return False, None, "joint '%s' not present in pose" % joint_name
    if not isinstance(delta, (list, tuple)) or len(delta) != 3:
        return False, None, "delta must be a 3-element list"
    for i, v in enumerate(delta):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False, None, "delta[%d] must be a number" % i
        if abs(v) > MAX_COMPONENT:
            return False, None, "delta[%d] out of range" % i

    # Deep-copy the joint so we don't mutate the input.
    joint = dict(pose[joint_name])
    joint["position"] = list(joint["position"])
    joint["rotation"] = list(joint["rotation"])

    if edit_mode == "translate":
        for i in range(3):
            joint["position"][i] += float(delta[i])
    elif edit_mode == "rotate":
        for i in range(3):
            joint["rotation"][i] += float(delta[i])

    edited = {k: dict(v) for k, v in pose.items()}
    edited[joint_name] = joint
    return True, edited, "ok"


def _make_preview_token(vrm_path, pose, edit_mode, joint_name, delta):
    """Deterministic token a renderer could use to fetch/generate a preview."""
    payload = {
        "vrm": vrm_path,
        "pose": pose,
        "edit_mode": edit_mode,
        "joint": joint_name,
        "delta": list(delta),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_VRMPoseEditor_Edit:
    """Validate a VRM path, parse a pose, apply one edit, and emit a preview token."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vrm_model_path": ("STRING", {"default": "model.vrm"}),
                "pose_data": ("STRING", {"default": "{}", "multiline": True}),
                "edit_mode": (list(EDIT_MODES),),
                "joint_name": (sorted(KNOWN_JOINTS),),
                "delta_x": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.001}),
                "delta_y": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.001}),
                "delta_z": ("FLOAT", {"default": 0.0, "min": -1e6, "max": 1e6, "step": 0.001}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("edited_vrm_pose", "preview_token", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/VRM"

    def run(self, vrm_model_path, pose_data, edit_mode, joint_name,
            delta_x, delta_y, delta_z):
        # 1. Validate VRM path
        ok, reason = _validate_vrm_path(vrm_model_path)
        if not ok:
            return ("{}", "", "ERROR: %s" % reason)

        # 2. Parse pose
        ok, pose, reason = _parse_pose(pose_data)
        if not ok:
            return ("{}", "", "ERROR: %s" % reason)

        # 3. Apply edit
        delta = [float(delta_x), float(delta_y), float(delta_z)]
        ok, edited, reason = _apply_edit(pose, edit_mode, joint_name, delta)
        if not ok:
            return (json.dumps({"joints": pose}, sort_keys=True), "", "ERROR: %s" % reason)

        # 4. Preview token
        token = _make_preview_token(vrm_model_path, edited, edit_mode,
                                    joint_name, delta)

        return (
            json.dumps({"joints": edited}, sort_keys=True),
            token,
            "ok",
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_VRMPoseEditor_Edit": PSN_VRMPoseEditor_Edit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VRMPoseEditor_Edit": "VRM Pose Editor (Edit)",
}
