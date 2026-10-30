import json

import pytest

from psn_nodes.gen.n_7_hymotion_to_scail_conversion import (
    PSN_HYMotionToSCAIL_Convert,
    convert_hymotion_to_scail,
    _transform_position,
    _transform_rotation,
    _normalize_quat,
)


def _make_hymotion():
    return {
        "frames": [
            {
                "Hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
                "Head": {"position": [0.0, 2.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
            },
            {
                "Hips": {"position": [0.1, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
            },
        ]
    }


def test_convert_produces_valid_sequence():
    pose_sequence, log = convert_hymotion_to_scail(_make_hymotion(), "{}")
    assert pose_sequence is not None
    assert pose_sequence["frame_count"] == 2
    assert len(pose_sequence["frames"]) == 2
    assert "Hips" in pose_sequence["bones"]
    assert "Head" in pose_sequence["bones"]
    assert "Parsed 2 HYMotion frame(s)." in log


def test_convert_coordinate_flip_y():
    # Identity rotation: position (0,1,0) -> flip Y -> (0,-1,0).
    pose_sequence, _ = convert_hymotion_to_scail(_make_hymotion(), "{}")
    hips = pose_sequence["frames"][0]["Hips"]
    assert hips["position"] == [0.0, -1.0, 0.0]
    assert hips["rotation"] == [0.0, 0.0, 0.0, 1.0]


def test_convert_rotation_mirror():
    # A 90-degree rotation about X: (0.7071, 0, 0, 0.7071) -> y sign flipped.
    data = {
        "frames": [
            {"Hips": {"position": [0.0, 0.0, 0.0], "rotation": [0.7071, 0.0, 0.0, 0.7071]}}
        ]
    }
    pose_sequence, _ = convert_hymotion_to_scail(data, "{}")
    hips = pose_sequence["frames"][0]["Hips"]
    assert hips["rotation"][0] == pytest.approx(0.7071, abs=1e-4)
    assert hips["rotation"][1] == pytest.approx(0.0, abs=1e-4)
    assert hips["rotation"][3] == pytest.approx(0.7071, abs=1e-4)


def test_convert_unmapped_bone_warning():
    data = {
        "frames": [
            {"Hips": {"position": [0.0, 1.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
             "CustomBone": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0]}}
        ]
    }
    pose_sequence, log = convert_hymotion_to_scail(data, "{}")
    assert pose_sequence is not None
    assert "CustomBone" not in pose_sequence["bones"]
    assert "WARNING: unmapped bone(s): CustomBone" in log


def test_convert_bad_hymotion_json():
    pose_sequence, log = convert_hymotion_to_scail("{not json", "{}")
    assert pose_sequence is None
    assert log.startswith("ERROR:")


def test_convert_missing_frames():
    pose_sequence, log = convert_hymotion_to_scail({"frames": []}, "{}")
    assert pose_sequence is None
    assert "non-empty" in log


def test_convert_invalid_position():
    data = {"frames": [{"Hips": {"position": [0.0, 1.0], "rotation": [0.0, 0.0, 0.0, 1.0]}}]}
    pose_sequence, log = convert_hymotion_to_scail(data, "{}")
    assert pose_sequence is None
    assert "invalid position" in log


def test_convert_bad_scail_config():
    pose_sequence, log = convert_hymotion_to_scail(_make_hymotion(), "{bad")
    assert pose_sequence is None
    assert "scail_config" in log


def test_node_run_returns_json_and_log():
    node = PSN_HYMotionToSCAIL_Convert()
    sequence, log = node.run(_make_hymotion(), "{}")
    assert isinstance(sequence, str)
    parsed = json.loads(sequence)
    assert parsed["frame_count"] == 2
    assert isinstance(log, str)


def test_node_run_bad_input_returns_none_sequence():
    node = PSN_HYMotionToSCAIL_Convert()
    sequence, log = node.run("not json", "{}")
    assert sequence is None
    assert log.startswith("ERROR:")


def test_normalize_quat_zero():
    assert _normalize_quat([0.0, 0.0, 0.0, 0.0]) == (0.0, 0.0, 0.0, 1.0)


def test_transform_position_identity():
    assert _transform_position([1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0]) == (1.0, -2.0, 3.0)
