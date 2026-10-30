"""Tests for n_10_spectral_noise_injection.py.

Run with:  python3 -B test_n_10_spectral_noise_injection.py
Must print 'ok' and exit 0.
"""

import math

import torch

from n_10_spectral_noise_injection import (
    PSN_SpectralScheduler,
    PSN_SpectralNoise,
    PSN_SpectralSampler,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _sigma_schedule,
    _spectral_noise,
    _radial_freq_mask,
)


def _tiny_latent(B=1, C=4, H=8, W=8, val=0.5):
    return {"samples": torch.full((B, C, H, W), val, dtype=torch.float32)}


# ---------------------------------------------------------------------------
# 1. Module-level mappings exist and are consistent
# ---------------------------------------------------------------------------
def test_mappings():
    assert "PSN_SpectralScheduler" in NODE_CLASS_MAPPINGS
    assert "PSN_SpectralNoise" in NODE_CLASS_MAPPINGS
    assert "PSN_SpectralSampler" in NODE_CLASS_MAPPINGS
    for k in NODE_CLASS_MAPPINGS:
        assert k in NODE_DISPLAY_NAME_MAPPINGS
        assert isinstance(NODE_DISPLAY_NAME_MAPPINGS[k], str)
        assert NODE_CLASS_MAPPINGS[k].FUNCTION == "run"
        assert NODE_CLASS_MAPPINGS[k].CATEGORY.startswith("ParametricStudio/")
    for cls in NODE_CLASS_MAPPINGS.values():
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)


# ---------------------------------------------------------------------------
# 2. Scheduler: linear schedule has correct length, descending, ends at 0
# ---------------------------------------------------------------------------
def test_scheduler_linear():
    node = PSN_SpectralScheduler()
    sigmas, cfg = node.run(
        steps=10, schedule_type="linear", start_sigma=1.0, end_sigma=0.0,
        spectral_weight=1.0, cutoff_frac=0.5, noise_type="gaussian", seed=42,
    )
    assert isinstance(sigmas, torch.Tensor)
    assert sigmas.dim() == 1
    assert sigmas.numel() == 11
    assert sigmas[0].item() == 1.0
    assert sigmas[-1].item() == 0.0
    for i in range(sigmas.numel() - 1):
        assert sigmas[i].item() >= sigmas[i + 1].item()
    assert isinstance(cfg, dict)
    assert cfg["spectral_weight"] == 1.0
    assert cfg["cutoff_frac"] == 0.5
    assert cfg["seed"] == 42
    assert cfg["noise_type"] == "gaussian"


# ---------------------------------------------------------------------------
# 3. Scheduler: progressive schedule differs from linear
# ---------------------------------------------------------------------------
def test_scheduler_progressive_differs():
    node = PSN_SpectralScheduler()
    s_lin, _ = node.run(10, "linear", 1.0, 0.0, 1.0, 0.5, "gaussian", 0)
    s_prog, _ = node.run(10, "progressive", 1.0, 0.0, 1.0, 0.5, "gaussian", 0)
    assert s_lin.numel() == s_prog.numel() == 11
    assert not torch.allclose(s_lin, s_prog, atol=1e-6)
    assert s_prog[6].item() < s_lin[6].item()


# ---------------------------------------------------------------------------
# 4. Scheduler: bad input (steps=0) raises
# ---------------------------------------------------------------------------
def test_scheduler_bad_steps():
    node = PSN_SpectralScheduler()
    try:
        node.run(0, "linear", 1.0, 0.0, 1.0, 0.5, "gaussian", 0)
        assert False, "expected ValueError for steps=0"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 5. Spectral noise: shape preserved, deterministic with same seed
