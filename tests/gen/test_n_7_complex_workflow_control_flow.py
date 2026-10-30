"""
Tests for PSN_List_Filter and PSN_Set_Operation nodes.
"""

import pytest
from psn_nodes.gen.n_7_complex_workflow_control_flow import (
    PSN_List_Filter,
    PSN_Set_Operation,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


class TestPSNListFilter:
    """Tests for PSN_List_Filter node."""
    
    def setup_method(self):
        self.node = PSN_List_Filter()
    
    def test_filter_none_values(self):
        """Test that None values are removed when condition_type is 'is_not_none'."""
        input_list = [1, None, 2, None, 3, None]
        result = self.node.run(input_list, "is_not_none")
        assert result[0] == [1, 2, 3]
    
    def test_filter_empty_values(self):
        """Test that empty values are removed when condition_type is 'is_not_empty'."""
        input_list = [1, "", 2, [], 3, {}, None, "hello", [1, 2]]
        result = self.node.run(input_list, "is_not_empty")
        assert result[0] == [1, 2, 3, "hello", [1, 2]]
    
    def test_filter_custom_is_string(self):
        """Test custom filter with 'is_string' function."""
        input_list = [1, "hello", 2, "world", None, 3.14]
        result = self.node.run(input_list, "custom", "is_string")
        assert result[0] == ["hello", "world"]
    
    def test_filter_custom_is_number(self):
        """Test custom filter with 'is_number' function."""
        input_list = [1, "hello", 2.5, None, 3, "world", True]
        result = self.node.run(input_list, "custom", "is_number")
        assert result[0] == [1, 2.5, 3]
    
    def test_filter_custom_is_positive(self):
        """Test custom filter with 'is_positive' function."""
        input_list = [-1, 0, 1, -2.5, 3.14, "hello", None]
        result = self.node.run(input_list, "custom", "is_positive")
        assert result[0] == [1, 3.14]
    
    def test_filter_empty_list(self):
        """Test filtering an empty list."""
        input_list = []
        result = self.node.run(input_list, "is_not_none")
        assert result[0] == []
    
    def test_filter_all_none(self):
        """Test filtering a list with all None values."""
        input_list = [None, None, None]
        result = self.node.run(input_list, "is_not_none")
        assert result[0] == []
    
    def test_filter_non_list_input(self):
        """Test that non-list input is handled gracefully."""
        result = self.node.run(42, "is_not_none")
        assert result[0] == [42]
    
    def test_filter_custom_unknown_function(self):
        """Test that unknown custom functions keep all items."""
        input_list = [1, "hello", None, 2]
        result = self.node.run(input_list, "custom", "unknown_function")
        assert result[0] == [1, "hello", None, 2]
    
    def test_filter_custom_empty_string(self):
        """Test that empty custom_func string keeps all items."""
        input_list = [1, "hello", None, 2]
        result = self.node.run(input_list, "custom", "")
        assert result[0] == [1, "hello", None, 2]
    
    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = PSN_List_Filter.INPUT_TYPES()
        assert "required" in input_types
        assert "optional" in input_types
        assert "input_list" in input_types["required"]
        assert "condition_type" in input_types["required"]
        assert "custom_func" in input_types["optional"]
    
    def test_return_types(self):
        """Test that RETURN_TYPES is correct."""
        assert PSN_List_Filter.RETURN_TYPES == ("LIST",)
        assert PSN_List_Filter.RETURN_NAMES == ("filtered_list",)
        assert PSN_List_Filter.FUNCTION == "run"


class TestPSNSetOperation:
    """Tests for PSN_Set_Operation node."""
    
    def setup_method(self):
        self.node = PSN_Set_Operation()
    
    def test_union(self):
        """Test union operation."""
        set_a = {1, 2, 3}
        set_b = {3, 4, 5}
        result = self.node.run(set_a, set_b, "union")
        assert result[0] == {1, 2, 3, 4, 5}
    
    def test_intersection(self):
        """Test intersection operation."""
        set_a = {1, 2, 3}
        set_b = {3, 4, 5}
        result = self.node.run(set_a, set_b, "intersection")
        assert result[0] == {3}
    
    def test_difference(self):
        """Test difference operation."""
        set_a = {1, 2, 3}
        set_b = {3, 4, 5}
        result = self.node.run(set_a, set_b, "difference")
        assert result[0] == {1, 2}
    
    def test_union_disjoint_sets(self):
        """Test union of disjoint sets."""
        set_a = {1, 2}
        set_b = {3, 4}
        result = self.node.run(set_a, set_b, "union")
        assert result[0] == {1, 2, 3, 4}
    
    def test_intersection_disjoint_sets(self):
        """Test intersection of disjoint sets."""
        set_a = {1, 2}
        set_b = {3, 4}
        result = self.node.run(set_a, set_b, "intersection")
        assert result[0] == set()
    
    def test_difference_empty_result(self):
        """Test difference when all elements are in set_b."""
        set_a = {1, 2}
        set_b = {1, 2, 3}
        result = self.node.run(set_a, set_b, "difference")
        assert result[0] == set()
    
    def test_empty_sets(self):
        """Test operations with empty sets."""
        set_a = set()
        set_b = {1, 2, 3}
        
        result_union = self.node.run(set_a, set_b, "union")
        assert result_union[0] == {1, 2, 3}
        
        result_intersection = self.node.run(set_a, set_b, "intersection")
        assert result_intersection[0] == set()
        
        result_difference = self.node.run(set_a, set_b, "difference")
        assert result_difference[0] == set()
    
    def test_non_set_inputs(self):
        """Test that non-set inputs are converted to sets."""
        list_a = [1, 2, 3]
        list_b = [3, 4, 5]
        result = self.node.run(list_a, list_b, "intersection")
        assert result[0] == {3}
    
    def test_single_element_inputs(self):
        """Test that single non-iterable inputs are wrapped in sets."""
        result = self.node.run(1, 2, "union")
        assert result[0] == {1, 2}
    
    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = PSN_Set_Operation.INPUT_TYPES()
        assert "required" in input_types
        assert "set_a" in input_types["required"]
        assert "set_b" in input_types["required"]
        assert "operation" in input_types["required"]
    
    def test_return_types(self):
        """Test that RETURN_TYPES is correct."""
        assert PSN_Set_Operation.RETURN_TYPES == ("SET",)
        assert PSN_Set_Operation.RETURN_NAMES == ("result_set",)
        assert PSN_Set_Operation.FUNCTION == "run"


class TestNodeMappings:
    """Tests for node mappings."""
    
    def test_node_class_mappings(self):
        """Test that NODE_CLASS_MAPPINGS contains both nodes."""
        assert "PSN_List_Filter" in NODE_CLASS_MAPPINGS
        assert "PSN_Set_Operation" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_List_Filter"] == PSN_List_Filter
        assert NODE_CLASS_MAPPINGS["PSN_Set_Operation"] == PSN_Set_Operation
    
    def test_node_display_name_mappings(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS contains both nodes."""
        assert "PSN_List_Filter" in NODE_DISPLAY_NAME_MAPPINGS
        assert "PSN_Set_Operation" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_List_Filter"] == "PSN List Filter"
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Set_Operation"] == "PSN Set Operation"
    
    def test_node_names_start_with_psn(self):
        """Test that all node names start with PSN_."""
        for node_name in NODE_CLASS_MAPPINGS:
            assert node_name.startswith("PSN_"), f"Node {node_name} does not start with PSN_"
