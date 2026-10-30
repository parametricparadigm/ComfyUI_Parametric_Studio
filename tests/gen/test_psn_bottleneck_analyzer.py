"""Tests for PSN_Bottleneck_Analyzer node."""

import pytest

from psn_nodes.gen.psn_bottleneck_analyzer import (
    PSN_Bottleneck_Analyzer,
    _validate_profile_data,
    _find_bottlenecks,
    _build_report,
)


class TestPSN_Bottleneck_Analyzer:
    """Test suite for the PSN_Bottleneck_Analyzer node."""

    def setup_method(self):
        self.node = PSN_Bottleneck_Analyzer()

    def test_basic_sorting_logic(self):
        """Verify that nodes are sorted by execution time descending."""
        profile = {
            "fast_node": 0.01,
            "medium_node": 0.5,
            "slow_node": 2.0,
            "fastest_node": 0.001,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=3)

        assert len(top_bottlenecks) == 3
        assert top_bottlenecks[0] == ["slow_node", 2.0]
        assert top_bottlenecks[1] == ["medium_node", 0.5]
        assert top_bottlenecks[2] == ["fast_node", 0.01]

    def test_top_n_larger_than_profile_size(self):
        """When top_n exceeds the number of nodes, return all nodes."""
        profile = {
            "node_a": 1.0,
            "node_b": 2.0,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=10)

        assert len(top_bottlenecks) == 2
        assert top_bottlenecks[0] == ["node_b", 2.0]
        assert top_bottlenecks[1] == ["node_a", 1.0]

    def test_top_n_zero_returns_empty(self):
        """When top_n is 0, return an empty list."""
        profile = {
            "node_a": 1.0,
            "node_b": 2.0,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=0)

        assert top_bottlenecks == []
        assert "No bottlenecks found" in report

    def test_empty_profile_data(self):
        """Empty dict should return empty results without error."""
        top_bottlenecks, report = self.node.run({}, top_n=5)

        assert top_bottlenecks == []
        assert "No bottlenecks found" in report

    def test_tie_breaking_alphabetical(self):
        """Ties in execution time should be broken alphabetically by node name."""
        profile = {
            "zeta": 1.0,
            "alpha": 1.0,
            "mid": 1.0,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=3)

        assert top_bottlenecks[0] == ["alpha", 1.0]
        assert top_bottlenecks[1] == ["mid", 1.0]
        assert top_bottlenecks[2] == ["zeta", 1.0]

    def test_invalid_profile_data_not_dict(self):
        """Non-dict input should return error report."""
        top_bottlenecks, report = self.node.run("not a dict", top_n=5)

        assert top_bottlenecks == []
        assert "Error" in report
        assert "must be a dict" in report

    def test_invalid_profile_data_non_string_key(self):
        """Non-string keys should be rejected."""
        profile = {123: 1.0}
        top_bottlenecks, report = self.node.run(profile, top_n=5)

        assert top_bottlenecks == []
        assert "Error" in report
        assert "must be a string" in report

    def test_invalid_profile_data_non_numeric_value(self):
        """Non-numeric values should be rejected."""
        profile = {"node_a": "fast"}
        top_bottlenecks, report = self.node.run(profile, top_n=5)

        assert top_bottlenecks == []
        assert "Error" in report
        assert "must be a number" in report

    def test_invalid_profile_data_negative_time(self):
        """Negative execution times should be rejected."""
        profile = {"node_a": -1.0}
        top_bottlenecks, report = self.node.run(profile, top_n=5)

        assert top_bottlenecks == []
        assert "Error" in report
        assert "non-negative" in report

    def test_invalid_profile_data_bool_value(self):
        """Boolean values should be rejected (bool is subclass of int)."""
        profile = {"node_a": True}
        top_bottlenecks, report = self.node.run(profile, top_n=5)

        assert top_bottlenecks == []
        assert "Error" in report
        assert "must be a number" in report

    def test_report_formatting(self):
        """Verify the report string contains expected content."""
        profile = {
            "slow": 3.0,
            "fast": 0.1,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=2)

        assert "Bottleneck Analysis Report" in report
        assert "Total nodes profiled: 2" in report
        assert "Top 2 slowest nodes:" in report
        assert "1. slow: 3.000000 seconds" in report
        assert "2. fast: 0.100000 seconds" in report

    def test_single_node_profile(self):
        """A profile with a single node should work correctly."""
        profile = {"only_node": 5.5}
        top_bottlenecks, report = self.node.run(profile, top_n=5)

        assert len(top_bottlenecks) == 1
        assert top_bottlenecks[0] == ["only_node", 5.5]
        assert "only_node: 5.500000 seconds" in report

    def test_integer_execution_times(self):
        """Integer execution times should be accepted and converted to float."""
        profile = {
            "node_a": 2,
            "node_b": 1,
        }
        top_bottlenecks, report = self.node.run(profile, top_n=2)

        assert top_bottlenecks[0] == ["node_a", 2.0]
        assert top_bottlenecks[1] == ["node_b", 1.0]

    def test_validate_profile_data_helper(self):
        """Directly test the validation helper function."""
        valid, msg, normalized = _validate_profile_data({"a": 1.0, "b": 2.0})
        assert valid is True
        assert msg == ""
        assert normalized == {"a": 1.0, "b": 2.0}

        valid, msg, normalized = _validate_profile_data("bad")
        assert valid is False
        assert "must be a dict" in msg
        assert normalized == {}

    def test_find_bottlenecks_helper(self):
        """Directly test the bottleneck finding helper."""
        profile = {"a": 1.0, "b": 3.0, "c": 2.0}
        result = _find_bottlenecks(profile, 2)
        assert result == [("b", 3.0), ("c", 2.0)]

        result = _find_bottlenecks(profile, 0)
        assert result == []

    def test_build_report_helper(self):
        """Directly test the report building helper."""
        bottlenecks = [("slow", 2.0), ("fast", 0.5)]
        report = _build_report(bottlenecks, 2, 2)
        assert "slow: 2.000000 seconds" in report
        assert "fast: 0.500000 seconds" in report

        report_empty = _build_report([], 0, 5)
        assert "No bottlenecks found" in report_empty
