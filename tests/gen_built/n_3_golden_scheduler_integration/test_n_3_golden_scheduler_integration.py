"""Unit tests for n_3_golden_scheduler_integration.

Run with:  python3 -B test_n_3_golden_scheduler_integration.py
Must print 'ok' and exit 0.
"""

import torch

from n_3_golden_scheduler_integration import (
    PSN_GoldenScheduler,
    PSN_GoldenSampler,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    golden_sigmas,
    linear_sigmas,
    _sigma_preview_image,
)


# ---------------------------------------------------------------------------
# 1. golden_sigmas basic shape & values
# ---------------------------------------------------------------------------

def test_golden_sigmas_shape_and_bounds():
    steps = 20
    sig = golden_sigmas(steps, shift=3.0)
    assert sig.dim() == 1, "sigmas must be 1-D"
    assert sig.numel() == steps, f"expected {steps} sigmas, got {sig.numel()}"
    assert sig.dtype == torch.float32
    # descending
    for i in range(sig.numel() - 1):
        assert sig[i].item() >= sig[i + 1].item(), "sigmas must be non-increasing"
    # first is the largest, last is 0
    assert sig[0].item() > 0.0, "first sigma must be positive"
    assert sig[-1].item() == 0.0, "last sigma must be 0"
    # all in [0, 1] for shift >= 1
    assert (sig >= 0.0).all() and (sig <= 1.0).all(), "sigmas must be in [0,1]"


# ---------------------------------------------------------------------------
# 2. golden differs from linear
# ---------------------------------------------------------------------------

def test_golden_differs_from_linear():
    steps = 20
    g = golden_sigmas(steps, shift=3.0)
    l = linear_sigmas(steps)
    assert g.numel() == l.numel()
    # they must not be identical
    assert not torch.allclose(g, l, atol=1e-6), "golden must differ from linear"
    # but both end at 0
    assert g[-1].item() == 0.0 and l[-1].item() == 0.0


# ---------------------------------------------------------------------------
# 3. edge case: steps == 1
# ---------------------------------------------------------------------------

def test_golden_sigmas_single_step():
    sig = golden_sigmas(1, shift=3.0)
    assert sig.numel() == 1
    assert sig[0].item() == 0.0


# ---------------------------------------------------------------------------
# 4. bad input: steps < 1 raises
# ---------------------------------------------------------------------------

def test_golden_sigmas_bad_steps():
    try:
        golden_sigmas(0, shift=3.0)
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        golden_sigmas(-5, shift=3.0)
        assert False, "should have raised"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 5. bad input: shift <= 0 raises
# ---------------------------------------------------------------------------

def test_golden_sigmas_bad_shift():
    try:
        golden_sigmas(10, shift=0.0)
        assert False, "should have raised"
    except ValueError:
        pass
    try:
        golden_sigmas(10, shift=-1.0)
        assert False, "should have raised"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 6. preview image shape and range
# ---------------------------------------------------------------------------

def test_preview_image():
    sig = golden_sigmas(20, shift=3.0)
    img = _sigma_preview_image(sig)
    assert img.shape == (1, 64, 256, 3), f"unexpected shape {img.shape}"
    assert img.dtype == torch.float32
    assert (img >= 0.0).all() and (img <= 1.0).all(), "image must be in [0,1]"
    # at least one bright pixel (the curve)
    assert (img.max() > 0.5).item(), "preview must contain a bright curve pixel"


# ---------------------------------------------------------------------------
# 7. PSN_GoldenScheduler node run
# ---------------------------------------------------------------------------

class _FakeModel:
    def __init__(self, shift=3.0):
        self.shift = shift


def test_scheduler_node():
    node = PSN_GoldenScheduler()
    model = _FakeModel(shift=5.0)
    sigmas, preview = node.run(model, steps=16, shift=0.0)
    assert sigmas.numel() == 16
    assert sigmas[-1].item() == 0.0
    assert preview.shape == (1, 64, 256, 3)
    # manual shift override
    sigmas2, _ = node.run(model, steps=16, shift=1.0)
    # shift=1.0 gives linear schedule
    lin = linear_sigmas(16)
    assert torch.allclose(sigmas2, lin, atol=1e-5), "shift=1 should equal linear"


# ---------------------------------------------------------------------------
# 8. PSN_GoldenSampler with a stub model
# ---------------------------------------------------------------------------

def test_sampler_node():
    node = PSN_GoldenSampler()
    # stub model: v = -x  (drives x toward 0)
    def stub_model(x, sigma):
        return -x

    latent = {"samples": torch.ones(1, 4, 8, 8, dtype=torch.float32)}
    sigmas = golden_sigmas(10, shift=3.0)
    out = node.run(stub_model, None, None, latent, sigmas, sampler="euler")
    assert isinstance(out, tuple) and len(out) == 1
    out_latent = out[0]
    assert "samples" in out_latent
    x = out_latent["samples"]
    assert x.shape == (1, 4, 8, 8)
    assert torch.isfinite(x).all(), "output must be finite"
    # input must not be mutated
    assert latent["samples"].sum().item() == 1.0 * 4 * 8 * 8, "input latent must not be mutated"


# ---------------------------------------------------------------------------
# 9. sampler bad input: non-callable model
# ---------------------------------------------------------------------------

def test_sampler_bad_model():
    node = PSN_GoldenSampler()
    latent = {"samples": torch.ones(1, 4, 8, 8)}
    sigmas = golden_sigmas(5, shift=3.0)
    try:
        node.run("not a model", None, None, latent, sigmas)
        assert False, "should have raised"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
# 10. registration mappings
# ---------------------------------------------------------------------------

def test_node_mappings():
    assert "PSN_GoldenScheduler" in NODE_CLASS_MAPPINGS
    assert "PSN_GoldenSampler" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_GoldenScheduler"] is PSN_GoldenScheduler
    assert NODE_CLASS_MAPPINGS["PSN_GoldenSampler"] is PSN_GoldenSampler
    assert "PSN_GoldenScheduler" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_GoldenSampler" in NODE_DISPLAY_NAME_MAPPINGS
    # INPUT_TYPES must be a classmethod returning a dict
    it = PSN_GoldenScheduler.INPUT_TYPES()
    assert "required" in it and "model" in it["required"]
    it2 = PSN_GoldenSampler.INPUT_TYPES()
    assert "required" in it2 and "sigmas" in it2["required"]


if __name__ == "__main__":
    test_golden_sigmas_shape_and_bounds()
    test_golden_differs_from_linear()
    test_golden_sigmas_single_step()
    test_golden_sigmas_bad_steps()
    test_golden_sigmas_bad_shift()
    test_preview_image()
    test_scheduler_node()
    test_sampler_node()
    test_sampler_bad_model()
    test_node_mappings()
    print("ok")
