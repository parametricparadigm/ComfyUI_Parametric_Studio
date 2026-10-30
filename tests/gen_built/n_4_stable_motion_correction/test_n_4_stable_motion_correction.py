import math

import torch

from n_4_stable_motion_correction import (
    PSN_VideoStabilizer,
    PSN_TimelineStabilizer,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def _shaky_video(b=4, h=16, w=16, shift=2):
    """A small video where a bright square moves by `shift` px each frame."""
    frames = []
    for i in range(b):
        f = torch.full((h, w, 3), 0.1, dtype=torch.float32)
        dx = i * shift
        for y in range(4, 8):
            for x in range(4, 8):
                nx = x + dx
                if 0 <= nx < w:
                    f[y, nx, :] = 0.9
        frames.append(f)
    return torch.stack(frames)


def test_module_mappings():
    assert "PSN_VideoStabilizer" in NODE_CLASS_MAPPINGS
    assert "PSN_TimelineStabilizer" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_VideoStabilizer"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_TimelineStabilizer"]
    for name, cls in NODE_CLASS_MAPPINGS.items():
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert cls.RETURN_TYPES == ("IMAGE",)
        it = cls.INPUT_TYPES()
        assert "required" in it


def test_stabilizer_shape_and_range():
    vid = _shaky_video(b=4, h=16, w=16, shift=2)
    node = PSN_VideoStabilizer()
    (out,) = node.run(vid, strength=0.8, smoothing=3)
    assert out.shape == vid.shape
    assert out.dtype == torch.float32
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_stabilizer_reduces_motion():
    """After stabilization the per-frame mean x of the bright square
    should be flatter (lower variance) than in the input."""
    vid = _shaky_video(b=5, h=16, w=16, shift=2)
    node = PSN_VideoStabilizer()
    (out,) = node.run(vid, strength=1.0, smoothing=3)

    def mean_x(frames):
        vals = []
        for f in frames:
            mask = (f[..., 0] > 0.5).nonzero()
            if mask.numel() == 0:
                vals.append(0.0)
            else:
                vals.append(float(mask[:, 1].float().mean()))
        return vals

    in_vals = mean_x(vid)
    out_vals = mean_x(out)
    in_var = torch.tensor(in_vals).var().item()
    out_var = torch.tensor(out_vals).var().item()
    assert out_var < in_var, ("expected reduced motion variance", in_var, out_var)


def test_stabilizer_single_frame_passthrough():
    vid = torch.rand(1, 8, 8, 3)
    node = PSN_VideoStabilizer()
    (out,) = node.run(vid, strength=0.5, smoothing=1)
    assert out.shape == vid.shape
    assert torch.allclose(out, vid, atol=1e-6)


def test_stabilizer_strength_zero_is_identity():
    vid = _shaky_video(b=3, h=16, w=16, shift=2)
    node = PSN_VideoStabilizer()
    (out,) = node.run(vid, strength=0.0, smoothing=3)
    assert torch.allclose(out, vid, atol=1e-5)


def test_stabilizer_bad_inputs():
    node = PSN_VideoStabilizer()
    vid = _shaky_video(b=3, h=16, w=16, shift=1)
    # non-tensor
    try:
        node.run("not a tensor", 0.5, 3)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # wrong dim
    try:
        node.run(torch.rand(4, 4, 3), 0.5, 3)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # bad strength
    try:
        node.run(vid, 1.5, 3)
        raise AssertionError("expected ValueError for strength")
    except ValueError:
        pass
    # bad smoothing
    try:
        node.run(vid, 0.5, 0)
        raise AssertionError("expected ValueError for smoothing")
    except ValueError:
        pass


def test_timeline_shape_and_count():
    # 5 frames at 10 fps = 0.4 s; at 20 fps -> 0.4*20+1 = 9 frames
    vid = torch.rand(5, 8, 8, 3)
    node = PSN_TimelineStabilizer()
    (out,) = node.run(vid, fps=20.0, src_fps=10.0)
    assert out.shape[0] == 9
    assert out.shape[1:] == (8, 8, 3)
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_timeline_downsample_dups_frames():
    # 5 frames at 20 fps = 0.2 s; at 10 fps -> 0.2*10+1 = 3 frames
    vid = torch.zeros(5, 4, 4, 3)
    for i in range(5):
        vid[i, :, :, 0] = i / 4.0
    node = PSN_TimelineStabilizer()
    (out,) = node.run(vid, fps=10.0, src_fps=20.0)
    assert out.shape[0] == 3
    # first and last frames should match the source endpoints
    assert torch.allclose(out[0], vid[0], atol=1e-6)
    assert torch.allclose(out[-1], vid[-1], atol=1e-6)


def test_timeline_identity_when_same_fps():
    vid = torch.rand(4, 8, 8, 3)
    node = PSN_TimelineStabilizer()
    (out,) = node.run(vid, fps=24.0, src_fps=24.0)
    assert out.shape == vid.shape
    assert torch.allclose(out, vid, atol=1e-6)


def test_timeline_bad_inputs():
    node = PSN_TimelineStabilizer()
    vid = torch.rand(3, 4, 4, 3)
    try:
        node.run(vid, fps=0.0, src_fps=24.0)
        raise AssertionError("expected ValueError for fps=0")
    except ValueError:
        pass
    try:
        node.run(vid, fps=24.0, src_fps=-1.0)
        raise AssertionError("expected ValueError for src_fps<0")
    except ValueError:
        pass
    try:
        node.run("nope", 24.0, 24.0)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_inputs_not_modified():
    vid = _shaky_video(b=3, h=16, w=16, shift=2)
    vid_copy = vid.clone()
    PSN_VideoStabilizer().run(vid, 0.8, 3)
    assert torch.equal(vid, vid_copy)

    vid2 = torch.rand(5, 8, 8, 3)
    vid2_copy = vid2.clone()
    PSN_TimelineStabilizer().run(vid2, 20.0, 10.0)
    assert torch.equal(vid2, vid2_copy)


if __name__ == "__main__":
    test_module_mappings()
    test_stabilizer_shape_and_range()
    test_stabilizer_reduces_motion()
    test_stabilizer_single_frame_passthrough()
    test_stabilizer_strength_zero_is_identity()
    test_stabilizer_bad_inputs()
    test_timeline_shape_and_count()
    test_timeline_downsample_dups_frames()
    test_timeline_identity_when_same_fps()
    test_timeline_bad_inputs()
    test_inputs_not_modified()
    print("ok")
