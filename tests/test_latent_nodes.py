import json, math
import pytest, torch
from psn_nodes import latent as L

def lat(*shape, seed=0, dtype=torch.float32): g = torch.Generator().manual_seed(seed); return {"samples": torch.randn(*shape, generator=g).to(dtype), "batch_index": [0]}
def run(node, *a, **k): return getattr(node, "run")(*a, **k)

def test_registry_and_input_validation():
    assert len(L.NODE_CLASS_MAPPINGS) == 12 and all(c.RETURN_TYPES and c.CATEGORY and c.FUNCTION == "run" for c in L.NODE_CLASS_MAPPINGS.values())
    with pytest.raises(ValueError, match="expected a LATENT"): run(L.PSN_LatentMath(), [1, 2], lat(1, 4, 8, 8), "add", 1.0)

def test_math_ops_values_strength_and_inputs_untouched():
    a, b = lat(2, 4, 8, 8, seed=1), lat(2, 4, 8, 8, seed=2); a0 = a["samples"].clone()
    assert torch.allclose(run(L.PSN_LatentMath(), a, b, "add", 1.0)[0]["samples"], a["samples"] + b["samples"])
    assert torch.allclose(run(L.PSN_LatentMath(), a, b, "subtract", 0.5)[0]["samples"], a["samples"] + 0.5 * (-b["samples"]))
    assert torch.allclose(run(L.PSN_LatentMath(), a, b, "lerp", 1.0)[0]["samples"], b["samples"]) and torch.equal(a["samples"], a0)
    assert torch.allclose(run(L.PSN_LatentMath(), a, b, "maximum", 1.0)[0]["samples"], torch.maximum(a["samples"], b["samples"]), atol=1e-6)
    assert torch.equal(run(L.PSN_LatentMath(), a, b, "add", 0.0)[0]["samples"], a["samples"])

def test_math_resizes_b_broadcasts_batch_and_rejects_channel_mismatch():
    a = lat(4, 4, 8, 8); out = run(L.PSN_LatentMath(), a, lat(1, 4, 4, 4), "add", 1.0)[0]["samples"]; assert out.shape == a["samples"].shape
    with pytest.raises(ValueError, match="channel mismatch"): run(L.PSN_LatentMath(), a, lat(1, 16, 8, 8), "add", 1.0)
    v = lat(1, 4, 3, 8, 8); assert run(L.PSN_LatentMath(), v, lat(1, 4, 5, 6, 6), "add", 1.0)[0]["samples"].shape == (1, 4, 3, 8, 8)    # 5-D video latent

def test_nan_results_are_refused():
    bad = lat(1, 4, 8, 8); bad["samples"][0, 0, 0, 0] = float("nan")
    with pytest.raises(ValueError, match="NaN"): run(L.PSN_LatentMath(), bad, lat(1, 4, 8, 8), "add", 1.0)

def test_slerp_endpoints_norm_and_parallel_fallback():
    a, b = lat(2, 4, 8, 8, seed=3), lat(2, 4, 8, 8, seed=4)
    assert torch.allclose(run(L.PSN_LatentSlerp(), a, b, 0.0)[0]["samples"], a["samples"], atol=1e-4) and torch.allclose(run(L.PSN_LatentSlerp(), a, b, 1.0)[0]["samples"], b["samples"], atol=1e-4)
    mid = run(L.PSN_LatentSlerp(), a, b, 0.5)[0]["samples"]; lin = 0.5 * (a["samples"] + b["samples"])
    assert mid.flatten(1).norm(dim=1).mean() > lin.flatten(1).norm(dim=1).mean()          # slerp keeps the magnitude that a straight blend loses
    same = run(L.PSN_LatentSlerp(), a, a, 0.3)[0]["samples"]; assert torch.isfinite(same).all() and torch.allclose(same, a["samples"], atol=1e-4)

