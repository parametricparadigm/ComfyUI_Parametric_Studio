"""Tests for n_10_consistent_img2img_denoise."""

import math

import torch

import n_10_consistent_img2img_denoise as mod


# ---------------------------------------------------------------------------
# 1. module-level mappings exist and are consistent
# ---------------------------------------------------------------------------
def test_mappings():
    assert "PSN_Actual_Denoise" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_Denoise_Preview" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_CLASS_MAPPINGS["PSN_Actual_Denoise"] is mod.PSN_Actual_Denoise
    assert mod.NODE_CLASS_MAPPINGS["PSN_Denoise_Preview"] is mod.PSN_Denoise_Preview
    assert "PSN_Actual_Denoise" in mod.NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_Denoise_Preview" in mod.NODE_DISPLAY_NAME_MAPPINGS


# ---------------------------------------------------------------------------
# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY
# ---------------------------------------------------------------------------
def test_node_interface():
    for cls in (mod.PSN_Actual_Denoise, mod.PSN_Denoise_Preview):
        it = cls.INPUT_TYPES()
        assert "required" in it
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.RETURN_TYPES, tuple)
        assert isinstance(cls.RETURN_NAMES, tuple)
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)

    # PSN_Actual_Denoise specific
    it = mod.PSN_Actual_Denoise.INPUT_TYPES()
    for key in ("image", "denoise", "model", "positive", "negative", "latent"):
        assert key in it["required"], key
    assert mod.PSN_Actual_Denoise.RETURN_TYPES == ("LATENT",)
    assert mod.PSN_Actual_Denoise.RETURN_NAMES == ("samples",)

    # PSN_Denoise_Preview specific
    it2 = mod.PSN_Denoise_Preview.INPUT_TYPES()
    assert "image" in it2["required"]
    assert "denoise" in it2["required"]
    assert mod.PSN_Denoise_Preview.RETURN_TYPES == ("IMAGE",)
    assert mod.PSN_Denoise_Preview.RETURN_NAMES == ("preview",)


