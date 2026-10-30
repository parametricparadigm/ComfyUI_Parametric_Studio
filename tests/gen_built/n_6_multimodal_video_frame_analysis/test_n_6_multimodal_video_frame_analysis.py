import json
import torch

import n_6_multimodal_video_frame_analysis as m


def make_frames(specs):
    """specs: list of (H, W, C, value) -> tensor [N,H,W,C] in 0..1."""
    ts = []
    for (h, w, c, v) in specs:
        ts.append(torch.full((h, w, c), float(v)))
    return torch.stack(ts)


def test_mappings():
    assert "PSN_Scene_Transition_Detector" in m.NODE_CLASS_MAPPINGS
    assert "PSN_Video_Frame_Captioner" in m.NODE_CLASS_MAPPINGS
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Video_Frame_Captioner"] == "PSN Video Frame Captioner"
    for name, cls in m.NODE_CLASS_MAPPINGS.items():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert hasattr(cls, "INPUT_TYPES")
        cls.INPUT_TYPES()


def test_detector_abrupt_change():
    # 4 frames: two identical dark, then two identical bright -> boundary at index 2
    frames = make_frames([(8, 8, 3, 0.1), (8, 8, 3, 0.1), (8, 8, 3, 0.9), (8, 8, 3, 0.9)])
    node = m.PSN_Scene_Transition_Detector()
    bounds, js = node.run(frames, 0.35, 16)
    assert list(bounds) == [2], bounds
    assert json.loads(js) == [2]


def test_detector_no_change():
    frames = make_frames([(8, 8, 3, 0.5), (8, 8, 3, 0.5), (8, 8, 3, 0.5)])
    node = m.PSN_Scene_Transition_Detector()
    bounds, _ = node.run(frames, 0.35, 16)
    assert list(bounds) == []


def test_detector_bad_input():
    node = m.PSN_Scene_Transition_Detector()
    # wrong number of dims
    try:
        node.run(torch.zeros(8, 8, 3), 0.35, 16)
        raise AssertionError("expected ValueError for 3D input")
    except ValueError:
        pass
    # non-tensor
    try:
        node.run([0.1, 0.2], 0.35, 16)
        raise AssertionError("expected TypeError for non-tensor")
    except TypeError:
        pass


def test_captioner_aggregation():
    frames = make_frames([(8, 8, 3, 0.1), (8, 8, 3, 0.1), (8, 8, 3, 0.9), (8, 8, 3, 0.9)])
    node = m.PSN_Video_Frame_Captioner()
    narrative, moments = node.run(frames, 1, "a cat walks\na dog runs\nthe sun sets\nthe night falls")
    assert "Frame 0: a cat walks" in narrative
    assert "Frame 3: the night falls" in narrative
    km = json.loads(moments)
    assert isinstance(km, list) and len(km) >= 2
    # boundary at 2 should be a key moment
    assert any(k["frame"] == 2 for k in km), km
    assert km[0]["frame"] == 0 and km[-1]["frame"] == 3


def test_captioner_interval_and_placeholders():
    frames = make_frames([(8, 8, 3, 0.2), (8, 8, 3, 0.2), (8, 8, 3, 0.2), (8, 8, 3, 0.2)])
    node = m.PSN_Video_Frame_Captioner()
    # interval 2 -> frames 0 and 2 selected; only one mock provided -> placeholder for second
    narrative, moments = node.run(frames, 2, "first only")
    assert "Frame 0: first only" in narrative
    assert "Frame 2: (frame 2)" in narrative
    km = json.loads(moments)
    assert km[0]["frame"] == 0 and km[-1]["frame"] == 3


def test_captioner_bad_interval():
    frames = make_frames([(8, 8, 3, 0.2), (8, 8, 3, 0.2)])
    node = m.PSN_Video_Frame_Captioner()
    try:
        node.run(frames, 0, "")
        raise AssertionError("expected ValueError for interval 0")
    except ValueError:
        pass


def test_no_inplace_mutation():
    frames = make_frames([(8, 8, 3, 0.1), (8, 8, 3, 0.9)])
    snapshot = frames.clone()
    m.PSN_Scene_Transition_Detector().run(frames, 0.35, 16)
    m.PSN_Video_Frame_Captioner().run(frames, 1, "x\ny")
    assert torch.equal(frames, snapshot)


if __name__ == "__main__":
    test_mappings()
    test_detector_abrupt_change()
    test_detector_no_change()
    test_detector_bad_input()
    test_captioner_aggregation()
    test_captioner_interval_and_placeholders()
    test_captioner_bad_interval()
    test_no_inplace_mutation()
    print("ok")
