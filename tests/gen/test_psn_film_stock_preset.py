"""Tests for PSN_Film_Stock_Preset."""

import math
import pytest
from psn_nodes.gen.psn_film_stock_preset import (
    PSN_Film_Stock_Preset,
    _apply_film_stock,
    _validate_lut,
    _build_identity_lut,
    _build_portra_400_lut,
    _build_hp5_plus_lut,
    _build_velvia_50_lut,
    FILM_STOCKS,
)


def test_portra_400_warm_shift_on_neutral_gray():
    """Verify that applying 'Kodak Portra 400' to a neutral gray image results in a slight warm shift (R > B)."""
    # Neutral gray: R=G=B=0.5
    image = [0.5, 0.5, 0.5]
    graded, lut = _apply_film_stock(image, "Kodak Portra 400", 1.0)
    assert len(graded) == 3
    r, g, b = graded
    # Warm shift means R > B
    assert r > b, f"Expected R > B for warm shift, got R={r}, B={b}"
    # Values should be in [0, 1]
    assert 0.0 <= r <= 1.0
    assert 0.0 <= g <= 1.0
    assert 0.0 <= b <= 1.0


def test_hp5_plus_monochrome():
    """Verify that applying 'Ilford HP5 Plus' produces monochrome output (R=G=B)."""
    image = [0.3, 0.5, 0.7]
    graded, lut = _apply_film_stock(image, "Ilford HP5 Plus", 1.0)
    r, g, b = graded
    # Monochrome means R ≈ G ≈ B
    assert abs(r - g) < 1e-6, f"Expected R ≈ G, got R={r}, G={g}"
    assert abs(g - b) < 1e-6, f"Expected G ≈ B, got G={g}, B={b}"


def test_velvia_50_high_saturation():
    """Verify that applying 'Fujifilm Velvia 50' increases saturation."""
    # A desaturated color
    image = [0.5, 0.5, 0.5]
    graded, lut = _apply_film_stock(image, "Fujifilm Velvia 50", 1.0)
    r, g, b = graded
    # Velvia should boost R and B, reduce G
    assert r >= 0.5, f"Expected R >= 0.5, got R={r}"
    assert b >= 0.5, f"Expected B >= 0.5, got B={b}"
    assert g <= 0.5, f"Expected G <= 0.5, got G={g}"


def test_intensity_zero_returns_original():
    """Verify that intensity=0 returns the original image unchanged."""
    image = [0.2, 0.4, 0.6]
    graded, lut = _apply_film_stock(image, "Kodak Portra 400", 0.0)
    assert graded == image, f"Expected original image, got {graded}"


def test_custom_lut_identity():
    """Verify that using an identity LUT with Custom returns the original image."""
    image = [0.1, 0.2, 0.3]
    identity_lut = _build_identity_lut()
    graded, lut = _apply_film_stock(image, "Custom", 1.0, custom_lut=identity_lut)
    # With identity LUT, output should be very close to input
    for i in range(3):
        assert abs(graded[i] - image[i]) < 1e-6, f"Expected identity, got {graded[i]} vs {image[i]}"


def test_custom_lut_required_when_custom_selected():
    """Verify that an error is raised when film_stock is 'Custom' but no custom_lut is provided."""
    image = [0.5, 0.5, 0.5]
    with pytest.raises(ValueError, match="custom_lut is required"):
        _apply_film_stock(image, "Custom", 1.0, custom_lut=None)


def test_invalid_film_stock_raises_error():
    """Verify that an unknown film stock name raises an error."""
    image = [0.5, 0.5, 0.5]
    with pytest.raises(ValueError, match="Unknown film stock"):
        _apply_film_stock(image, "NonExistent Stock", 1.0)


def test_invalid_image_length_raises_error():
    """Verify that an image with length not a multiple of 3 raises an error."""
    image = [0.5, 0.5]  # Length 2, not multiple of 3
    with pytest.raises(ValueError, match="multiple of 3"):
        _apply_film_stock(image, "Kodak Portra 400", 1.0)


def test_invalid_intensity_raises_error():
    """Verify that an intensity outside [0, 1] raises an error."""
    image = [0.5, 0.5, 0.5]
    with pytest.raises(ValueError, match="intensity must be between"):
        _apply_film_stock(image, "Kodak Portra 400", 1.5)


def test_invalid_image_values_raises_error():
    """Verify that image values outside [0, 1] raise an error."""
    image = [1.5, 0.5, 0.5]  # R > 1.0
    with pytest.raises(ValueError, match="image values must be in"):
        _apply_film_stock(image, "Kodak Portra 400", 1.0)


def test_invalid_custom_lut_structure_raises_error():
    """Verify that an invalid custom LUT structure raises an error."""
    image = [0.5, 0.5, 0.5]
    invalid_lut = [[1, 2, 3]]  # Not a proper 3D structure
    with pytest.raises(ValueError, match="custom_lut is invalid"):
        _apply_film_stock(image, "Custom", 1.0, custom_lut=invalid_lut)


def test_node_run_method():
    """Test the node's run method directly."""
    node = PSN_Film_Stock_Preset()
    image = [0.5, 0.5, 0.5]
    graded, lut = node.run(image, "Kodak Portra 400", 1.0)
    assert len(graded) == 3
    assert isinstance(lut, list)
    # Verify warm shift
    assert graded[0] > graded[2]


def test_node_run_with_custom_lut():
    """Test the node's run method with a custom LUT."""
    node = PSN_Film_Stock_Preset()
    image = [0.5, 0.5, 0.5]
    custom_lut = _build_portra_400_lut()
    graded, lut = node.run(image, "Custom", 1.0, custom_lut=custom_lut)
    assert len(graded) == 3
    assert lut == custom_lut


def test_all_preset_stocks_no_nans():
    """Smoke test: run on a small image with all 3 preset stocks, ensure no NaNs and output shape matches input."""
    image = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    for stock in ["Kodak Portra 400", "Ilford HP5 Plus", "Fujifilm Velvia 50"]:
        graded, lut = _apply_film_stock(image, stock, 1.0)
        assert len(graded) == len(image), f"Output length mismatch for {stock}"
        for val in graded:
            assert not math.isnan(val), f"NaN found in output for {stock}"
            assert 0.0 <= val <= 1.0, f"Value out of range for {stock}: {val}"


def test_validate_lut_function():
    """Test the _validate_lut function with valid and invalid LUTs."""
    valid_lut = _build_identity_lut()
    assert _validate_lut(valid_lut) is True
    
    invalid_lut = [[1, 2, 3]]
    assert _validate_lut(invalid_lut) is False
    
    empty_lut = []
    assert _validate_lut(empty_lut) is False
    
    lut_with_out_of_range = [[[0.0, 0.0, 0.0], [0.0, 0.0, 1.5]],
                              [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]]
    assert _validate_lut(lut_with_out_of_range) is False
