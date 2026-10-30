"""Tests for PSN_LatentDiff node."""

import pytest
from psn_nodes.gen.psn_latent_diff import PSN_LatentDiff, _parse_latent_json, _compute_mse, _compute_max_diff


class TestPSNLatentDiff:
    """Tests for the PSN_LatentDiff node and its helper functions."""

    def test_mse_known_values(self):
        """Verify MSE calculation with known tensors."""
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert _compute_mse(a, b) == 0.0

    def test_mse_nonzero(self):
        """Verify MSE with non-zero differences."""
        a = [1.0, 2.0, 3.0]
        b = [2.0, 2.0, 3.0]
        # MSE = ((1-2)^2 + (2-2)^2 + (3-3)^2) / 3 = 1/3
        expected = 1.0 / 3.0
        assert abs(_compute_mse(a, b) - expected) < 1e-9

    def test_max_diff_known(self):
        """Verify Max Absolute Difference with known values."""
        a = [1.0, 5.0, 3.0]
        b = [2.0, 5.0, 1.0]
        # diffs: 1, 0, 2 -> max = 2
        assert _compute_max_diff(a, b) == 2.0

    def test_empty_latents(self):
        """Test with empty latent lists."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("[]", "[]")
        assert mse == 0.0
        assert max_diff == 0.0
        assert "empty" in report.lower()

    def test_length_mismatch(self):
        """Test with mismatched latent lengths."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("[1.0, 2.0]", "[1.0]")
        assert mse == 0.0
        assert max_diff == 0.0
        assert "Length mismatch" in report

    def test_invalid_json(self):
        """Test with invalid JSON input."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("not json", "[1.0]")
        assert mse == 0.0
        assert max_diff == 0.0
        assert "Error" in report

    def test_non_numeric_items(self):
        """Test with non-numeric items in latent JSON."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("[1.0, \"two\"]", "[1.0, 2.0]")
        assert mse == 0.0
        assert max_diff == 0.0
        assert "Error" in report

    def test_nan_in_latent(self):
        """Test with NaN in latent JSON."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("[1.0, NaN]", "[1.0, 2.0]")
        assert mse == 0.0
        assert max_diff == 0.0
        assert "Error" in report

    def test_parse_latent_json_valid(self):
        """Test _parse_latent_json with valid input."""
        result = _parse_latent_json("[1.0, 2.0, 3.0]")
        assert result == [1.0, 2.0, 3.0]

    def test_parse_latent_json_not_list(self):
        """Test _parse_latent_json with non-list JSON."""
        with pytest.raises(ValueError):
            _parse_latent_json("123")

    def test_parse_latent_json_bool_rejected(self):
        """Test _parse_latent_json rejects booleans."""
        with pytest.raises(ValueError):
            _parse_latent_json("[true, 1.0]")

    def test_node_returns_correct_types(self):
        """Test that node returns correct types."""
        node = PSN_LatentDiff()
        mse, max_diff, report = node.run("[1.0, 2.0]", "[1.0, 3.0]")
        assert isinstance(mse, float)
        assert isinstance(max_diff, float)
        assert isinstance(report, str)
        # MSE = ((1-1)^2 + (2-3)^2)/2 = 0.5
        assert abs(mse - 0.5) < 1e-9
        assert max_diff == 1.0
