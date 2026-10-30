"""Tests for PSN_ProportionAdjust_Modify (pure-logic proportion adjustment)."""

import json
import math

import pytest

from psn_nodes.gen.n_8_proportion_adjustment_tool import (
    PSN_ProportionAdjust_Modify,
    _BODY_TYPES,
    _parse_pose,
)


def _make_pose():
    """A simple symmetric pose with known geometry."""
    return [
        {"name": "head", "x": 0.0, "y": 0.0},
        {"name": "neck", "x": 0.0, "y": 1.0},
        {"name": "left_shoulder", "x": -1.0, "y": 1.0},
        {"name": "right_shoulder", "x": 1.0, "y": 1.0},
        {"name": "left_hip", "x": -1.0, "y": 3.0},
        {"name": "right_hip", "x": 1.0, "y": 3.0},
        {"name": "left_hand", "x": -2.0, "y": 1.0},
        {"name": "right_hand", "x": 2.0, "y": 1.0},
        {"name": "left_ankle", "x": -1.0, "y": 6.0},
        {"name": "right_ankle", "x": 1.0, "y": 6.0},
    ]


def _pose_text():
    return json.dumps(_make_pose())


def _dist(a, b):
    return math.hypot(b["x"] - a["x"], b["y"] - a["y"])


def test_muscular_increases_arm_length():
    node = PSN_ProportionAdjust_Modify()
    out_json, metrics = node.run(_pose_text(), "muscular", 1.0)
    out = json.loads(out_json)
    idx = {kp["name"]: kp for kp in out}
    # Left arm: left_shoulder -> left_hand
    orig = _make_pose()
    oidx = {kp["name"]: kp for kp in orig}
    orig_arm = _dist(oidx["left_shoulder"], oidx["left_hand"])
    new_arm = _dist(idx["left_shoulder"], idx["left_hand"])
    assert new_arm > orig_arm
    assert metrics > 0.0


def test_tall_increases_leg_length():
    node = PSN_ProportionAdjust_Modify()
    out_json, metrics = node.run(_pose_text(), "tall", 1.0)
    out = json.loads(out_json)
    idx = {kp["name"]: kp for kp in out}
    orig = _make_pose()
    oidx = {kp["name"]: kp for kp in orig}
    orig_leg = _dist(oidx["left_hip"], oidx["left_ankle"])
    new_leg = _dist(idx["left_hip"], idx["left_ankle"])
    assert new_leg > orig_leg
    assert metrics > 0.0


def test_neutral_no_change():
    node = PSN_ProportionAdjust_Modify()
    out_json, metrics = node.run(_pose_text(), "neutral", 1.0)
    out = json.loads(out_json)
    assert out == _make_pose()
    assert metrics == 0.0


def test_zero_strength_no_change():
    node = PSN_ProportionAdjust_Modify()
    out_json, metrics = node.run(_pose_text(), "muscular", 0.0)
    out = json.loads(out_json)
    assert out == _make_pose()
    assert metrics == 0.0


def test_partial_strength_blends():
    node = PSN_ProportionAdjust_Modify()
    out_json, _ = node.run(_pose_text(), "muscular", 0.5)
    out = json.loads(out_json)
    idx = {kp["name"]: kp for kp in out}
    orig = _make_pose()
    oidx = {kp["name"]: kp for kp in orig}
    orig_arm = _dist(oidx["left_shoulder"], oidx["left_hand"])
    new_arm = _dist(idx["left_shoulder"], idx["left_hand"])
    # At strength 0.5, factor 1.15 -> eff = 1 + 0.15*0.5 = 1.075
    expected = orig_arm * 1.075
    assert abs(new_arm - expected) < 1e-9


def test_invalid_json_raises():
    node = PSN_ProportionAdjust_Modify()
    with pytest.raises(ValueError):
        node.run("not json", "muscular", 1.0)


def test_non_list_json_raises():
    node = PSN_ProportionAdjust_Modify()
    with pytest.raises(ValueError):
        node.run('{"a": 1}', "muscular", 1.0)


def test_missing_name_raises():
    node = PSN_ProportionAdjust_Modify()
    bad = json.dumps([{"x": 0.0, "y": 0.0}])
    with pytest.raises(ValueError):
        node.run(bad, "muscular", 1.0)


def test_non_numeric_coord_raises():
    node = PSN_ProportionAdjust_Modify()
    bad = json.dumps([{"name": "head", "x": "abc", "y": 0.0}])
    with pytest.raises(ValueError):
        node.run(bad, "muscular", 1.0)


def test_unknown_body_type_raises():
    node = PSN_ProportionAdjust_Modify()
    with pytest.raises(ValueError):
        node.run(_pose_text(), "giant", 1.0)


def test_empty_pose_returns_empty():
    node = PSN_ProportionAdjust_Modify()
    out_json, metrics = node.run("[]", "muscular", 1.0)
    out = json.loads(out_json)
    assert out == []
    assert metrics == 0.0


def test_strength_clamped_above_two():
    node = PSN_ProportionAdjust_Modify()
    # strength > 2.0 is clamped to 2.0
    out_json, _ = node.run(_pose_text(), "muscular", 5.0)
    out = json.loads(out_json)
    idx = {kp["name"]: kp for kp in out}
    orig = _make_pose()
    oidx = {kp["name"]: kp for kp in orig}
    orig_arm = _dist(oidx["left_shoulder"], oidx["left_hand"])
    new_arm = _dist(idx["left_shoulder"], idx["left_hand"])
    # eff = 1 + 0.15*2.0 = 1.30
    expected = orig_arm * 1.30
    assert abs(new_arm - expected) < 1e-9
