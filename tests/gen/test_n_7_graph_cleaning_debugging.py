"""
Tests for PSN Graph Cleaning & Debugging nodes.

These tests verify the pure-logic functionality of:
- PSN_Graph_Cleaner: Removing orphaned nodes from graphs
- PSN_List_Processor: List operations (SORT, REVERSE, UNIQUE, SLICE)

No file I/O, network access, or GPU operations are used.
"""

import pytest
from psn_nodes.gen.n_7_graph_cleaning_debugging import (
    PSN_Graph_Cleaner,
    PSN_List_Processor,
    clean_graph,
    process_list,
    LIST_OPERATIONS,
)


class TestPSN_Graph_Cleaner:
    """Tests for PSN_Graph_Cleaner node."""
    
    def test_removes_orphaned_node(self):
        """Test that orphaned nodes are removed from the graph."""
        graph = {
            "nodes": {
                "node1": {
                    "id": "node1",
                    "inputs": [],
                    "outputs": []
                },
                "node2": {
                    "id": "node2",
                    "inputs": [{"node": "node1", "slot": 0}],
                    "outputs": []
                }
            }
        }
        
        cleaner = PSN_Graph_Cleaner()
        (cleaned_graph,) = cleaner.run(graph)
        
        # node1 is referenced by node2, so it should NOT be removed
        # node2 has an input connection, so it should NOT be removed
        assert "node1" in cleaned_graph["nodes"]
        assert "node2" in cleaned_graph["nodes"]
    
    def test_removes_truly_orphaned_node(self):
        """Test that a node with no connections is removed."""
        graph = {
            "nodes": {
                "orphan": {
                    "id": "orphan",
                    "inputs": [],
                    "outputs": []
                },
                "connected1": {
                    "id": "connected1",
                    "inputs": [],
                    "outputs": []
                },
                "connected2": {
                    "id": "connected2",
                    "inputs": [{"node": "connected1", "slot": 0}],
                    "outputs": []
                }
            }
        }
        
        cleaner = PSN_Graph_Cleaner()
        (cleaned_graph,) = cleaner.run(graph)
        
        # orphan has no connections and is not referenced
        assert "orphan" not in cleaned_graph["nodes"]
        # connected1 is referenced by connected2
        assert "connected1" in cleaned_graph["nodes"]
        # connected2 has an input connection
        assert "connected2" in cleaned_graph["nodes"]
    
    def test_empty_graph(self):
        """Test that an empty graph is handled correctly."""
        graph = {"nodes": {}}
        
        cleaner = PSN_Graph_Cleaner()
        (cleaned_graph,) = cleaner.run(graph)
        
        assert cleaned_graph["nodes"] == {}
    
    def test_graph_with_no_nodes_key(self):
        """Test that a graph without 'nodes' key is handled."""
        graph = {"other_key": "value"}
        
        cleaner = PSN_Graph_Cleaner()
        (cleaned_graph,) = cleaner.run(graph)
        
        assert "nodes" in cleaned_graph
        assert cleaned_graph["nodes"] == {}
    
    def test_invalid_graph_type(self):
        """Test that invalid graph type raises an error."""
        with pytest.raises(ValueError):
            clean_graph("not a dict")
    
    def test_invalid_nodes_type(self):
        """Test that invalid nodes type raises an error."""
        graph = {"nodes": "not a dict"}
        with pytest.raises(ValueError):
            clean_graph(graph)
    
    def test_preserves_other_graph_keys(self):
        """Test that other keys in the graph are preserved."""
        graph = {
            "nodes": {
                "node1": {
                    "id": "node1",
                    "inputs": [],
                    "outputs": []
                }
            },
            "links": [1, 2, 3],
            "metadata": {"version": 1}
        }
        
        cleaner = PSN_Graph_Cleaner()
        (cleaned_graph,) = cleaner.run(graph)
        
        assert "links" in cleaned_graph
        assert cleaned_graph["links"] == [1, 2, 3]
        assert "metadata" in cleaned_graph
        assert cleaned_graph["metadata"] == {"version": 1}


