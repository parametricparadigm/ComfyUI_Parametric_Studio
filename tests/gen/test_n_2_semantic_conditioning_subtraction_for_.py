import pytest
import json
import math
from psn_nodes.gen.n_2_semantic_conditioning_subtraction_for_ import (
    PSN_Conditioning_Subtract,
    PSN_Conditioning_Clamp,
    _mean_magnitude,
    _subtract_vectors,
    _clamp_vector,
    _parse_vector_json
)


class TestPSN_Conditioning_Subtract:
    def test_basic_subtraction(self):
        node = PSN_Conditioning_Subtract()
        base_vec = "[1.0, 2.0, 3.0]"
        sub_vec = "[0.5, 0.5, 0.5]"
        strength = 1.0
        auto_scale = False
        
        result_float, result_json = node.run(
            base_conditioning=0.0,
            subtract_conditioning=0.0,
            strength=strength,
            auto_scale=auto_scale,
            base_vector=base_vec,
            subtract_vector=sub_vec
        )
        
        expected = [1.0 - 0.5, 2.0 - 0.5, 3.0 - 0.5]
        parsed_result = json.loads(result_json)
        assert parsed_result == expected
        assert result_float == expected[0]

    def test_auto_scale(self):
        node = PSN_Conditioning_Subtract()
        base_vec = "[2.0, 2.0]"  # Norm = sqrt(8) = 2.828
        sub_vec = "[1.0, 1.0]"   # Norm = sqrt(2) = 1.414
        strength = 1.0
        auto_scale = True
        
        result_float, result_json = node.run(
            base_conditioning=0.0,
            subtract_conditioning=0.0,
            strength=strength,
            auto_scale=auto_scale,
            base_vector=base_vec,
            subtract_vector=sub_vec
        )
        
        # Auto-scale factor = base_norm / sub_norm = 2.828 / 1.414 = 2.0
        # Effective strength = 1.0 * 2.0 = 2.0
        # Result = [2.0 - (1.0 * 2.0), 2.0 - (1.0 * 2.0)] = [0.0, 0.0]
        expected = [0.0, 0.0]
        parsed_result = json.loads(result_json)
        assert parsed_result == expected
        assert result_float == 0.0

    def test_mismatched_lengths(self):
        node = PSN_Conditioning_Subtract()
        base_vec = "[1.0, 2.0]"
        sub_vec = "[1.0]"
        
        with pytest.raises(ValueError, match="Vectors must have the same length"):
            node.run(
                base_conditioning=0.0,
                subtract_conditioning=0.0,
                strength=1.0,
                auto_scale=False,
                base_vector=base_vec,
                subtract_vector=sub_vec
            )

    def test_invalid_vector_format(self):
        node = PSN_Conditioning_Subtract()
        base_vec = "not a list"
        sub_vec = "[1.0]"
        
        with pytest.raises(ValueError, match="Invalid JSON format"):
            node.run(
                base_conditioning=0.0,
                subtract_conditioning=0.0,
                strength=1.0,
                auto_scale=False,
                base_vector=base_vec,
                subtract_vector=sub_vec
            )

    def test_non_numeric_elements(self):
        node = PSN_Conditioning_Subtract()
        base_vec = "[1.0, \"two\"]"
        sub_vec = "[1.0, 1.0]"
        
        with pytest.raises(ValueError, match="All elements in the vector must be numbers"):
            node.run(
                base_conditioning=0.0,
                subtract_conditioning=0.0,
                strength=1.0,
                auto_scale=False,
                base_vector=base_vec,
                subtract_vector=sub_vec
            )


