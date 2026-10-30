import json
import math

from psn_nodes.gen.n_2_deterministic_camera_motion import (
    PSN_Camera_Path_Definer,
    PSN_Camera_Apply,
    _parse_keyframes,
    _interp_dim,
    _catmull_rom,
)


def _two_kf():
    return json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 10, "x": 10, "y": 10, "z": 1, "rot": 0},
    ])


def test_linear_midpoint():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "linear", 100)
    assert curve["type"] == "KEYFRAMED_CURVE"
    assert "error" not in curve
    app = PSN_Camera_Apply()
    _, px, py, _, _ = app.run(curve, 5)
    assert math.isclose(px, 5.0, abs_tol=1e-9)
    assert math.isclose(py, 5.0, abs_tol=1e-9)


def test_step_holds_until_next_keyframe():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "step", 100)
    app = PSN_Camera_Apply()
    _, px, _, _, _ = app.run(curve, 9)
    assert math.isclose(px, 0.0, abs_tol=1e-9)
    _, px2, _, _, _ = app.run(curve, 10)
    assert math.isclose(px2, 10.0, abs_tol=1e-9)


def test_cubic_endpoints_match_keyframes():
    node = PSN_Camera_Path_Definer()
    curve, _ = node.run(_two_kf(), "cubic", 100)
    app = PSN_Camera_Apply()
    _, px0, _, _, _ = app.run(curve, 0)
    _, px10, _, _, _ = app.run(curve, 10)
    assert math.isclose(px0, 0.0, abs_tol=1e-9)
    assert math.isclose(px10, 10.0, abs_tol=1e-9)


def test_smoke_no_nans_over_100_frames():
    node = PSN_Camera_Path_Definer()
    kfs = json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 50, "x": 20, "y": -10, "z": 2, "rot": 90},
        {"frame": 100, "x": 5, "y": 5, "z": 1, "rot": 180},
    ])
    curve, _ = node.run(kfs, "cubic", 100)
    app = PSN_Camera_Apply()
    for f in range(100):
        _, px, py, zoom, rot = app.run(curve, f)
        for v in (px, py, zoom, rot):
            assert not math.isnan(v)
            assert not math.isinf(v)


def test_invalid_json_returns_error_curve():
    node = PSN_Camera_Path_Definer()
    curve, preview = node.run("not json {", "linear", 10)
    assert curve["type"] == "KEYFRAMED_CURVE"
    assert "error" in curve
    assert preview.startswith("ERROR:")


def test_bad_input_non_numeric_dim():
    bad = json.dumps([{"frame": 0, "x": "ten", "y": 0, "z": 1, "rot": 0}])
    parsed, err = _parse_keyframes(bad)
    assert parsed is None
    assert err is not None
    assert "number" in err


def test_duplicate_frames_rejected():
    bad = json.dumps([
        {"frame": 0, "x": 0, "y": 0, "z": 1, "rot": 0},
        {"frame": 0, "x": 1, "y": 1, "z": 1, "rot": 0},
    ])
    parsed, err = _parse_keyframes(bad)
    assert parsed is None
    assert "duplicate" in err


def test_catmull_rom_midpoint_equals_linear_for_collinear():
    # For equally spaced collinear points, Catmull-Rom at t=0.5 equals linear.
    val = _catmull_rom(0.0, 1.0, 2.0, 3.0, 0.5)
    assert math.isclose(val, 1.5, abs_tol=1e-9)


def test_interp_dim_clamps_out_of_range():
    values = [0.0, 10.0]
    frames = [0, 10]
    assert _interp_dim(values, frames, -5, "linear") == 0.0
    assert _interp_dim(values, frames, 99, "linear") == 10.0


def test_apply_invalid_curve():
    app = PSN_Camera_Apply()
    out, px, py, zoom, rot = app.run({"type": "WRONG"}, 0)
    assert out.startswith("ERROR:")
    assert px == 0.0 and py == 0.0 and zoom == 1.0 and rot == 0.0
