"""Tests for n_2_high_fps_temporal_smoothing (plain asserts, no pytest)."""

import math

import torch

from n_2_high_fps_temporal_smoothing import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    PSN_FPSResampler,
    PSN_FrameInterpolator,
)


def _img(n, h=4, w=4, c=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(n, h, w, c, generator=g)


# 1. Module-level mappings exist and are consistent.
assert set(NODE_CLASS_MAPPINGS) == {"PSN_FrameInterpolator", "PSN_FPSResampler"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
for name, cls in NODE_CLASS_MAPPINGS.items():
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    assert cls.RETURN_TYPES == ("IMAGE",)
    assert isinstance(cls.INPUT_TYPES(), dict)

# 2. Interpolator: 10 frames 24 -> 48 fps gives 20 frames (2x).
img = _img(10)
node = PSN_FrameInterpolator()
(out,) = node.run(img, 24.0, 48.0)
assert out.shape[0] == 20, out.shape
assert out.shape[1:] == img.shape[1:]
assert out.dtype == torch.float32
# Input must not be modified in place.
assert out.data_ptr() != img.data_ptr()

# 3. Interpolator: blended frames are actual linear blends.
img2 = _img(2, seed=1)
img2[0].fill_(0.0)
img2[1].fill_(1.0)
(out2,) = PSN_FrameInterpolator().run(img2, 10.0, 30.0)  # ratio 3 -> 6 frames
assert out2.shape[0] == 6, out2.shape
# Single gap gets all 4 inserts -> blends at t = 1/5, 2/5, 3/5, 4/5.
assert torch.allclose(out2[1], torch.full_like(out2[1], 0.2))
assert torch.allclose(out2[2], torch.full_like(out2[1], 0.4))
assert torch.allclose(out2[3], torch.full_like(out2[1], 0.6))
assert torch.allclose(out2[4], torch.full_like(out2[1], 0.8))
assert torch.allclose(out2[5], img2[1])

# 4. Interpolator: target <= source returns a copy with same frame count.
img3 = _img(7, seed=2)
(out3,) = PSN_FrameInterpolator().run(img3, 60.0, 30.0)
assert out3.shape[0] == 7
assert torch.equal(out3, img3)

# 5. Resampler nearest: 30 -> 60 fps doubles frame count.
img4 = _img(10, seed=3)
(out4,) = PSN_FPSResampler().run(img4, 30.0, 60.0, "nearest")
assert out4.shape[0] == 20, out4.shape
# Nearest resampling must only ever pick original frames.
for i in range(out4.shape[0]):
    assert any(torch.equal(out4[i], img4[j]) for j in range(10))

# 6. Resampler linear: 30 -> 15 fps halves frame count, values are blends.
img5 = _img(4, seed=4)
img5[0].fill_(0.0)
img5[3].fill_(1.0)
(out5,) = PSN_FPSResampler().run(img5, 30.0, 15.0, "linear")
assert out5.shape[0] == 2, out5.shape
# positions: 0.0 and 2.0 -> frames 0 and 2 (frame 2 is 0.666 blend)
assert torch.allclose(out5[0], img5[0])
assert torch.allclose(out5[1], img5[2])

# 7. Edge case: single frame input, upsample keeps at least 1 frame.
img6 = _img(1, seed=5)
(out6,) = PSN_FPSResampler().run(img6, 24.0, 96.0, "nearest")
assert out6.shape[0] >= 1
assert torch.equal(out6[0], img6[0])

# 8. Bad input: non-tensor raises TypeError.
try:
    PSN_FPSResampler().run("not a tensor", 30.0, 60.0, "nearest")
    raise AssertionError("expected TypeError")
except TypeError:
    pass

# 9. Bad input: 3D tensor raises ValueError.
try:
    PSN_FrameInterpolator().run(torch.rand(4, 4, 3), 24.0, 48.0)
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 10. Bad input: non-positive fps raises ValueError.
try:
    PSN_FPSResampler().run(_img(2), 0.0, 60.0, "nearest")
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 11. Bad input: invalid mode raises ValueError.
try:
    PSN_FPSResampler().run(_img(2), 30.0, 60.0, "cubic")
    raise AssertionError("expected ValueError")
except ValueError:
    pass

# 12. Resampler nearest downsample drops frames correctly (60 -> 30).
img7 = _img(6, seed=6)
(out7,) = PSN_FPSResampler().run(img7, 60.0, 30.0, "nearest")
assert out7.shape[0] == 3, out7.shape
assert torch.equal(out7[0], img7[0])
assert torch.equal(out7[1], img7[2])
assert torch.equal(out7[2], img7[4])

print("ok")
