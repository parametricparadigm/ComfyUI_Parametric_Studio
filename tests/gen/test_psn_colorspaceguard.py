"""Tests for PSN_ColorSpaceGuard pure-logic color-space validation node."""

import pytest

from psn_nodes.gen.psn_colorspaceguard import (
    PSN_ColorSpaceGuard,
    _srgb_to_linear,
    _linear_to_srgb,
    _infer_space_from_range,
    _conversion_ops,
    _validate_bit_depth,
    _validate_space,
)


def test_psn_guard_ok_when_space_matches():
    """sRGB range [0,1] expecting sRGB should report OK, no conversion."""
    node = PSN_ColorSpaceGuard()
    status, inferred, plan, needs = node.run(
        vmin=0.0, vmax=1.0, vmean=0.5,
        expected_space="sRGB", bit_depth=8, auto_fix=True,
    )
    assert status == "OK"
    assert inferred == "sRGB"
    assert needs is False
    assert plan == "no-op"


def test_psn_guard_conversion_srgb_to_linear():
    """sRGB range expecting Linear_sRGB should trigger conversion."""
    node = PSN_ColorSpaceGuard()
    status, inferred, plan, needs = node.run(
        vmin=0.0, vmax=1.0, vmean=0.5,
        expected_space="Linear_sRGB", bit_depth=16, auto_fix=True,
    )
    assert needs is True
    assert "Converted from sRGB to Linear_sRGB" in status
    assert "linearize_srgb" in plan


def test_psn_guard_no_conversion_when_auto_fix_false():
    """Mismatch with auto_fix=False should report MISMATCH, not convert."""
    node = PSN_ColorSpaceGuard()
    status, inferred, plan, needs = node.run(
        vmin=0.0, vmax=1.0, vmean=0.5,
        expected_space="Linear_sRGB", bit_depth=8, auto_fix=False,
    )
    assert needs is True
    assert status.startswith("MISMATCH")
    assert "auto_fix=False" in plan


def test_psn_guard_hdr_range_inferred_linear():
    """Values > 1.0 should be inferred as Linear_sRGB."""
    node = PSN_ColorSpaceGuard()
    status, inferred, plan, needs = node.run(
        vmin=0.0, vmax=3.5, vmean=1.2,
        expected_space="Linear_sRGB", bit_depth=32, auto_fix=True,
    )
    assert inferred == "Linear_sRGB"
    assert status == "OK"
    assert needs is False


def test_psn_guard_metadata_overrides_inference():
    """Explicit metadata should override range-based inference."""
    node = PSN_ColorSpaceGuard()
    status, inferred, plan, needs = node.run(
        vmin=0.0, vmax=1.0, vmean=0.5,
        expected_space="ACEScg", bit_depth=16, auto_fix=True,
        metadata="color_space=ACEScg",
    )
    assert inferred == "ACEScg"
    assert status == "OK"
    assert needs is False


def test_psn_guard_invalid_bit_depth_raises():
    """Bit depth not in allowed set should raise ValueError."""
    node = PSN_ColorSpaceGuard()
    with pytest.raises(ValueError, match="bit_depth"):
        node.run(
            vmin=0.0, vmax=1.0, vmean=0.5,
            expected_space="sRGB", bit_depth=12, auto_fix=True,
        )


def test_psn_guard_invalid_space_raises():
    """Invalid expected_space should raise ValueError."""
    node = PSN_ColorSpaceGuard()
    with pytest.raises(ValueError, match="expected_space"):
        node.run(
            vmin=0.0, vmax=1.0, vmean=0.5,
            expected_space="XYZ", bit_depth=8, auto_fix=True,
        )


def test_psn_guard_vmin_vmean_vmax_inconsistent_raises():
    """vmean outside [vmin, vmax] should raise ValueError."""
    node = PSN_ColorSpaceGuard()
    with pytest.raises(ValueError, match="vmin"):
        node.run(
            vmin=0.5, vmax=1.0, vmean=0.2,
            expected_space="sRGB", bit_depth=8, auto_fix=True,
        )


def test_psn_srgb_to_linear_roundtrip():
    """sRGB -> linear -> sRGB should approximately roundtrip."""
    for v in [0.0, 0.1, 0.5, 0.9, 1.0]:
        lin = _srgb_to_linear(v)
        back = _linear_to_srgb(lin)
        assert abs(back - v) < 1e-6, "roundtrip failed for v=%s" % v


def test_psn_conversion_ops_same_space():
    """Same space should yield no ops."""
    assert _conversion_ops("sRGB", "sRGB") == []


def test_psn_conversion_ops_srgb_to_aces():
    """sRGB to ACEScg should require linearize then encode."""
    ops = _conversion_ops("sRGB", "ACEScg")
    assert "linearize_srgb" in ops
    assert "encode_acescg" in ops


def test_psn_infer_negative_values_linear():
    """Negative values should be inferred as Linear_sRGB."""
    space, conf, reason = _infer_space_from_range(-0.1, 1.0, None)
    assert space == "Linear_sRGB"
    assert conf == "low"