class TestPSN_List_Processor:
    """Tests for PSN_List_Processor node."""
    
    def test_sort_operation(self):
        """Test SORT operation on a list of numbers."""
        processor = PSN_List_Processor()
        (result,) = processor.run([3, 1, 4, 1, 5, 9, 2, 6], "SORT")
        
        assert result == [1, 1, 2, 3, 4, 5, 6, 9]
    
    def test_sort_strings(self):
        """Test SORT operation on a list of strings."""
        processor = PSN_List_Processor()
        (result,) = processor.run(["banana", "apple", "cherry"], "SORT")
        
        assert result == ["apple", "banana", "cherry"]
    
    def test_reverse_operation(self):
        """Test REVERSE operation."""
        processor = PSN_List_Processor()
        (result,) = processor.run([1, 2, 3, 4, 5], "REVERSE")
        
        assert result == [5, 4, 3, 2, 1]
    
    def test_unique_operation(self):
        """Test UNIQUE operation removes duplicates while preserving order."""
        processor = PSN_List_Processor()
        (result,) = processor.run([3, 1, 4, 1, 5, 9, 2, 6, 5, 3], "UNIQUE")
        
        assert result == [3, 1, 4, 5, 9, 2, 6]
    
    def test_slice_operation(self):
        """Test SLICE operation with start and end."""
        processor = PSN_List_Processor()
        (result,) = processor.run([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "SLICE", start=2, end=5)
        
        assert result == [3, 4, 5]
    
    def test_slice_operation_to_end(self):
        """Test SLICE operation with end=-1 (to end)."""
        processor = PSN_List_Processor()
        (result,) = processor.run([1, 2, 3, 4, 5], "SLICE", start=2, end=-1)
        
        assert result == [3, 4, 5]
    
    def test_slice_operation_from_start(self):
        """Test SLICE operation with start=0."""
        processor = PSN_List_Processor()
        (result,) = processor.run([1, 2, 3, 4, 5], "SLICE", start=0, end=3)
        
        assert result == [1, 2, 3]
    
    def test_empty_list(self):
        """Test operations on an empty list."""
        processor = PSN_List_Processor()
        
        (result,) = processor.run([], "SORT")
        assert result == []
        
        (result,) = processor.run([], "REVERSE")
        assert result == []
        
        (result,) = processor.run([], "UNIQUE")
        assert result == []
        
        (result,) = processor.run([], "SLICE", start=0, end=5)
        assert result == []
    
    def test_invalid_operation(self):
        """Test that invalid operation raises an error."""
        processor = PSN_List_Processor()
        with pytest.raises(ValueError):
            processor.run([1, 2, 3], "INVALID_OP")
    
    def test_invalid_input_type(self):
        """Test that non-list input raises an error."""
        processor = PSN_List_Processor()
        with pytest.raises(ValueError):
            processor.run("not a list", "SORT")
    
    def test_mixed_type_sort(self):
        """Test SORT with mixed types (should not crash)."""
        processor = PSN_List_Processor()
        (result,) = processor.run([3, "apple", 1, "banana"], "SORT")
        
        # Should return a sorted list (by string representation for mixed types)
        assert len(result) == 4
    
    def test_unique_with_mixed_types(self):
        """Test UNIQUE with mixed types."""
        processor = PSN_List_Processor()
        (result,) = processor.run([1, "1", 1, "2", 2], "UNIQUE")
        
        # 1 (int) and "1" (str) are different, so both should be kept
        assert 1 in result
        assert "1" in result
        assert len(result) == 4  # 1, "1", "2", 2


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_process_list_sort(self):
        """Test process_list with SORT."""
        result = process_list([3, 1, 2], "SORT")
        assert result == [1, 2, 3]
    
    def test_process_list_reverse(self):
        """Test process_list with REVERSE."""
        result = process_list([1, 2, 3], "REVERSE")
        assert result == [3, 2, 1]
    
    def test_process_list_unique(self):
        """Test process_list with UNIQUE."""
        result = process_list([1, 2, 2, 3, 3, 3], "UNIQUE")
        assert result == [1, 2, 3]
    
    def test_process_list_slice(self):
        """Test process_list with SLICE."""
        result = process_list([1, 2, 3, 4, 5], "SLICE", start=1, end=4)
        assert result == [2, 3, 4]
    
    def test_process_list_invalid_operation(self):
        """Test process_list with invalid operation."""
        with pytest.raises(ValueError):
            process_list([1, 2, 3], "INVALID")
    
    def test_process_list_invalid_input(self):
        """Test process_list with invalid input type."""
        with pytest.raises(ValueError):
            process_list("not a list", "SORT")
    
    def test_list_operations_constant(self):
        """Test that LIST_OPERATIONS contains expected values."""
        assert "SORT" in LIST_OPERATIONS
        assert "REVERSE" in LIST_OPERATIONS
        assert "UNIQUE" in LIST_OPERATIONS
        assert "SLICE" in LIST_OPERATIONS
        assert len(LIST_OPERATIONS) == 4