class TestPSN_Conditioning_Clamp:
    def test_linear_clamp(self):
        node = PSN_Conditioning_Clamp()
        vec = "[-2.0, 0.5, 3.0]"
        min_val = -1.0
        max_val = 1.0
        method = "linear"
        
        result_float, result_json = node.run(
            min_val=min_val,
            max_val=max_val,
            method=method,
            vector=vec
        )
        
        expected = [-1.0, 0.5, 1.0]
        parsed_result = json.loads(result_json)
        assert parsed_result == expected
        assert result_float == -1.0

    def test_tanh_clamp(self):
        node = PSN_Conditioning_Clamp()
        vec = "[-2.0, 0.0, 2.0]"
        min_val = -1.0
        max_val = 1.0
        method = "tanh"
        
        result_float, result_json = node.run(
            min_val=min_val,
            max_val=max_val,
            method=method,
            vector=vec
        )
        
        # tanh(-2) ≈ -0.9640, tanh(0) = 0, tanh(2) ≈ 0.9640
        # Center = 0, half_range = 1
        # Result: [0 + tanh(-2)*1, 0 + tanh(0)*1, 0 + tanh(2)*1]
        expected = [math.tanh(-2.0), 0.0, math.tanh(2.0)]
        parsed_result = json.loads(result_json)
        assert len(parsed_result) == len(expected)
        for r, e in zip(parsed_result, expected):
            assert abs(r - e) < 1e-6
        assert abs(result_float - math.tanh(-2.0)) < 1e-6

    def test_invalid_range(self):
        node = PSN_Conditioning_Clamp()
        vec = "[1.0]"
        min_val = 2.0
        max_val = 1.0
        method = "linear"
        
        with pytest.raises(ValueError, match="min_val must be less than or equal to max_val"):
            node.run(
                min_val=min_val,
                max_val=max_val,
                method=method,
                vector=vec
            )

    def test_invalid_method(self):
        node = PSN_Conditioning_Clamp()
        vec = "[1.0]"
        min_val = -1.0
        max_val = 1.0
        method = "invalid"
        
        with pytest.raises(ValueError, match="Unknown clamp method"):
            node.run(
                min_val=min_val,
                max_val=max_val,
                method=method,
                vector=vec
            )


class TestHelperFunctions:
    def test_mean_magnitude(self):
        vec = [3.0, 4.0]
        assert _mean_magnitude(vec) == 5.0  # sqrt(9 + 16) = 5
        
        vec = []
        assert _mean_magnitude(vec) == 0.0

    def test_subtract_vectors(self):
        base = [1.0, 2.0, 3.0]
        sub = [0.5, 0.5, 0.5]
        strength = 2.0
        result = _subtract_vectors(base, sub, strength)
        expected = [1.0 - 1.0, 2.0 - 1.0, 3.0 - 1.0]
        assert result == expected

    def test_clamp_vector_linear(self):
        vec = [-2.0, 0.5, 3.0]
        result = _clamp_vector(vec, -1.0, 1.0, "linear")
        expected = [-1.0, 0.5, 1.0]
        assert result == expected

    def test_clamp_vector_tanh(self):
        vec = [-1.0, 0.0, 1.0]
        result = _clamp_vector(vec, -1.0, 1.0, "tanh")
        expected = [math.tanh(-1.0), 0.0, math.tanh(1.0)]
        assert len(result) == len(expected)
        for r, e in zip(result, expected):
            assert abs(r - e) < 1e-6

    def test_parse_vector_json_valid(self):
        vec_str = "[1.0, 2.0, 3.0]"
        result = _parse_vector_json(vec_str)
        assert result == [1.0, 2.0, 3.0]

    def test_parse_vector_json_empty(self):
        result = _parse_vector_json("")
        assert result == []
        result = _parse_vector_json("[]")
        assert result == []

    def test_parse_vector_json_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON format"):
            _parse_vector_json("{invalid}")

    def test_parse_vector_json_not_list(self):
        with pytest.raises(ValueError, match="Parsed JSON must be a list"):
            _parse_vector_json("123")

    def test_parse_vector_json_non_numeric(self):
        with pytest.raises(ValueError, match="All elements in the vector must be numbers"):
            _parse_vector_json("[1.0, \"two\"]")
