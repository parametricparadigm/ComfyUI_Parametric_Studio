import json
import math

import torch

import n_8_timeline_based_camera_direction as M


def test_editor_interpolation():
    kf = json.dumps([
        {"time": 0.0, "position": [0.0, 0.0, 0.0], "zoom": 1.0},
        {"time": 1.0, "position": [2.0, 0.0, 0.0], "zoom": 3.0},
    ])
    node = M.PSN_CameraTimelineEditor()
    (curve,) = node.run(kf, 1.0, 3)
    samples = json.loads(curve)
    assert len(samples) == 3
    # endpoints
    assert samples[0]["position"] == [0.0, 0.0, 0.0]
    assert samples[0]["zoom"] == 1.0
    assert samples[-1]["position"] == [2.0, 0.0, 0.0]
    assert samples[-1]["zoom"] == 3.0
    # midpoint: smoothstep(0.5) = 0.5 -> x = 1.0, zoom = 2.0
    mid = samples[1]
    assert abs(mid["position"][0] - 1.0) < 1e-9
    assert abs(mid["zoom"] - 2.0) < 1e-9
    # monotonic x
    assert samples[0]["position"][0] <= samples[1]["position"][0] <= samples[-1]["position"][0]


def test_editor_bad_input():
    node = M.PSN_CameraTimelineEditor()
    # not a list
    try:
        node.run("{\"time\": 0}", 1.0, 4)
        raise AssertionError("expected error for non-list keyframes")
    except ValueError:
        pass
    # empty list
    try:
        node.run("[]", 1.0, 4)
        raise AssertionError("expected error for empty keyframes")
    except ValueError:
        pass
    # bad position length
    try:
        node.run(json.dumps([{"time": 0, "position": [0, 0], "zoom": 1}]), 1.0, 4)
        raise AssertionError("expected error for bad position")
    except ValueError:
        pass
    # non-numeric time
    try:
        node.run(json.dumps([{"time": "a", "position": [0, 0, 0], "zoom": 1}]), 1.0, 4)
        raise AssertionError("expected error for bad time")
    except ValueError:
        pass


def test_editor_single_keyframe():
    kf = json.dumps([{"time": 0.0, "position": [1.0, 2.0, 3.0], "zoom": 2.0}])
    node = M.PSN_CameraTimelineEditor()
    (curve,) = node.run(kf, 5.0, 4)
    samples = json.loads(curve)
    assert len(samples) == 4
    for s in samples:
        assert s["position"] == [1.0, 2.0, 3.0]
        assert s["zoom"] == 2.0


def test_editor_unsorted_keyframes():
    kf = json.dumps([
        {"time": 2.0, "position": [4.0, 0.0, 0.0], "zoom": 5.0},
        {"time": 0.0, "position": [0.0, 0.0, 0.0], "zoom": 1.0},
    ])
    node = M.PSN_CameraTimelineEditor()
    (curve,) = node.run(kf, 2.0, 3)
    samples = json.loads(curve)
    assert samples[0]["position"] == [0.0, 0.0, 0.0]
    assert samples[-1]["position"] == [4.0, 0.0, 0.0]


def test_energy_mapper():
    kf = json.dumps([
        {"time": 0.0, "position": [0.0, 0.0, 0.0], "zoom": 1.0},
        {"time": 1.0, "position": [1.0, 0.0, 0.0], "zoom": 1.0},
        {"time": 2.0, "position": [2.0, 0.0, 0.0], "zoom": 1.0},
    ])
    editor = M.PSN_CameraTimelineEditor()
    (curve,) = editor.run(kf, 2.0, 4)
    # constant-amplitude sine: energy ~ constant
    sr = 44100
    t = torch.arange(0, sr * 2, dtype=torch.float32) / float(sr)
    wf = torch.sin(2 * math.pi * 440.0 * t).unsqueeze(0)
    audio = {"waveform": wf, "sample_rate": sr}
    mapper = M.PSN_EnergyCurveMapper()
    (out,) = mapper.run(curve, audio, 1.0, 1.0)
    synced = json.loads(out)
    assert len(synced) == 4
    for s in synced:
        assert "speed" in s and "zoom" in s and "energy" in s
        assert s["energy"] >= 0.0
    # with constant energy, zoom should be scaled by (1 + 0.5*e) > 1
    assert synced[0]["zoom"] > 1.0
    # speed should be positive for moving camera
    assert synced[0]["speed"] > 0.0


def test_energy_mapper_silence():
    kf = json.dumps([
        {"time": 0.0, "position": [0.0, 0.0, 0.0], "zoom": 1.0},
        {"time": 1.0, "position": [1.0, 0.0, 0.0], "zoom": 1.0},
    ])
    editor = M.PSN_CameraTimelineEditor()
    (curve,) = editor.run(kf, 1.0, 3)
    sr = 44100
    wf = torch.zeros(1, sr)
    audio = {"waveform": wf, "sample_rate": sr}
    mapper = M.PSN_EnergyCurveMapper()
    (out,) = mapper.run(curve, audio, 1.0, 1.0)
    synced = json.loads(out)
    for s in synced:
        assert s["energy"] == 0.0
        assert s["zoom"] == 1.0  # no scaling


def test_energy_mapper_bad_curve():
    mapper = M.PSN_EnergyCurveMapper()
    sr = 44100
    wf = torch.zeros(1, sr)
    audio = {"waveform": wf, "sample_rate": sr}
    try:
        mapper.run("not json", audio, 1.0, 1.0)
        raise AssertionError("expected error for bad curve")
    except ValueError:
        pass
    try:
        mapper.run(json.dumps([{"position": [0, 0, 0], "zoom": 1}]), audio, 1.0, 1.0)
        raise AssertionError("expected error for single-sample curve")
    except ValueError:
        pass


def test_module_mappings():
    assert "PSN_CameraTimelineEditor" in M.NODE_CLASS_MAPPINGS
    assert "PSN_EnergyCurveMapper" in M.NODE_CLASS_MAPPINGS
    assert M.NODE_CLASS_MAPPINGS["PSN_CameraTimelineEditor"].FUNCTION == "run"
    assert M.NODE_CLASS_MAPPINGS["PSN_CameraTimelineEditor"].RETURN_TYPES == ("STRING",)
    assert M.NODE_CLASS_MAPPINGS["PSN_EnergyCurveMapper"].RETURN_NAMES == ("synced_camera_params",)
    # INPUT_TYPES callable
    it = M.PSN_CameraTimelineEditor.INPUT_TYPES()
    assert "keyframes" in it["required"]
    assert "duration" in it["required"]


def main():
    test_editor_interpolation()
    test_editor_bad_input()
    test_editor_single_keyframe()
    test_editor_unsorted_keyframes()
    test_energy_mapper()
    test_energy_mapper_silence()
    test_energy_mapper_bad_curve()
    test_module_mappings()
    print("ok")


if __name__ == "__main__":
    main()
