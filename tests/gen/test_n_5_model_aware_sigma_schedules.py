"""
Tests for PSN_ModelAwareScheduler node.
"""

import json
import math
import pytest

from psn_nodes.gen.n_5_model_aware_sigma_schedules import (
    PSN_ModelAwareScheduler,
    _generate_sigmas,
    _validate_config,
    DEFAULT_SCHEDULES,
    MODEL_FAMILIES,
)


class TestPSNModelAwareScheduler:
    """Tests for the PSN_ModelAwareScheduler node."""
    
    def setup_method(self):
        self.node = PSN_ModelAwareScheduler()
    
    def test_input_types_structure(self):
        """Test that INPUT_TYPES has the correct structure."""
        input_types = PSN_ModelAwareScheduler.INPUT_TYPES()
        
        assert "required" in input_types
        assert "optional" in input_types
        
        assert "steps" in input_types["required"]
        assert "model_family" in input_types["required"]
        
        assert "config" in input_types["optional"]
    
    def test_return_types(self):
        """Test that RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_ModelAwareScheduler.RETURN_TYPES == ("LIST", "STRING")
        assert PSN_ModelAwareScheduler.RETURN_NAMES == ("sigmas", "schedule_info")
        assert PSN_ModelAwareScheduler.FUNCTION == "run"
        assert PSN_ModelAwareScheduler.CATEGORY == "ParametricStudio/Schedules"
    
    def test_generate_sigmas_basic(self):
        """Test basic sigma generation with default parameters."""
        sigmas = _generate_sigmas(10, 3.0, 1.0, 0.001)
        
        assert len(sigmas) == 10
        assert all(isinstance(s, float) for s in sigmas)
        assert all(s > 0 for s in sigmas)
        
        # First sigma should be close to start (1.0)
        assert sigmas[0] > 0.5
        # Last sigma should be close to end (0.001)
        assert sigmas[-1] < 0.1
    
    def test_generate_sigmas_single_step(self):
        """Test sigma generation with a single step."""
        sigmas = _generate_sigmas(1, 3.0, 1.0, 0.001)
        
        assert len(sigmas) == 1
        assert sigmas[0] == 1.0
    
    def test_generate_sigmas_zero_steps(self):
        """Test sigma generation with zero steps."""
        sigmas = _generate_sigmas(0, 3.0, 1.0, 0.001)
        
        assert sigmas == []
    
    def test_generate_sigmas_negative_steps(self):
        """Test sigma generation with negative steps."""
        sigmas = _generate_sigmas(-5, 3.0, 1.0, 0.001)
        
        assert sigmas == []
    
    def test_generate_sigmas_different_shifts(self):
        """Test that different shift values produce different sigmas."""
        sigmas_shift_2 = _generate_sigmas(10, 2.0, 1.0, 0.001)
        sigmas_shift_4 = _generate_sigmas(10, 4.0, 1.0, 0.001)
        
        assert len(sigmas_shift_2) == 10
        assert len(sigmas_shift_4) == 10
        
        # The sigmas should be different due to different shift values
        assert sigmas_shift_2 != sigmas_shift_4
    
    def test_validate_config_valid(self):
        """Test config validation with valid JSON."""
        config_json = json.dumps({"shift": 3.5, "start": 1.0, "end": 0.001})
        result = _validate_config(config_json)
        
        assert result is not None
        assert result["shift"] == 3.5
        assert result["start"] == 1.0
        assert result["end"] == 0.001
    
    def test_validate_config_invalid_json(self):
        """Test config validation with invalid JSON."""
        result = _validate_config("not valid json")
        
        assert result is None
    
    def test_validate_config_empty(self):
        """Test config validation with empty string."""
        result = _validate_config("")
        
        assert result is None
    
    def test_validate_config_none(self):
        """Test config validation with None."""
        result = _validate_config(None)
        
        assert result is None
    
    def test_validate_config_invalid_values(self):
        """Test config validation with out-of-range values."""
        # Shift too high
        result = _validate_config(json.dumps({"shift": 15.0}))
        assert result is None
        
        # Start too low
        result = _validate_config(json.dumps({"start": -1.0}))
        assert result is None
        
        # End too high
        result = _validate_config(json.dumps({"end": 10.0}))
        assert result is None
    
    def test_validate_config_partial(self):
        """Test config validation with partial config."""
        config_json = json.dumps({"shift": 3.5})
        result = _validate_config(config_json)
        
        assert result is not None
        assert result["shift"] == 3.5
        assert "start" not in result
        assert "end" not in result
    
    def test_run_basic(self):
        """Test basic run with default parameters."""
        sigmas, schedule_info = self.node.run(20, "Flux1")
        
        assert len(sigmas) == 20
        assert all(isinstance(s, float) for s in sigmas)
        
        info = json.loads(schedule_info)
        assert info["model_family"] == "Flux1"
        assert info["steps"] == 20
        assert info["shift"] == 3.5
        assert info["start"] == 1.0
        assert info["end"] == 0.001
        assert info["num_sigmas"] == 20
    
    def test_run_different_families(self):
        """Test that different model families produce different sigmas."""
        sigmas_krea, _ = self.node.run(20, "Krea2")
        sigmas_flux, _ = self.node.run(20, "Flux1")
        sigmas_sd3, _ = self.node.run(20, "SD3")
        
        assert len(sigmas_krea) == 20
        assert len(sigmas_flux) == 20
        assert len(sigmas_sd3) == 20
        
        # All should be different due to different shift values
        assert sigmas_krea != sigmas_flux
        assert sigmas_flux != sigmas_sd3
        assert sigmas_krea != sigmas_sd3
    
    def test_run_with_config_override(self):
        """Test run with config override."""
        config_json = json.dumps({"shift": 5.0})
        sigmas, schedule_info = self.node.run(20, "Flux1", config=config_json)
        
        info = json.loads(schedule_info)
        assert info["shift"] == 5.0
        assert info["start"] == 1.0  # Default start
        assert info["end"] == 0.001  # Default end
        
        # Compare with default Flux1 sigmas
        sigmas_default, _ = self.node.run(20, "Flux1")
        assert sigmas != sigmas_default
    
    def test_run_invalid_steps(self):
        """Test run with invalid steps (should default to 20)."""
        sigmas, schedule_info = self.node.run(0, "Flux1")
        
        info = json.loads(schedule_info)
        assert info["steps"] == 20
        assert len(sigmas) == 20
    
    def test_run_invalid_model_family(self):
        """Test run with invalid model family (should default to Auto)."""
        sigmas, schedule_info = self.node.run(20, "InvalidFamily")
        
        info = json.loads(schedule_info)
        assert info["model_family"] == "Auto"
        assert len(sigmas) == 20
    
    def test_run_single_step(self):
        """Test run with a single step."""
        sigmas, schedule_info = self.node.run(1, "Flux1")
        
        assert len(sigmas) == 1
        assert sigmas[0] == 1.0
        
        info = json.loads(schedule_info)
        assert info["steps"] == 1
        assert info["num_sigmas"] == 1
    
    def test_run_large_steps(self):
        """Test run with a large number of steps."""
        sigmas, schedule_info = self.node.run(100, "Flux1")
        
        assert len(sigmas) == 100
        assert all(isinstance(s, float) for s in sigmas)
        assert all(s > 0 for s in sigmas)
        
        info = json.loads(schedule_info)
        assert info["steps"] == 100
        assert info["num_sigmas"] == 100
    
    def test_node_class_mappings(self):
        """Test that NODE_CLASS_MAPPINGS is correctly defined."""
        from psn_nodes.gen.n_5_model_aware_sigma_schedules import NODE_CLASS_MAPPINGS
        
        assert "PSN_ModelAwareScheduler" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_ModelAwareScheduler"] == PSN_ModelAwareScheduler
    
    def test_node_display_name_mappings(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS is correctly defined."""
        from psn_nodes.gen.n_5_model_aware_sigma_schedules import NODE_DISPLAY_NAME_MAPPINGS
        
        assert "PSN_ModelAwareScheduler" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ModelAwareScheduler"] == "Model-Aware Sigma Scheduler"
    
    def test_model_families_list(self):
        """Test that MODEL_FAMILIES contains the expected values."""
        assert "Auto" in MODEL_FAMILIES
        assert "Krea2" in MODEL_FAMILIES
        assert "Flux1" in MODEL_FAMILIES
        assert "SD3" in MODEL_FAMILIES
    
    def test_default_schedules(self):
        """Test that DEFAULT_SCHEDULES has the expected structure."""
        for family in ["Krea2", "Flux1", "SD3", "Auto"]:
            assert family in DEFAULT_SCHEDULES
            schedule = DEFAULT_SCHEDULES[family]
            assert "shift" in schedule
            assert "start" in schedule
            assert "end" in schedule
            assert schedule["shift"] > 0
            assert schedule["start"] > 0
            assert schedule["end"] > 0
            assert schedule["end"] < schedule["start"]
