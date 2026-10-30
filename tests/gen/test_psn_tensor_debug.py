"""
Tests for PSN Tensor Debug nodes.
"""

import json
import pytest
from psn_nodes.gen.psn_tensor_debug import (
    PSN_Tensor_Inspect,
    PSN_Tensor_Save,
    _validate_tensor_data,
    _flatten_tensor,
    _get_shape,
    _compute_stats,
    _validate_path,
)


class TestPSNTensorInspect:
    """Tests for PSN_Tensor_Inspect node."""
    
    def test_basic_statistics(self):
        """Verify statistics are correct for a known tensor."""
        node = PSN_Tensor_Inspect()
        tensor_data = json.dumps([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data=tensor_data,
            dtype="float32",
            print_values=False
        )
        assert shape == "(2, 3)"
        assert dtype == "float32"
        assert min_val == 1.0
        assert max_val == 6.0
        assert mean_val == pytest.approx(3.5)
    
    def test_single_element_tensor(self):
        """Test with a single-element tensor."""
        node = PSN_Tensor_Inspect()
        tensor_data = json.dumps([[42.0]])
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data=tensor_data,
            dtype="float64",
            print_values=False
        )
        assert shape == "(1, 1)"
        assert min_val == 42.0
        assert max_val == 42.0
        assert mean_val == 42.0
    
    def test_invalid_json_input(self):
        """Test with invalid JSON input."""
        node = PSN_Tensor_Inspect()
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data="not valid json",
            dtype="float32",
            print_values=False
        )
        assert shape.startswith("error")
    
    def test_empty_tensor(self):
        """Test with empty tensor data."""
        node = PSN_Tensor_Inspect()
        tensor_data = json.dumps([])
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data=tensor_data,
            dtype="float32",
            print_values=False
        )
        assert shape.startswith("error")
    
    def test_non_numeric_tensor(self):
        """Test with non-numeric values in tensor."""
        node = PSN_Tensor_Inspect()
        tensor_data = json.dumps([["a", "b"], ["c", "d"]])
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data=tensor_data,
            dtype="float32",
            print_values=False
        )
        assert shape.startswith("error")
    
    def test_print_values_flag(self):
        """Test that print_values flag doesn't cause errors (pure logic)."""
        node = PSN_Tensor_Inspect()
        tensor_data = json.dumps([[1.0, 2.0]])
        # Should not raise, just returns stats
        shape, dtype, min_val, max_val, mean_val = node.run(
            tensor_data=tensor_data,
            dtype="float32",
            print_values=True,
            max_print_elements=50
        )
        assert shape == "(1, 2)"
        assert min_val == 1.0
        assert max_val == 2.0


class TestPSNTensorSave:
    """Tests for PSN_Tensor_Save node."""
    
    def test_valid_path(self):
        """Test with a valid path."""
        node = PSN_Tensor_Save()
        result = node.run(path="output/tensor.pt")
        assert result[0] == "output/tensor.pt"
    
    def test_empty_path(self):
        """Test with empty path."""
        node = PSN_Tensor_Save()
        result = node.run(path="")
        assert result[0].startswith("error")
    
    def test_path_with_null_byte(self):
        """Test with path containing null byte."""
        node = PSN_Tensor_Save()
        result = node.run(path="bad\x00path.pt")
        assert result[0].startswith("error")
    
    def test_non_string_path(self):
        """Test with non-string path."""
        node = PSN_Tensor_Save()
        result = node.run(path=12345)
        assert result[0].startswith("error")
    
    def test_path_with_tensor_data(self):
        """Test with valid tensor data provided."""
        node = PSN_Tensor_Save()
        tensor_data = json.dumps([[1.0, 2.0]])
        result = node.run(path="test.pt", tensor_data=tensor_data)
        assert result[0] == "test.pt"
    
    def test_path_with_invalid_tensor_data(self):
        """Test with invalid tensor data."""
        node = PSN_Tensor_Save()
        result = node.run(path="test.pt", tensor_data="invalid json")
        assert result[0].startswith("error")


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_flatten_tensor(self):
        """Test tensor flattening."""
        data = [[1, 2], [3, 4]]
        assert _flatten_tensor(data) == [1, 2, 3, 4]
    
    def test_get_shape(self):
        """Test shape extraction."""
        data = [[1, 2, 3], [4, 5, 6]]
        assert _get_shape(data) == (2, 3)
    
    def test_compute_stats(self):
        """Test statistics computation."""
        data = [[1, 2], [3, 4]]
        min_val, max_val, mean_val = _compute_stats(data)
        assert min_val == 1.0
        assert max_val == 4.0
        assert mean_val == 2.5
    
    def test_validate_path_valid(self):
        """Test valid path validation."""
        is_valid, err = _validate_path("valid/path.pt")
        assert is_valid is True
        assert err == ""
    
    def test_validate_path_invalid(self):
        """Test invalid path validation."""
        is_valid, err = _validate_path("")
        assert is_valid is False
        assert err != ""
