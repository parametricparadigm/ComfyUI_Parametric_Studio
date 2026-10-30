"""Tests for PSN_Resolution_Preset node."""

import pytest
from psn_nodes.gen.psn_resolution_preset import (
    PSN_Resolution_Preset,
    _compute_dimensions,
    _round_to_multiple,
    _clamp,
    MODEL_CONSTRAINTS,
    ASPECT_VALUES,
)


def test_psn_resolution_preset_square_1to1():
    """1:1 aspect ratio with 1024x1024 should stay 1024x1024."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "1:1", "SDXL")
    assert w == 1024
    assert h == 1024
    assert latent == 128
    assert w % 8 == 0
    assert h % 8 == 0


def test_psn_resolution_preset_wide_16to9():
    """16:9 aspect ratio with base 1024 should give 1024x576 (rounded to 8)."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "16:9", "SDXL")
    # base = max(1024,1024) = 1024, ar_w>=ar_h so target_w=1024, target_h=round(1024*9/16)=576
    assert w == 1024
    assert h == 576
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 72


def test_psn_resolution_preset_tall_9to16():
    """9:16 aspect ratio with base 1024 should give 576x1024."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "9:16", "SDXL")
    # ar_w < ar_h so target_h=1024, target_w=round(1024*9/16)=576
    assert w == 576
    assert h == 1024
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 72


def test_psn_resolution_preset_custom_preserves_dimensions():
    """Custom aspect ratio should use provided width/height directly."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(768, 512, "custom", "SDXL")
    assert w == 768
    assert h == 512
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 64


def test_psn_resolution_preset_clamps_to_model_max():
    """Dimensions exceeding model max should be clamped."""
    node = PSN_Resolution_Preset()
    # Wan max is 1024, so 2048 should be clamped to 1024
    w, h, latent = node.run(2048, 2048, "1:1", "Wan")
    assert w == 1024
    assert h == 1024
    assert w % 8 == 0
    assert h % 8 == 0


def test_psn_resolution_preset_clamps_to_model_min():
    """Dimensions below model min should be clamped up."""
    node = PSN_Resolution_Preset()
    # SDXL min is 256, so 16 should be clamped to 256
    w, h, latent = node.run(16, 16, "1:1", "SDXL")
    assert w == 256
    assert h == 256
    assert w % 8 == 0
    assert h % 8 == 0


def test_psn_resolution_preset_rounds_to_multiple_of_8():
    """Non-multiple-of-8 dimensions should be rounded to nearest multiple of 8."""
    node = PSN_Resolution_Preset()
    # 1000 is not a multiple of 8; round(1000/8)=125, 125*8=1000. Actually 1000/8=125 exactly.
    # Try 1001: round(1001/8)=round(125.125)=125, 125*8=1000
    w, h, latent = node.run(1001, 1001, "custom", "Custom")
    assert w % 8 == 0
    assert h % 8 == 0
    assert w == 1000
    assert h == 1000


def test_psn_resolution_preset_bad_model_type():
    """Unknown model type should return zeros."""
    w, h, latent, reason = _compute_dimensions(1024, 1024, "1:1", "UnknownModel")
    assert w == 0
    assert h == 0
    assert latent == 0
    assert "unknown model type" in reason


def test_psn_resolution_preset_bad_aspect_ratio():
    """Unknown aspect ratio should return zeros."""
    w, h, latent, reason = _compute_dimensions(1024, 1024, "7:5", "SDXL")
    assert w == 0
    assert h == 0
    assert latent == 0
    assert "unknown aspect ratio" in reason


def test_psn_resolution_preset_4to3_aspect():
    """4:3 aspect ratio with base 1024 should give 1024x768."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "4:3", "SDXL")
    # ar_w=4 >= ar_h=3, target_w=1024, target_h=round(1024*3/4)=768
    assert w == 1024
    assert h == 768
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 96


def test_psn_resolution_preset_3to4_aspect():
    """3:4 aspect ratio with base 1024 should give 768x1024."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "3:4", "SDXL")
    # ar_w=3 < ar_h=4, target_h=1024, target_w=round(1024*3/4)=768
    assert w == 768
    assert h == 1024
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 96


def test_psn_resolution_preset_flux_model():
    """Flux model should work with standard dimensions."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1024, 1024, "1:1", "Flux")
    assert w == 1024
    assert h == 1024
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 128


def test_psn_resolution_preset_custom_model_wider_range():
    """Custom model allows wider range (8 to 4096)."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(4096, 4096, "1:1", "Custom")
    assert w == 4096
    assert h == 4096
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 512


def test_psn_resolution_preset_non_square_custom():
    """Custom with non-square dimensions should preserve them if valid."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(1280, 720, "custom", "SDXL")
    assert w == 1280
    assert h == 720
    assert w % 8 == 0
    assert h % 8 == 0
    assert latent == 90


def test_psn_resolution_preset_very_small_custom():
    """Very small custom dimensions should be clamped to model min."""
    node = PSN_Resolution_Preset()
    w, h, latent = node.run(8, 8, "custom", "SDXL")
    # SDXL min is 256
    assert w == 256
    assert h == 256
    assert w % 8 == 0
    assert h % 8 == 0


def test_psn_resolution_preset_aspect_with_different_base():
    """Aspect ratio uses max(width, height) as base."""
    node = PSN_Resolution_Preset()
    # width=512, height=1024, aspect 16:9
    # base = max(512, 1024) = 1024
    # ar_w=16 >= ar_h=9, target_w=1024, target_h=round(1024*9/16)=576
    w, h, latent = node.run(512, 1024, "16:9", "SDXL")
    assert w == 1024
    assert h == 576
    assert w % 8 == 0
    assert h % 8 == 0
