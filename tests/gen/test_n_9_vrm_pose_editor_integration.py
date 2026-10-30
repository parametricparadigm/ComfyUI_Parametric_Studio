"""Tests for psn_nodes.gen.n_9_vrm_pose_editor_integration."""

import json

from psn_nodes.gen.n_9_vrm_pose_editor_integration import (
    PSN_VRMPoseEditor_Edit,
    _validate_vrm_path,
    _parse_pose,
    _apply_edit,
    _make_preview_token,
    EDIT_MODES,
    KNOWN_JOINTS,
)


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def test_validate_vrm_path_ok():
    ok, reason = _validate_vrm_path("models/character.vrm")
    assert ok is True
    assert reason == "ok"


def test_validate_vrm_path_bad_extension():
    ok, reason = _validate_vrm_path("models/character.obj")
    assert ok is False
    assert "must end with" in reason


def test_validate_vrm_path_traversal():
    ok, reason = _validate_vrm_path("../../etc/passwd.vrm")
    assert ok is False
    assert ".." in reason


def test_validate_vrm_path_empty():
    ok, reason = _validate_vrm_path("")
    assert ok is False


# ---------------------------------------------------------------------------
# Pose parsing
# ---------------------------------------------------------------------------

def test_parse_pose_valid_json():
    pose_json = json.dumps({
        "joints": {
            "hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0]},
            "head": {"position": [0.0, 2.0, 0.0], "rotation": [0.1, 0.2, 0.3]},
        }
    })
    ok, pose, reason = _parse_pose(pose_json)
    assert ok is True
    assert "hips" in pose
    assert pose["head"]["rotation"] == [0.1, 0.2, 0.3]


def test_parse_pose_unknown_joint():
    pose_json = json.dumps({"joints": {"nonexistent": {"position": [0, 0, 0], "rotation": [0, 0, 0]}}})
    ok, pose, reason = _parse_pose(pose_json)
    assert ok is False
    assert "unknown joint" in reason


def test_parse_pose_bad_json():
    ok, pose, reason = _parse_pose("{not valid json")
    assert ok is False
    assert "parse error" in reason


def test_parse_pose_dict_input():
    pose_dict = {"joints": {"spine": {"position": [0, 0, 0], "rotation": [0, 0, 0]}}}
    ok, pose, reason = _parse_pose(pose_dict)
    assert ok is True
    assert "spine" in pose


# ---------------------------------------------------------------------------
# Edit application
# ---------------------------------------------------------------------------

def test_apply_edit_translate():
    pose = {"hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0]}}
    ok, edited, reason = _apply_edit(pose, "translate", "hips", [0.1, 0.2, 0.3])
    assert ok is True
    assert edited["hips"]["position"] == [0.1, 1.2, 0.3]
    # Original unchanged
    assert pose["hips"]["position"] == [0.0, 1.0, 0.0]


def test_apply_edit_rotate():
    pose = {"head": {"position": [0.0, 2.0, 0.0], "rotation": [0.0, 0.0, 0.0]}}
    ok, edited, reason = _apply_edit(pose, "rotate", "head", [0.5, 0.0, 0.0])
    assert ok is True
    assert edited["head"]["rotation"] == [0.5, 0.0, 0.0]
    assert edited["head"]["position"] == [0.0, 2.0, 0.0]


def test_apply_edit_joint_not_in_pose():
    pose = {"hips": {"position": [0, 0, 0], "rotation": [0, 0, 0]}}
    ok, edited, reason = _apply_edit(pose, "translate", "head", [1, 0, 0])
    assert ok is False
    assert "not present" in reason


def test_apply_edit_bad_mode():
    pose = {"hips": {"position": [0, 0, 0], "rotation": [0, 0, 0]}}
    ok, edited, reason = _apply_edit(pose, "scale", "hips", [1, 1, 1])
    assert ok is False
    assert "edit_mode" in reason


# ---------------------------------------------------------------------------
# Preview token
# ---------------------------------------------------------------------------

def test_preview_token_deterministic():
    pose = {"hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0]}}
    t1 = _make_preview_token("m.vrm", pose, "translate", "hips", [0.1, 0, 0])
    t2 = _make_preview_token("m.vrm", pose, "translate", "hips", [0.1, 0, 0])
    assert t1 == t2
    assert len(t1) == 64  # sha256 hex


def test_preview_token_differs_on_change():
    pose = {"hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0]}}
    t1 = _make_preview_token("m.vrm", pose, "translate", "hips", [0.1, 0, 0])
    t2 = _make_preview_token("m.vrm", pose, "translate", "hips", [0.2, 0, 0])
    assert t1 != t2


# ---------------------------------------------------------------------------
# Node end-to-end
# ---------------------------------------------------------------------------

def test_node_run_success():
    node = PSN_VRMPoseEditor_Edit()
    pose_json = json.dumps({
        "joints": {
            "hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0]},
        }
    })
    edited_str, token, status = node.run(
        vrm_model_path="model.vrm",
        pose_data=pose_json,
        edit_mode="translate",
        joint_name="hips",
        delta_x=0.5,
        delta_y=0.0,
        delta_z=0.0,
    )
    assert status == "ok"
    assert len(token) == 64
    edited = json.loads(edited_str)
    assert edited["joints"]["hips"]["position"] == [0.5, 1.0, 0.0]


def test_node_run_bad_path():
    node = PSN_VRMPoseEditor_Edit()
    pose_json = json.dumps({"joints": {"hips": {"position": [0, 0, 0], "rotation": [0, 0, 0]}}})
    edited_str, token, status = node.run(
        vrm_model_path="../evil.vrm",
        pose_data=pose_json,
        edit_mode="translate",
        joint_name="hips",
        delta_x=0.0,
        delta_y=0.0,
        delta_z=0.0,
    )
    assert status.startswith("ERROR")
    assert token == ""


def test_node_run_bad_pose():
    node = PSN_VRMPoseEditor_Edit()
    edited_str, token, status = node.run(
        vrm_model_path="model.vrm",
        pose_data="not json at all",
        edit_mode="translate",
        joint_name="hips",
        delta_x=0.0,
        delta_y=0.0,
        delta_z=0.0,
    )
    assert status.startswith("ERROR")
    assert "parse error" in status