# ---------------------------------------------------------------------------
def test_spectral_noise_deterministic():
    cfg = {"spectral_weight": 1.0, "cutoff_frac": 0.5, "seed": 123, "noise_type": "gaussian"}
    shape = (1, 4, 8, 8)
    n1 = _spectral_noise(shape, cfg, torch.device("cpu"), torch.float32)
    n2 = _spectral_noise(shape, cfg, torch.device("cpu"), torch.float32)
    assert n1.shape == shape
    assert torch.allclose(n1, n2, atol=1e-6)
    cfg2 = dict(cfg, seed=456)
    n3 = _spectral_noise(shape, cfg2, torch.device("cpu"), torch.float32)
    assert not torch.allclose(n1, n3, atol=1e-4)


# ---------------------------------------------------------------------------
# 6. Spectral noise: high-frequency boost increases variance vs weight=0
# ---------------------------------------------------------------------------
def test_spectral_noise_weight_effect():
    shape = (1, 4, 16, 16)
    cfg_low = {"spectral_weight": 0.0, "cutoff_frac": 0.5, "seed": 7, "noise_type": "gaussian"}
    cfg_high = {"spectral_weight": 3.0, "cutoff_frac": 0.5, "seed": 7, "noise_type": "gaussian"}
    n_low = _spectral_noise(shape, cfg_low, torch.device("cpu"), torch.float32)
    n_high = _spectral_noise(shape, cfg_high, torch.device("cpu"), torch.float32)
    assert n_high.var().item() > n_low.var().item()


# ---------------------------------------------------------------------------
# 7. PSN_SpectralNoise node: output shape matches input, input not modified
# ---------------------------------------------------------------------------
def test_spectral_noise_node():
    node = PSN_SpectralNoise()
    lat = _tiny_latent()
    orig = lat["samples"].clone()
    cfg = {"spectral_weight": 1.0, "cutoff_frac": 0.5, "seed": 1, "noise_type": "gaussian"}
    (out_lat,) = node.run(lat, cfg, noise_scale=0.5)
    assert out_lat["samples"].shape == lat["samples"].shape
    assert torch.allclose(lat["samples"], orig, atol=1e-6)
    assert not torch.allclose(out_lat["samples"], orig, atol=1e-4)


# ---------------------------------------------------------------------------
# 8. PSN_SpectralNoise: bad latent (not a dict) raises
# ---------------------------------------------------------------------------
def test_spectral_noise_bad_latent():
    node = PSN_SpectralNoise()
    cfg = {"spectral_weight": 1.0, "cutoff_frac": 0.5, "seed": 1, "noise_type": "gaussian"}
    try:
        node.run("not a latent", cfg, noise_scale=1.0)
        assert False, "expected ValueError for bad latent"
    except ValueError:
        pass
    try:
        node.run({"samples": torch.randn(2, 8, 8)}, cfg, noise_scale=1.0)
        assert False, "expected ValueError for 3-D latent"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 9. PSN_SpectralSampler: end-to-end with trivial denoiser, output valid
# ---------------------------------------------------------------------------
def test_spectral_sampler_e2e():
    sched = PSN_SpectralScheduler()
    sigmas, cfg = sched.run(5, "linear", 1.0, 0.0, 1.0, 0.5, "gaussian", 99)
    lat = _tiny_latent(B=1, C=4, H=8, W=8, val=0.3)
    sampler = PSN_SpectralSampler()
    (out_lat,) = sampler.run(lat, sigmas, cfg, sampler="euler", noise_scale=1.0)
    assert out_lat["samples"].shape == lat["samples"].shape
    assert torch.isfinite(out_lat["samples"]).all()
    assert torch.allclose(lat["samples"], torch.full((1, 4, 8, 8), 0.3), atol=1e-6)


