"""Tests for psn_nodes.gen.psn_scrna_normalize."""

import math
import pytest

from psn_nodes.gen.psn_scrna_normalize import (
    PSN_ScRNA_Normalize,
    _validate_matrix,
    _normalize_total,
    _apply_log1p,
    _extract_matrix,
)


def _make_adata(matrix):
    return {"X": matrix, "n_obs": len(matrix), "n_vars": len(matrix[0])}


class TestPSNScRNANormalize:
    def test_row_sums_match_target(self):
        """After normalization (no log1p), each row sum should equal target_sum."""
        matrix = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        adata = _make_adata(matrix)
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(adata, target_sum=10000.0, log1p=False)
        for row in result["X"]:
            assert math.isclose(sum(row), 10000.0, rel_tol=1e-9)

    def test_log1p_applied(self):
        """With log1p=True, values should be log1p of the normalized values."""
        matrix = [[10.0, 20.0]]
        adata = _make_adata(matrix)
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(adata, target_sum=10000.0, log1p=True)
        # Normalized: [10000/3, 20000/3]; log1p:
        expected = [math.log1p(10000.0 / 3.0), math.log1p(20000.0 / 3.0)]
        for got, exp in zip(result["X"][0], expected):
            assert math.isclose(got, exp, rel_tol=1e-9)

    def test_zero_row_stays_zero(self):
        """A row with all zeros should remain all zeros (no division by zero)."""
        matrix = [[0.0, 0.0], [1.0, 1.0]]
        adata = _make_adata(matrix)
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(adata, target_sum=10000.0, log1p=False)
        assert result["X"][0] == [0.0, 0.0]
        assert math.isclose(sum(result["X"][1]), 10000.0, rel_tol=1e-9)

    def test_plain_list_input(self):
        """Input can be a plain 2D list instead of an AnnData dict."""
        matrix = [[2.0, 2.0], [3.0, 1.0]]
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(matrix, target_sum=100.0, log1p=False)
        assert isinstance(result, dict)
        assert "X" in result
        for row in result["X"]:
            assert math.isclose(sum(row), 100.0, rel_tol=1e-9)

    def test_bad_input_negative_value(self):
        """Negative expression values should raise ValueError."""
        matrix = [[1.0, -1.0]]
        with pytest.raises(ValueError, match="negative"):
            PSN_ScRNA_Normalize().run(_make_adata(matrix), target_sum=10000.0, log1p=False)

    def test_bad_input_mismatched_row_lengths(self):
        """Rows with different lengths should raise ValueError."""
        matrix = [[1.0, 2.0], [3.0]]
        with pytest.raises(ValueError, match="length"):
            PSN_ScRNA_Normalize().run(_make_adata(matrix), target_sum=10000.0, log1p=False)

    def test_bad_input_none_adata(self):
        """None adata should raise ValueError."""
        with pytest.raises(ValueError, match="must not be None"):
            PSN_ScRNA_Normalize().run(None, target_sum=10000.0, log1p=False)

    def test_bad_input_non_numeric_element(self):
        """Non-numeric elements should raise ValueError."""
        matrix = [[1.0, "abc"]]
        with pytest.raises(ValueError, match="not a number"):
            PSN_ScRNA_Normalize().run(_make_adata(matrix), target_sum=10000.0, log1p=False)

    def test_target_sum_zero(self):
        """target_sum=0 should produce all-zero rows."""
        matrix = [[1.0, 2.0]]
        adata = _make_adata(matrix)
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(adata, target_sum=0.0, log1p=False)
        assert result["X"][0] == [0.0, 0.0]

    def test_single_cell_single_gene(self):
        """Edge case: 1x1 matrix."""
        matrix = [[5.0]]
        adata = _make_adata(matrix)
        node = PSN_ScRNA_Normalize()
        (result,) = node.run(adata, target_sum=20000.0, log1p=False)
        assert math.isclose(result["X"][0][0], 20000.0, rel_tol=1e-9)
