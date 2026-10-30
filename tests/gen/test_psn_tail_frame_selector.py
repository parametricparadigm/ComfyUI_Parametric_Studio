"""Tests for PSN_Tail_Frame_Selector node."""

import pytest
from psn_nodes.gen.psn_tail_frame_selector import PSN_Tail_Frame_Selector


class TestPSNTailFrameSelector:
    """Test suite for PSN_Tail_Frame_Selector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = PSN_Tail_Frame_Selector()

    def test_basic_selection_highest_score(self):
        """Test that the node selects the candidate with the highest score."""
        scores = [0.5, 0.9, 0.7, 0.3]
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 1
        assert score == 0.9
        assert "Selected candidate 1" in reason

    def test_single_candidate(self):
        """Test with only one candidate frame."""
        scores = [0.85]
        selected_index, score, reason = self.node.run(scores, "PSNR")
        assert selected_index == 0
        assert score == 0.85
        assert "Selected candidate 0" in reason

    def test_all_equal_scores(self):
        """Test when all candidates have the same score (should select first)."""
        scores = [0.7, 0.7, 0.7]
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 0
        assert score == 0.7

    def test_empty_candidates(self):
        """Test with empty candidate list."""
        scores = []
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 0
        assert score == 0.0
        assert "No candidate frames" in reason

    def test_invalid_scores_type(self):
        """Test with non-numeric score in the list."""
        scores = [0.5, "invalid", 0.7]
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 0
        assert score == 0.0
        assert "not a number" in reason

    def test_nan_score(self):
        """Test with NaN score in the list."""
        import math
        scores = [0.5, math.nan, 0.7]
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 0
        assert score == 0.0
        assert "NaN" in reason

    def test_non_list_input(self):
        """Test with non-list input for candidate_scores."""
        selected_index, score, reason = self.node.run("not a list", "SSIM")
        assert selected_index == 0
        assert score == 0.0
        assert "must be a list" in reason

    def test_negative_scores(self):
        """Test with negative scores (valid for some metrics)."""
        scores = [-0.5, -0.2, -0.8]
        selected_index, score, reason = self.node.run(scores, "LPIPS")
        assert selected_index == 1
        assert score == -0.2

    def test_large_number_of_candidates(self):
        """Test with a large number of candidates."""
        scores = [float(i) / 100.0 for i in range(100)]
        selected_index, score, reason = self.node.run(scores, "SSIM")
        assert selected_index == 99
        assert score == 0.99

    def test_metric_in_reason(self):
        """Test that the metric name appears in the reason string."""
        scores = [0.5, 0.9]
        _, _, reason = self.node.run(scores, "PSNR")
        assert "PSNR" in reason