# ---------------------------------------------------------------------------
# 10. PSN_SpectralSampler: with a custom model callable
# ---------------------------------------------------------------------------
def test_spectral_sampler_custom_model():
    sched = PSN_SpectralScheduler()
    sigmas, cfg = sched.run(3, "linear", 1.0, 0.0, 1.0, 0.5, "gaussian", 5)
    lat = _tiny_latent(B=1, C=2, H=4, W=4, val=0.5)

    call_count = [0]

    def fake_model(latent_dict, sigma):
        call_count[0] += 1
        x = latent_dict["samples"] - sigma * 0.1
        return {"samples": x}

    sampler = PSN_SpectralSampler()
    (out_lat,) = sampler.run(lat, sigmas, cfg, sampler="euler", noise_scale=0.5, model=fake_model)
    assert call_count[0] == 3
    assert out_lat["samples"].shape == lat["samples"].shape
    assert torch.isfinite(out_lat["samples"]).all()


# ---------------------------------------------------------------------------
# 11. PSN_SpectralSampler: bad sigmas (too short) raises
# ---------------------------------------------------------------------------
def test_spectral_sampler_bad_sigmas():
    sampler = PSN_SpectralSampler()
    lat = _tiny_latent()
    cfg = {"spectral_weight": 1.0, "cutoff_frac": 0.5, "seed": 1, "noise_type": "gaussian"}
    try:
        sampler.run(lat, torch.tensor([1.0]), cfg, sampler="euler", noise_scale=1.0)
        assert False, "expected ValueError for 1-element sigmas"
    except ValueError:
        pass
    try:
        sampler.run(lat, [1.0, 0.5, 0.0], cfg, sampler="euler", noise_scale=1.0)
        assert False, "expected ValueError for list sigmas"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 12. Radial freq mask: DC is 1, corners are 0 (for cutoff=0.5)
# ---------------------------------------------------------------------------
def test_radial_mask():
    H, W = 8, 8
    mask = _radial_freq_mask(H, W, 0.5, torch.device("cpu"), torch.float32)
    assert mask.shape == (H, W)
    assert mask[0, 0].item() == 1.0
    assert mask[H // 2, W // 2].item() == 0.0
    assert mask.min().item() >= 0.0
    assert mask.max().item() <= 1.0


# ---------------------------------------------------------------------------
# 13. Scheduler: karras and exponential produce valid descending schedules
# ---------------------------------------------------------------------------
def test_scheduler_karras_exponential():
    node = PSN_SpectralScheduler()
    for st in ("karras", "exponential"):
        sigmas, _ = node.run(8, st, 1.0, 0.0, 1.0, 0.5, "gaussian", 0)
        assert sigmas.numel() == 9
        assert sigmas[0].item() > 0.99
        assert sigmas[-1].item() == 0.0
        for i in range(sigmas.numel() - 1):
            assert sigmas[i].item() >= sigmas[i + 1].item() - 1e-6


# ---------------------------------------------------------------------------
# 14. Scheduler: bad schedule_type raises
# ---------------------------------------------------------------------------
def test_scheduler_bad_type():
    node = PSN_SpectralScheduler()
    try:
        node.run(5, "bogus", 1.0, 0.0, 1.0, 0.5, "gaussian", 0)
        assert False, "expected ValueError for bad schedule_type"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# 15. Scheduler: bad cutoff_frac raises
# ---------------------------------------------------------------------------
def test_scheduler_bad_cutoff():
    node = PSN_SpectralScheduler()
    try:
        node.run(5, "linear", 1.0, 0.0, 1.0, 1.5, "gaussian", 0)
        assert False, "expected ValueError for cutoff_frac > 1"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_mappings()
    test_scheduler_linear()
    test_scheduler_progressive_differs()
    test_scheduler_bad_steps()
    test_spectral_noise_deterministic()
    test_spectral_noise_weight_effect()
    test_spectral_noise_node()
    test_spectral_noise_bad_latent()
    test_spectral_sampler_e2e()
    test_spectral_sampler_custom_model()
    test_spectral_sampler_bad_sigmas()
    test_radial_mask()
    test_scheduler_karras_exponential()
    test_scheduler_bad_type()
    test_scheduler_bad_cutoff()
    print("ok")