def test_normalize_modes():
    x = {"samples": lat(2, 4, 16, 16, seed=5)["samples"] * 3 + 2}
    s = run(L.PSN_LatentNormalize(), x, "standardize", 1.0, 1.0)[0]["samples"]; assert abs(float(s.mean())) < 1e-3 and abs(float(s.std()) - 1) < 1e-2
    t = run(L.PSN_LatentNormalize(), x, "set_std", 0.5, 1.0)[0]["samples"]; assert abs(float(t.std()) - 0.5) < 2e-2
    ref = {"samples": lat(2, 4, 16, 16, seed=6)["samples"] * 0.5 - 1}; m = run(L.PSN_LatentNormalize(), x, "match_reference", 1.0, 1.0, ref)[0]["samples"]
    assert abs(float(m.mean()) - float(ref["samples"].mean())) < 0.05 and abs(float(m.std()) - float(ref["samples"].std())) < 0.05
    with pytest.raises(ValueError, match="reference"): run(L.PSN_LatentNormalize(), x, "match_reference", 1.0, 1.0)
    assert torch.allclose(run(L.PSN_LatentNormalize(), x, "standardize", 1.0, 0.0)[0]["samples"], x["samples"])

def test_batch_nodes():
    a = lat(3, 4, 8, 8); r = run(L.PSN_LatentBatchRepeat(), a, 2)[0]["samples"]; assert r.shape[0] == 6 and torch.equal(r[3:], a["samples"])
    sl = run(L.PSN_LatentBatchSlice(), a, -2, 5)[0]; assert sl["samples"].shape[0] == 2 and torch.equal(sl["samples"], a["samples"][1:]) and "batch_index" not in sl
    with pytest.raises(ValueError, match="empty slice"): run(L.PSN_LatentBatchSlice(), a, 9, 1)
    c = run(L.PSN_LatentBatchConcat(), a, lat(2, 4, 4, 4))[0]["samples"]; assert c.shape == (5, 4, 8, 8)

def test_noise_is_seeded_scaled_and_structured():
    x = {"samples": torch.zeros(1, 4, 32, 32)}; n1 = run(L.PSN_LatentNoiseInject(), x, 7, 1.0, 1, 1)[0]["samples"]; n2 = run(L.PSN_LatentNoiseInject(), x, 7, 1.0, 1, 1)[0]["samples"]; n3 = run(L.PSN_LatentNoiseInject(), x, 8, 1.0, 1, 1)[0]["samples"]
    assert torch.equal(n1, n2) and not torch.equal(n1, n3) and abs(float(n1.std()) - 1) < 0.15
    assert torch.equal(run(L.PSN_LatentNoiseInject(), x, 7, 0.0, 1, 1)[0]["samples"], x["samples"])
    blob = run(L.PSN_LatentNoiseInject(), x, 7, 1.0, 8, 2)[0]["samples"]; nb = lambda t: float((t[..., 1:] - t[..., :-1]).abs().mean())
    assert nb(blob) < 0.6 * nb(n1)                                                       # neighbouring cells correlate: smooth blobs, not white noise
    assert run(L.PSN_LatentNoiseInject(), {"samples": torch.zeros(1, 4, 3, 16, 16)}, 1, 0.5, 4, 1)[0]["samples"].shape == (1, 4, 3, 16, 16)

def test_tileable_removes_the_seam_of_smooth_content_and_keeps_the_centre():
    ramp = torch.linspace(0, 1, 32).view(1, 1, 1, 32).expand(1, 4, 32, 32).clone() + 0.01 * torch.randn(1, 4, 32, 32); ramp += torch.linspace(0, 1, 32).view(1, 1, 32, 1)
    x = {"samples": ramp}; seam = lambda t: float((t[..., 0] - t[..., -1]).abs().mean() + (t[..., 0, :] - t[..., -1, :]).abs().mean())
    y = run(L.PSN_LatentTileable(), x, "both", 0.5)[0]["samples"]; assert seam(ramp) > 1.5 and seam(y) < 0.25 * seam(ramp)          # a 0-to-1 ramp has a hard seam; blended it is continuous
    assert torch.equal(y[..., 8:24, 8:24], ramp[..., 8:24, 8:24]) and y.shape == ramp.shape                                         # the middle is untouched
    xo = run(L.PSN_LatentTileable(), x, "x", 0.5)[0]["samples"]; assert torch.equal(xo[..., 8:24, :], ramp[..., 8:24, :]) is False and torch.equal(xo[..., 4:28], ramp[..., 4:28]) is False
    assert float((xo[..., 0] - xo[..., -1]).abs().mean()) < 0.25 * float((ramp[..., 0] - ramp[..., -1]).abs().mean())