# ---------------------------------------------------------------------------
# 3. sigma schedule: correct shape, range, monotonic decrease, denoise=0
# ---------------------------------------------------------------------------
def test_sigma_schedule():
    s = mod._build_sigma_schedule(0.5, num_steps=10)
    assert s.shape == (10,)
    assert s.dtype == torch.float32
    assert s[0].item() == 0.5  # starts at denoise
    assert s[-1].item() > 0.0  # ends above 0
    # monotonically non-increasing
    for i in range(1, 10):
        assert s[i].item() <= s[i - 1].item() + 1e-7

    # denoise=0 -> all zeros
    s0 = mod._build_sigma_schedule(0.0, num_steps=5)
    assert (s0 == 0).all()

    # denoise=1 -> starts at 1
    s1 = mod._build_sigma_schedule(1.0, num_steps=3)
    assert abs(s1[0].item() - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# 4. PSN_Denoise_Preview: denoise=0 returns original image unchanged
# ---------------------------------------------------------------------------
def test_preview_denoise_zero():
    img = torch.rand(1, 8, 8, 3)
    node = mod.PSN_Denoise_Preview()
    (preview,) = node.run(image=img, denoise=0.0, seed=42)
    assert preview.shape == img.shape
    assert torch.allclose(preview, img, atol=1e-6)


# ---------------------------------------------------------------------------
# 5. PSN_Denoise_Preview: denoise=1 changes the image (noise injected)
# ---------------------------------------------------------------------------
def test_preview_denoise_one():
    img = torch.rand(1, 8, 8, 3)
    node = mod.PSN_Denoise_Preview()
    (preview,) = node.run(image=img, denoise=1.0, seed=42)
    assert preview.shape == img.shape
    # must differ from original
    assert not torch.allclose(preview, img, atol=1e-4)
    # must be in [0, 1]
    assert preview.min().item() >= 0.0
    assert preview.max().item() <= 1.0


# ---------------------------------------------------------------------------
# 6. PSN_Actual_Denoise: denoise=0 returns the original latent unchanged
# ---------------------------------------------------------------------------
def test_actual_denoise_zero():
    img = torch.rand(1, 8, 8, 3)
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    (out,) = node.run(
        image=img, denoise=0.0, model=None, positive=None, negative=None,
        latent=lat, seed=0, num_steps=10,
    )
    assert "samples" in out
    assert out["samples"].shape == lat["samples"].shape
    assert torch.allclose(out["samples"], lat["samples"], atol=1e-5)


# ---------------------------------------------------------------------------
# 7. PSN_Actual_Denoise: denoise=1 changes the latent (noise injected)
# ---------------------------------------------------------------------------
def test_actual_denoise_one():
    img = torch.rand(1, 8, 8, 3)
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    (out,) = node.run(
        image=img, denoise=1.0, model=None, positive=None, negative=None,
        latent=lat, seed=0, num_steps=10,
    )
    assert out["samples"].shape == lat["samples"].shape
    assert not torch.allclose(out["samples"], lat["samples"], atol=1e-4)


# ---------------------------------------------------------------------------
# 8. PSN_Actual_Denoise: denoise=0.5 is a blend between 0 and 1 results
# ---------------------------------------------------------------------------
def test_actual_denoise_blend():
    img = torch.rand(1, 8, 8, 3)
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    (out0,) = node.run(image=img, denoise=0.0, model=None, positive=None,
                       negative=None, latent=lat, seed=0, num_steps=10)
    (out1,) = node.run(image=img, denoise=1.0, model=None, positive=None,
                       negative=None, latent=lat, seed=0, num_steps=10)
    (out05,) = node.run(image=img, denoise=0.5, model=None, positive=None,
                        negative=None, latent=lat, seed=0, num_steps=10)
    # out05 should be closer to out0 than out1 is (denoise=0.5 < 1.0)
    dist05_0 = (out05["samples"] - out0["samples"]).abs().mean().item()
    dist1_0 = (out1["samples"] - out0["samples"]).abs().mean().item()
    assert dist05_0 < dist1_0
    # out05 should be different from both out0 and out1
    assert not torch.allclose(out05["samples"], out0["samples"], atol=1e-4)
    assert not torch.allclose(out05["samples"], out1["samples"], atol=1e-4)


# ---------------------------------------------------------------------------
# 9. bad input: denoise out of range raises ValueError
# ---------------------------------------------------------------------------
def test_bad_denoise():
    img = torch.rand(1, 4, 4, 3)
    lat = {"samples": torch.randn(1, 4, 4, 4)}
    node = mod.PSN_Actual_Denoise()
    try:
        node.run(image=img, denoise=1.5, model=None, positive=None,
                 negative=None, latent=lat)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        node.run(image=img, denoise=-0.1, model=None, positive=None,
                 negative=None, latent=lat)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 10. bad input: wrong image shape raises ValueError
# ---------------------------------------------------------------------------
def test_bad_image_shape():
    bad_img = torch.rand(1, 8, 3)  # 3-D, not 4-D
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    try:
        node.run(image=bad_img, denoise=0.5, model=None, positive=None,
                 negative=None, latent=lat)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 11. bad input: non-tensor image raises TypeError
# ---------------------------------------------------------------------------
def test_bad_image_type():
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    try:
        node.run(image="not a tensor", denoise=0.5, model=None, positive=None,
                 negative=None, latent=lat)
        assert False, "expected TypeError"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# 12. inputs are not modified in place
# ---------------------------------------------------------------------------
def test_no_inplace():
    img = torch.rand(1, 8, 8, 3)
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    img_orig = img.clone()
    lat_orig = lat["samples"].clone()
    node = mod.PSN_Actual_Denoise()
    node.run(image=img, denoise=0.5, model=None, positive=None,
             negative=None, latent=lat, seed=0, num_steps=10)
    assert torch.equal(img, img_orig)
    assert torch.equal(lat["samples"], lat_orig)


# ---------------------------------------------------------------------------
# 13. preview: non-finite image raises ValueError
# ---------------------------------------------------------------------------
def test_preview_nonfinite():
    img = torch.rand(1, 4, 4, 3)
    img[0, 0, 0, 0] = float("nan")
    node = mod.PSN_Denoise_Preview()
    try:
        node.run(image=img, denoise=0.5)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 14. deterministic: same seed gives same output
# ---------------------------------------------------------------------------
def test_deterministic():
    img = torch.rand(1, 8, 8, 3)
    lat = {"samples": torch.randn(1, 4, 8, 8)}
    node = mod.PSN_Actual_Denoise()
    (a,) = node.run(image=img, denoise=0.5, model=None, positive=None,
                    negative=None, latent=lat, seed=123, num_steps=10)
    (b,) = node.run(image=img, denoise=0.5, model=None, positive=None,
                    negative=None, latent=lat, seed=123, num_steps=10)
    assert torch.allclose(a["samples"], b["samples"], atol=1e-7)


# ---------------------------------------------------------------------------
# run all
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_mappings()
    test_node_interface()
    test_sigma_schedule()
    test_preview_denoise_zero()
    test_preview_denoise_one()
    test_actual_denoise_zero()
    test_actual_denoise_one()
    test_actual_denoise_blend()
    test_bad_denoise()
    test_bad_image_shape()
    test_bad_image_type()
    test_no_inplace()
    test_preview_nonfinite()
    test_deterministic()
    print("ok")
