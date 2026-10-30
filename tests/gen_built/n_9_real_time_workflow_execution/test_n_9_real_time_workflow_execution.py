import torch

import n_9_real_time_workflow_execution as m


def test_mappings():
    assert "PSN_Realtime_Loop" in m.NODE_CLASS_MAPPINGS
    assert "PSN_Motion_Detect" in m.NODE_CLASS_MAPPINGS
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Realtime_Loop"]
    for name, cls in m.NODE_CLASS_MAPPINGS.items():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.INPUT_TYPES(), dict)


def test_loop_emits_frames_and_last():
    node = m.PSN_Realtime_Loop()
    frames = torch.rand(3, 4, 4, 3)
    out1, last1 = node.run(frames, 30.0, pacing=False, reset=True)
    out2, last2 = node.run(frames, 30.0, pacing=False)
    out3, last3 = node.run(frames, 30.0, pacing=False)
    assert out1.shape == (1, 4, 4, 3)
    assert last1 is False and last2 is False and last3 is True
    # wraps around after last
    out4, last4 = node.run(frames, 30.0, pacing=False)
    assert last4 is False
    assert torch.equal(out4, out1)


def test_loop_bad_fps():
    node = m.PSN_Realtime_Loop()
    frames = torch.rand(2, 4, 4, 3)
    try:
        node.run(frames, 0.0)
        raise AssertionError("expected ValueError for fps<=0")
    except ValueError:
        pass


def test_loop_bad_image():
    node = m.PSN_Realtime_Loop()
    try:
        node.run("not a tensor", 30.0)
        raise AssertionError("expected TypeError for non-tensor")
    except TypeError:
        pass
    try:
        node.run(torch.rand(4, 4), 30.0)
        raise AssertionError("expected ValueError for wrong dims")
    except ValueError:
        pass


def test_motion_static_near_zero():
    node = m.PSN_Motion_Detect()
    frame = torch.rand(1, 8, 8, 3)
    mask, score = node.run(frame, frame.clone())
    assert mask.shape == (1, 8, 8, 1)
    assert abs(score) < 1e-6
    assert float(mask.sum().item()) == 0.0


def test_motion_different_frames():
    node = m.PSN_Motion_Detect()
    a = torch.zeros(1, 4, 4, 3)
    b = torch.ones(1, 4, 4, 3)
    mask, score = node.run(a, b, threshold=0.5)
    assert abs(score - 1.0) < 1e-6
    assert float(mask.sum().item()) == 16.0


def test_motion_shape_mismatch():
    node = m.PSN_Motion_Detect()
    a = torch.rand(1, 4, 4, 3)
    b = torch.rand(1, 5, 5, 3)
    try:
        node.run(a, b)
        raise AssertionError("expected ValueError for shape mismatch")
    except ValueError:
        pass


def test_no_inplace_mutation():
    node = m.PSN_Motion_Detect()
    a = torch.rand(1, 4, 4, 3)
    b = torch.rand(1, 4, 4, 3)
    a_copy = a.clone()
    b_copy = b.clone()
    node.run(a, b)
    assert torch.equal(a, a_copy)
    assert torch.equal(b, b_copy)


def test_fps_pacing_timing():
    import time
    node = m.PSN_Realtime_Loop()
    frames = torch.rand(2, 4, 4, 3)
    t0 = time.time()
    node.run(frames, 50.0, pacing=True, reset=True)
    node.run(frames, 50.0, pacing=True)
    elapsed = time.time() - t0
    # 2 frames at 50 fps => ~0.02s of pacing (only between, not after last)
    assert elapsed >= 0.015, f"pacing too fast: {elapsed}"


if __name__ == "__main__":
    test_mappings()
    test_loop_emits_frames_and_last()
    test_loop_bad_fps()
    test_loop_bad_image()
    test_motion_static_near_zero()
    test_motion_different_frames()
    test_motion_shape_mismatch()
    test_no_inplace_mutation()
    test_fps_pacing_timing()
    print("ok")