def test_temporal_smoothing_calms_flicker_and_anchors():
    base = torch.randn(1, 4, 1, 8, 8); frames = torch.cat([base + 0.8 * torch.randn(1, 4, 1, 8, 8) for _ in range(8)], 2); v = {"samples": frames}
    jitter = lambda t: float((t[:, :, 1:] - t[:, :, :-1]).abs().mean())
    sm = run(L.PSN_LatentTemporalSmooth(), v, 0.7, False)[0]["samples"]; assert jitter(sm) < 0.6 * jitter(frames) and torch.equal(sm[:, :, 0], frames[:, :, 0])
    assert torch.equal(run(L.PSN_LatentTemporalSmooth(), v, 0.0, False)[0]["samples"], frames)
    b = {"samples": torch.randn(5, 4, 8, 8)}; assert jitter(run(L.PSN_LatentTemporalSmooth(), b, 0.8, False)[0]["samples"].permute(1, 0, 2, 3).unsqueeze(0)) < jitter(b["samples"].permute(1, 0, 2, 3).unsqueeze(0))   # 4-D: batch is time
    anch = run(L.PSN_LatentTemporalSmooth(), v, 0.9, True)[0]["samples"]; assert torch.isfinite(anch).all() and anch.shape == frames.shape

def test_patch_inject_position_feather_and_clipping():
    a = {"samples": torch.zeros(1, 4, 16, 16)}; b = {"samples": torch.ones(1, 4, 6, 6)}
    p = run(L.PSN_LatentPatchInject(), a, b, 5, 5, 0, 1.0)[0]["samples"]; assert float(p[..., 5:11, 5:11].min()) == 1.0 and float(p.sum()) == 4 * 36
    f = run(L.PSN_LatentPatchInject(), a, b, 5, 5, 2, 1.0)[0]["samples"]; assert 0 < float(f[0, 0, 5, 5]) < 1.0 and float(f[0, 0, 8, 8]) == pytest.approx(1.0, abs=0.35)
    c = run(L.PSN_LatentPatchInject(), a, b, 13, 13, 0, 1.0)[0]["samples"]; assert float(c.sum()) == 4 * 9 and float(a["samples"].sum()) == 0
    assert float(run(L.PSN_LatentPatchInject(), a, b, 100, 100, 0, 1.0)[0]["samples"].sum()) == 0
    assert float(run(L.PSN_LatentPatchInject(), a, b, 5, 5, 0, 0.5)[0]["samples"][0, 0, 6, 6]) == 0.5

def test_direction_moves_along_positive_minus_negative():
    pos, neg = {"samples": torch.ones(3, 4, 8, 8) * 2}, {"samples": torch.ones(2, 4, 8, 8)}; t = {"samples": torch.zeros(2, 4, 8, 8)}
    out = run(L.PSN_LatentDirection(), t, pos, neg, 0.5)[0]["samples"]; assert torch.allclose(out, torch.full_like(out, 0.5)) and torch.equal(run(L.PSN_LatentDirection(), t, pos, neg, 0.0)[0]["samples"], t["samples"])

def test_stats_and_bad_value_guard():
    x = lat(1, 4, 8, 8); lt, summary, js = run(L.PSN_LatentStats(), x, True); d = json.loads(js)
    assert d["shape"] == [1, 4, 8, 8] and d["nan_or_inf"] == 0 and lt is x and "mean" in summary
    x["samples"][0, 0, 0, 0] = float("inf")
    with pytest.raises(ValueError, match="NaN/Inf"): run(L.PSN_LatentStats(), x, True)
    assert json.loads(run(L.PSN_LatentStats(), x, False)[2])["nan_or_inf"] == 1

def test_dtype_and_edge_cases_preserved():
    h = lat(1, 4, 8, 8, dtype=torch.float16)
    for out in (run(L.PSN_LatentMath(), h, h, "add", 0.5), run(L.PSN_LatentSlerp(), h, lat(1, 4, 8, 8, dtype=torch.float16), 0.5), run(L.PSN_LatentNoiseInject(), h, 1, 0.1, 2, 2), run(L.PSN_LatentTileable(), h, "both", 0.5), run(L.PSN_LatentNormalize(), h, "standardize", 1.0, 1.0)):
        assert out[0]["samples"].dtype == torch.float16
    one = lat(1, 4, 8, 8); assert torch.equal(run(L.PSN_LatentTemporalSmooth(), one, 0.5, True)[0]["samples"], one["samples"])
