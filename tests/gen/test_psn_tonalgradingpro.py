"""Tests for PSN_TonalGradingPro (pure-logic tonal grading)."""

import math

from psn_nodes.gen.psn_tonalgradingpro import (
    PSN_TonalGradingPro,
    _apply_tonal,
    _parse_curves,
    _validate_scalar,
)


def _node():
    return PSN_TonalGradingPro()


def test_exposure_increases_mean_pixel_value():
    """+1.0 exposure should roughly double a mid-gray pixel (2^1 = 2x)."""
    node = _node()
    # Mid-gray 0.5 with +1.0 exposure -> 0.5 * 2 = 1.0 (clamped).
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=1.0, contrast=1.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("ok")
    # 0.5 * 2 = 1.0, clamped to 1.0.
    assert math.isclose(out_r, 1.0, abs_tol=1e-6)
    assert math.isclose(out_g, 1.0, abs_tol=1e-6)
    assert math.isclose(out_b, 1.0, abs_tol=1e-6)


def test_exposure_on_dark_pixel_doubles_value():
    """A dark pixel (0.25) with +1.0 exposure should become ~0.5."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.25, g=0.25, b=0.25,
        exposure=1.0, contrast=1.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("ok")
    assert math.isclose(out_r, 0.5, abs_tol=1e-6)


def test_brightness_adds_to_pixel():
    """Brightness +0.2 on 0.3 should yield 0.5."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.3, g=0.3, b=0.3,
        exposure=0.0, contrast=1.0, brightness=0.2, saturation=1.0,
    )
    assert report.startswith("ok")
    assert math.isclose(out_r, 0.5, abs_tol=1e-6)


def test_contrast_pivots_around_mid_gray():
    """Contrast 2.0 on 0.75 (above pivot 0.5) should push it higher."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.75, g=0.75, b=0.75,
        exposure=0.0, contrast=2.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("ok")
    # 0.5 + (0.75 - 0.5) * 2 = 0.5 + 0.5 = 1.0
    assert math.isclose(out_r, 1.0, abs_tol=1e-6)


def test_saturation_zero_gives_grayscale():
    """Saturation 0.0 should collapse RGB to luminance (gray)."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=1.0, g=0.0, b=0.0,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=0.0,
    )
    assert report.startswith("ok")
    # Luminance of pure red = 0.2126.
    expected = 0.2126
    assert math.isclose(out_r, expected, abs_tol=1e-6)
    assert math.isclose(out_g, expected, abs_tol=1e-6)
    assert math.isclose(out_b, expected, abs_tol=1e-6)


def test_curves_json_identity():
    """An identity curve (0->0, 1->1) should leave the value unchanged."""
    node = _node()
    curves = '[{"x":0,"y":0},{"x":1,"y":1}]'
    # Use list-of-points form.
    curves_json = '[[0,0],[1,1]]'
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=1.0,
        curves_json=curves_json,
    )
    assert report.startswith("ok")
    assert math.isclose(out_r, 0.5, abs_tol=1e-6)


def test_curves_json_inverts_channel():
    """An inverting curve (0->1, 1->0) should flip the value."""
    node = _node()
    curves_json = '[[0,1],[1,0]]'
    out_r, out_g, out_b, report = node.run(
        r=0.25, g=0.25, b=0.25,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=1.0,
        curves_json=curves_json,
    )
    assert report.startswith("ok")
    # 0.25 -> 1 - 0.25 = 0.75
    assert math.isclose(out_r, 0.75, abs_tol=1e-6)


def test_curves_json_per_channel_dict():
    """Per-channel dict form should apply different curves per channel."""
    node = _node()
    curves_json = '{"r": [[0,1],[1,0]], "g": [[0,0],[1,1]], "b": [[0,0],[1,1]]}'
    out_r, out_g, out_b, report = node.run(
        r=0.25, g=0.25, b=0.25,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=1.0,
        curves_json=curves_json,
    )
    assert report.startswith("ok")
    assert math.isclose(out_r, 0.75, abs_tol=1e-6)
    assert math.isclose(out_g, 0.25, abs_tol=1e-6)
    assert math.isclose(out_b, 0.25, abs_tol=1e-6)


def test_invalid_curves_json_returns_error():
    """Malformed JSON should produce an error report and zeroed output."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=1.0,
        curves_json="{not valid json",
    )
    assert report.startswith("error")
    assert out_r == 0.0 and out_g == 0.0 and out_b == 0.0


def test_curves_json_bad_point_shape():
    """A point that is not a 2-element list should be rejected."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=0.0, contrast=1.0, brightness=0.0, saturation=1.0,
        curves_json='[[0,0,1],[1,1]]',
    )
    assert report.startswith("error")


def test_curves_json_out_of_range_clamped():
    """Curve points outside [0,1] should be clamped, not rejected."""
    ok, curves, reason = _parse_curves('[[0, 2], [1, -1]]')
    assert ok
    assert curves is not None
    # y values clamped to [0,1].
    assert curves["r"][0] == (0.0, 1.0)
    assert curves["r"][1] == (1.0, 0.0)


def test_invalid_scalar_exposure_returns_error():
    """A non-finite exposure should produce an error report."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=float("inf"), contrast=1.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("error")
    assert out_r == 0.0


def test_invalid_scalar_bool_rejected():
    """Booleans should be rejected as scalar inputs."""
    ok, val, why = _validate_scalar("exposure", True, -10.0, 10.0)
    assert not ok
    assert why.startswith("invalid")


def test_scalar_clamping():
    """Out-of-range scalars should be clamped to safe bounds."""
    ok, val, why = _validate_scalar("exposure", 999.0, -10.0, 10.0)
    assert ok
    assert val == 10.0
    ok, val, why = _validate_scalar("brightness", -5.0, -1.0, 1.0)
    assert ok
    assert val == -1.0


def test_extreme_exposure_clamped_not_nan():
    """Extreme exposure should clamp to [0,1] and never produce NaN."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=10.0, contrast=1.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("ok")
    assert math.isfinite(out_r)
    assert 0.0 <= out_r <= 1.0


def test_negative_exposure_darkens():
    """-1.0 exposure should halve a mid-gray pixel."""
    node = _node()
    out_r, out_g, out_b, report = node.run(
        r=0.5, g=0.5, b=0.5,
        exposure=-1.0, contrast=1.0, brightness=0.0, saturation=1.0,
    )
    assert report.startswith("ok")
    assert math.isclose(out_r, 0.25, abs_tol=1e-6)
