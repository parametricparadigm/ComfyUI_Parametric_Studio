"""
Tests for PSN_HDR_Color_Manager node.
"""

import json
import pytest

from psn_nodes.gen.n_6_color_managed_video_export_for_hdr_con import (
    PSN_HDR_Color_Manager,
    validate_icc_profile,
    validate_target_colorspace,
    compute_tone_mapping_params,
    build_color_config,
    ALLOWED_ICC_PROFILES,
    ALLOWED_TARGET_COLORSPACES,
    HDR_TONE_MAPPING_MODES,
)


def test_valid_srgb_to_srgb_no_hdr():
    """Test valid sRGB to sRGB conversion with HDR disabled."""
    node = PSN_HDR_Color_Manager()
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=False,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["icc_profile"] == "sRGB"
    assert config["target_colorspace"] == "sRGB"
    assert config["hdr_mode"] is False
    assert config["tone_mapping"]["enabled"] is False
    assert config["color_conversion"]["method"] == "matrix"


def test_valid_p3_to_rec2020_with_hdr():
    """Test valid Display P3 to Rec.2020 conversion with HDR enabled."""
    node = PSN_HDR_Color_Manager()
    valid, config_json, reason = node.run(
        icc_profile="Display P3",
        target_colorspace="Rec.2020",
        hdr_mode=True,
        tone_mapping_mode="ACES",
        exposure=1.5,
        gamma=2.2,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["icc_profile"] == "Display P3"
    assert config["target_colorspace"] == "Rec.2020"
    assert config["hdr_mode"] is True
    assert config["tone_mapping"]["enabled"] is True
    assert config["tone_mapping"]["mode"] == "ACES"
    assert config["tone_mapping"]["exposure"] == 1.5
    assert config["tone_mapping"]["gamma"] == 2.2
    assert config["color_conversion"]["method"] == "lut"


def test_invalid_icc_profile():
    """Test that an invalid ICC profile is rejected."""
    node = PSN_HDR_Color_Manager()
    valid, config_json, reason = node.run(
        icc_profile="InvalidProfile",
        target_colorspace="sRGB",
        hdr_mode=False,
    )
    assert valid is False
    assert "not in allow-list" in reason
    assert config_json == "{}"


def test_invalid_target_colorspace():
    """Test that an invalid target colorspace is rejected."""
    node = PSN_HDR_Color_Manager()
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="InvalidSpace",
        hdr_mode=False,
    )
    assert valid is False
    assert "not in allow-list" in reason
    assert config_json == "{}"


def test_exposure_clamping():
    """Test that exposure values are clamped to valid range."""
    node = PSN_HDR_Color_Manager()
    # Test high exposure clamping
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=True,
        exposure=100.0,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["tone_mapping"]["exposure"] == 10.0  # Clamped to max

    # Test low exposure clamping
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=True,
        exposure=0.01,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["tone_mapping"]["exposure"] == 0.1  # Clamped to min


def test_gamma_clamping():
    """Test that gamma values are clamped to valid range."""
    node = PSN_HDR_Color_Manager()
    # Test high gamma clamping
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=True,
        gamma=100.0,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["tone_mapping"]["gamma"] == 10.0  # Clamped to max

    # Test low gamma clamping
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=True,
        gamma=0.01,
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["tone_mapping"]["gamma"] == 0.1  # Clamped to min


def test_invalid_tone_mapping_mode_fallback():
    """Test that an invalid tone mapping mode falls back to Reinhard."""
    node = PSN_HDR_Color_Manager()
    valid, config_json, reason = node.run(
        icc_profile="sRGB",
        target_colorspace="sRGB",
        hdr_mode=True,
        tone_mapping_mode="InvalidMode",
    )
    assert valid is True
    config = json.loads(config_json)
    assert config["tone_mapping"]["mode"] == "Reinhard"  # Fallback to default


def test_validate_icc_profile_function():
    """Test the validate_icc_profile helper function directly."""
    # Valid profile
    is_valid, reason = validate_icc_profile("sRGB")
    assert is_valid is True
    assert reason == "Valid ICC profile"

    # Invalid profile
    is_valid, reason = validate_icc_profile("BadProfile")
    assert is_valid is False
    assert "not in allow-list" in reason

    # Non-string input
    is_valid, reason = validate_icc_profile(123)
    assert is_valid is False
    assert "must be a string" in reason


def test_validate_target_colorspace_function():
    """Test the validate_target_colorspace helper function directly."""
    # Valid colorspace
    is_valid, reason = validate_target_colorspace("Display P3")
    assert is_valid is True
    assert reason == "Valid target colorspace"

    # Invalid colorspace
    is_valid, reason = validate_target_colorspace("BadSpace")
    assert is_valid is False
    assert "not in allow-list" in reason

    # Non-string input
    is_valid, reason = validate_target_colorspace(None)
    assert is_valid is False
    assert "must be a string" in reason


def test_compute_tone_mapping_params_hdr_disabled():
    """Test tone mapping params when HDR is disabled."""
    params = compute_tone_mapping_params(
        hdr_mode=False,
        tone_mapping_mode="ACES",
        exposure=2.0,
        gamma=2.2,
    )
    assert params["enabled"] is False
    assert params["mode"] == "None"
    assert params["exposure"] == 1.0
    assert params["gamma"] == 1.0


def test_compute_tone_mapping_params_hdr_enabled():
    """Test tone mapping params when HDR is enabled."""
    params = compute_tone_mapping_params(
        hdr_mode=True,
        tone_mapping_mode="ACES",
        exposure=1.5,
        gamma=2.2,
    )
    assert params["enabled"] is True
    assert params["mode"] == "ACES"
    assert params["exposure"] == 1.5
    assert params["gamma"] == 2.2
    assert params["white_point"] == 1.0
    assert params["adapt_luminance"] == 0.18


def test_build_color_config_invalid_icc():
    """Test build_color_config with invalid ICC profile."""
    is_valid, config, reason = build_color_config(
        icc_profile="Invalid",
        target_colorspace="sRGB",
        hdr_mode=False,
        tone_mapping_mode="Reinhard",
        exposure=1.0,
        gamma=1.0,
    )
    assert is_valid is False
    assert config == {}
    assert "not in allow-list" in reason


def test_build_color_config_invalid_colorspace():
    """Test build_color_config with invalid target colorspace."""
    is_valid, config, reason = build_color_config(
        icc_profile="sRGB",
        target_colorspace="Invalid",
        hdr_mode=False,
        tone_mapping_mode="Reinhard",
        exposure=1.0,
        gamma=1.0,
    )
    assert is_valid is False
    assert config == {}
    assert "not in allow-list" in reason


def test_all_allowed_icc_profiles():
    """Test that all allowed ICC profiles are valid."""
    for profile in ALLOWED_ICC_PROFILES:
        is_valid, reason = validate_icc_profile(profile)
        assert is_valid is True, f"Profile {profile} should be valid"


def test_all_allowed_colorspaces():
    """Test that all allowed target colorspaces are valid."""
    for cs in ALLOWED_TARGET_COLORSPACES:
        is_valid, reason = validate_target_colorspace(cs)
        assert is_valid is True, f"Colorspace {cs} should be valid"


def test_all_tone_mapping_modes():
    """Test that all tone mapping modes are accepted."""
    for mode in HDR_TONE_MAPPING_MODES:
        params = compute_tone_mapping_params(
            hdr_mode=True,
            tone_mapping_mode=mode,
            exposure=1.0,
            gamma=1.0,
        )
        assert params["mode"] == mode
