"""
Tests for PSN_NodeProfiler.

These tests verify the pure-logic timing profiler without any network, file,
or GPU dependencies. We use small simulated durations to keep tests fast.
"""

import json
import pytest
from psn_nodes.gen.psn_node_profiler import PSN_NodeProfiler, _profile_operations


class TestPSN_NodeProfiler:
    """Test suite for PSN_NodeProfiler node."""

    def test_basic_profiling_single_node(self):
        """Test profiling a single node with a small duration."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "test_node", "duration": 0.001}])
        result = node.run("run_1", ops)
        
        assert len(result) == 1
        profile = result[0]
        assert profile["run_id"] == "run_1"
        assert "test_node" in profile["nodes"]
        assert profile["nodes"]["test_node"]["duration"] >= 0.001
        assert profile["total_duration"] >= 0.001

    def test_profiling_multiple_nodes(self):
        """Test profiling multiple nodes and verify all are present."""
        node = PSN_NodeProfiler()
        ops = json.dumps([
            {"name": "node_a", "duration": 0.001},
            {"name": "node_b", "duration": 0.002},
            {"name": "node_c", "duration": 0.001},
        ])
        result = node.run("run_2", ops)
        
        profile = result[0]
        assert profile["run_id"] == "run_2"
        assert set(profile["nodes"].keys()) == {"node_a", "node_b", "node_c"}
        assert profile["total_duration"] >= 0.004  # Sum of durations

    def test_empty_operations_list(self):
        """Test that an empty operations list returns valid profile with zero duration."""
        node = PSN_NodeProfiler()
        ops = json.dumps([])
        result = node.run("run_3", ops)
        
        profile = result[0]
        assert profile["run_id"] == "run_3"
        assert profile["nodes"] == {}
        assert profile["total_duration"] == 0.0

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises a ValueError."""
        node = PSN_NodeProfiler()
        with pytest.raises(ValueError, match="Invalid JSON"):
            node.run("run_4", "not valid json")

    def test_operations_not_a_list_raises_error(self):
        """Test that non-list JSON raises a ValueError."""
        node = PSN_NodeProfiler()
        ops = json.dumps({"name": "test"})  # Dict, not list
        with pytest.raises(ValueError, match="must be a JSON list"):
            node.run("run_5", ops)

    def test_operation_missing_name_raises_error(self):
        """Test that an operation without a name field raises a ValueError."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"duration": 0.001}])  # Missing 'name'
        with pytest.raises(ValueError, match="must have a 'name'"):
            node.run("run_6", ops)

    def test_operation_negative_duration_raises_error(self):
        """Test that a negative duration raises a ValueError."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "test", "duration": -0.001}])
        with pytest.raises(ValueError, match="must be non-negative"):
            node.run("run_7", ops)

    def test_operation_non_numeric_duration_raises_error(self):
        """Test that a non-numeric duration raises a ValueError."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "test", "duration": "fast"}])
        with pytest.raises(ValueError, match="must be a number"):
            node.run("run_8", ops)

    def test_verbose_mode_includes_metadata(self):
        """Test that verbose mode adds extra metadata to the profile."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "node_x", "duration": 0.001}])
        result = node.run("run_9", ops, verbose=True)
        
        profile = result[0]
        assert profile.get("verbose") is True
        assert profile.get("node_count") == 1

    def test_zero_duration_node(self):
        """Test that a node with zero duration is handled correctly."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "instant_node", "duration": 0.0}])
        result = node.run("run_10", ops)
        
        profile = result[0]
        assert "instant_node" in profile["nodes"]
        assert profile["nodes"]["instant_node"]["duration"] >= 0.0
        assert profile["total_duration"] >= 0.0

    def test_profile_operations_direct_call(self):
        """Test the internal _profile_operations function directly."""
        ops = [
            {"name": "direct_a", "duration": 0.001},
            {"name": "direct_b", "duration": 0.001},
        ]
        profile = _profile_operations("direct_run", ops)
        
        assert profile["run_id"] == "direct_run"
        assert len(profile["nodes"]) == 2
        assert profile["total_duration"] >= 0.002

    def test_run_id_is_preserved(self):
        """Test that the run_id is correctly preserved in the output."""
        node = PSN_NodeProfiler()
        ops = json.dumps([{"name": "test", "duration": 0.001}])
        result = node.run("unique_run_id_123", ops)
        
        profile = result[0]
        assert profile["run_id"] == "unique_run_id_123"
