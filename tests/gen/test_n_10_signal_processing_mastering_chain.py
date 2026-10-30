"""Tests for PSN_Sig_Process mastering chain node."""

import json
import math

import pytest

from psn_nodes.gen.n_10_signal_processing_mastering_chain import (
    PSN_Sig_Process,
    _parse_audio,
    _denoise,
    _apply_eq,
    _normalize,
)


def _make_audio(samples, sample_rate=44100):
    return json.dumps({"samples": samples, "sample_rate": sample_rate})


def test_normalize_brings_peak_to_one():
    """Normalization should scale the peak to exactly 1.0 (0 dBFS)."""
    samples = [0.5, -0.5, 0.25, -0.25, 0.75]
    node = PSN_Sig_Process()
    result = node.run(_make_audio(samples), denoise=False, eq_low=0.0, eq_high=0.0, normalize=True)
    data = json.loads(result[0])
    peak = max(abs(s) for s in data["samples"])
    assert abs(peak - 1.0) < 1e-9


def test_normalize_zero_audio():
    """All-zero audio should remain all-zero after normalization."""
    samples = [0.0, 0.0, 0.0]
    node = PSN_Sig_Process()
    result = node.run(_make_audio(samples), denoise=False, eq_low=0.0, eq_high=0.0, normalize=True)
    data = json.loads(result[0])
    assert all(s == 0.0 for s in data["samples"])


def test_eq_gain_applied():
    """EQ gains in dB should scale samples correctly."""
    samples = [1.0, 1.0, 1.0, 1.0]
    # +6 dB low, 0 dB high
    node = PSN_Sig_Process()
    result = node.run(_make_audio(samples), denoise=False, eq_low=6.0, eq_high=0.0, normalize=False)
    data = json.loads(result[0])
    # First half (low band) should be scaled by 10^(6/20) ≈ 1.995
    expected_low = 1.0 * (10.0 ** (6.0 / 20.0))
    assert abs(data["samples"][0] - expected_low) < 1e-9
    # Second half (high band) unchanged
    assert abs(data["samples"][2] - 1.0) < 1e-9


def test_denoise_reduces_noise():
    """Denoising (moving average) should reduce variance of a noisy signal."""
    # Create a signal with a constant value plus alternating noise
    base = 0.5
    noisy = [base + (0.1 if i % 2 == 0 else -0.1) for i in range(20)]
    denoised = _denoise(noisy, window=5)
    # Variance should decrease
    mean_orig = sum(noisy) / len(noisy)
    mean_den = sum(denoised) / len(denoised)
    var_orig = sum((x - mean_orig) ** 2 for x in noisy) / len(noisy)
    var_den = sum((x - mean_den) ** 2 for x in denoised) / len(denoised)
    assert var_den < var_orig


def test_bad_audio_json_raises():
    """Invalid JSON should raise ValueError."""
    node = PSN_Sig_Process()
    with pytest.raises(ValueError):
        node.run("not valid json", denoise=False, eq_low=0.0, eq_high=0.0, normalize=True)


def test_bad_audio_type_raises():
    """Non-string audio input should raise ValueError."""
    node = PSN_Sig_Process()
    with pytest.raises(ValueError):
        node.run(12345, denoise=False, eq_low=0.0, eq_high=0.0, normalize=True)


def test_empty_samples():
    """Empty sample list should pass through unchanged."""
    node = PSN_Sig_Process()
    result = node.run(_make_audio([]), denoise=True, eq_low=3.0, eq_high=-3.0, normalize=True)
    data = json.loads(result[0])
    assert data["samples"] == []


def test_parse_audio_list_format():
    """Audio as a plain JSON list should be parsed correctly."""
    samples, sr = _parse_audio("[1.0, 2.0, 3.0]")
    assert samples == [1.0, 2.0, 3.0]
    assert sr == 44100


def test_parse_audio_non_numeric_sample():
    """Non-numeric sample in list should raise ValueError."""
    with pytest.raises(ValueError):
        _parse_audio('["a", 1.0]')


def test_full_chain_order():
    """Full chain: denoise -> EQ -> normalize should produce peak 1.0."""
    samples = [0.1, -0.1, 0.2, -0.2, 0.3, -0.3]
    node = PSN_Sig_Process()
    result = node.run(_make_audio(samples), denoise=True, eq_low=2.0, eq_high=-2.0, normalize=True)
    data = json.loads(result[0])
    peak = max(abs(s) for s in data["samples"])
    assert abs(peak - 1.0) < 1e-9
