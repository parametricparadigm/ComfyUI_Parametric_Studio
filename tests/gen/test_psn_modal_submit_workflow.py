"""
Tests for PSN_Modal_Submit_Workflow node.

These tests verify the pure-logic implementation of the Modal submit workflow
node, including input validation, job ID generation, and status simulation.
"""

import json
import pytest

from psn_nodes.gen.psn_modal_submit_workflow import (
    PSN_Modal_Submit_Workflow,
    _validate_workflow_json,
    _validate_modal_env,
    _validate_gpu_type,
    _validate_timeout_sec,
    _generate_job_id,
    _simulate_submission,
    ALLOWED_GPU_TYPES,
    ALLOWED_MODAL_ENVS,
)


class TestPSNModalSubmitWorkflow:
    """Test suite for PSN_Modal_Submit_Workflow node."""
    
    def test_valid_inputs_returns_completed_status(self):
        """Test that valid inputs return a job_id and 'completed' status."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": [], "links": []})
        job_id, status = node.run(workflow_json, "prod", "A100", 300)
        
        assert job_id.startswith("modal-job-")
        assert len(job_id) == len("modal-job-") + 16
        assert status == "completed"
    
    def test_invalid_json_returns_failed_status(self):
        """Test that invalid JSON returns empty job_id and 'failed' status."""
        node = PSN_Modal_Submit_Workflow()
        job_id, status = node.run("not valid json", "prod", "A100", 300)
        
        assert job_id == ""
        assert status == "failed"
    
    def test_empty_workflow_json_returns_failed(self):
        """Test that empty workflow_json returns failed status."""
        node = PSN_Modal_Submit_Workflow()
        job_id, status = node.run("", "prod", "A100", 300)
        
        assert job_id == ""
        assert status == "failed"
    
    def test_invalid_modal_env_returns_failed(self):
        """Test that invalid modal_env returns failed status."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": []})
        job_id, status = node.run(workflow_json, "invalid_env", "A100", 300)
        
        assert job_id == ""
        assert status == "failed"
    
    def test_invalid_gpu_type_returns_failed(self):
        """Test that invalid gpu_type returns failed status."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": []})
        job_id, status = node.run(workflow_json, "prod", "V100", 300)
        
        assert job_id == ""
        assert status == "failed"
    
    def test_invalid_timeout_returns_failed(self):
        """Test that invalid timeout_sec returns failed status."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": []})
        
        # Zero timeout
        job_id, status = node.run(workflow_json, "prod", "A100", 0)
        assert job_id == ""
        assert status == "failed"
        
        # Negative timeout
        job_id, status = node.run(workflow_json, "prod", "A100", -10)
        assert job_id == ""
        assert status == "failed"
        
        # Timeout too large
        job_id, status = node.run(workflow_json, "prod", "A100", 100000)
        assert job_id == ""
        assert status == "failed"
    
    def test_job_id_is_deterministic(self):
        """Test that the same inputs always produce the same job_id."""
        workflow_json = json.dumps({"nodes": [{"id": 1}]})
        job_id1 = _generate_job_id(workflow_json, "prod", "A100", 300)
        job_id2 = _generate_job_id(workflow_json, "prod", "A100", 300)
        
        assert job_id1 == job_id2
    
    def test_job_id_changes_with_different_inputs(self):
        """Test that different inputs produce different job_ids."""
        workflow_json1 = json.dumps({"nodes": [{"id": 1}]})
        workflow_json2 = json.dumps({"nodes": [{"id": 2}]})
        
        job_id1 = _generate_job_id(workflow_json1, "prod", "A100", 300)
        job_id2 = _generate_job_id(workflow_json2, "prod", "A100", 300)
        
        assert job_id1 != job_id2
    
    def test_all_valid_gpu_types_accepted(self):
        """Test that all allowed GPU types are accepted."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": []})
        
        for gpu_type in ALLOWED_GPU_TYPES:
            job_id, status = node.run(workflow_json, "prod", gpu_type, 300)
            assert status == "completed", f"Failed for gpu_type: {gpu_type}"
            assert job_id.startswith("modal-job-")
    
    def test_all_valid_modal_envs_accepted(self):
        """Test that all allowed modal environments are accepted."""
        node = PSN_Modal_Submit_Workflow()
        workflow_json = json.dumps({"nodes": []})
        
        for env in ALLOWED_MODAL_ENVS:
            job_id, status = node.run(workflow_json, env, "A100", 300)
            assert status == "completed", f"Failed for modal_env: {env}"
            assert job_id.startswith("modal-job-")
    
    def test_validate_workflow_json_with_non_dict_json(self):
        """Test that JSON that parses to non-dict is rejected."""
        valid, err = _validate_workflow_json("[1, 2, 3]")
        assert not valid
        assert "JSON object" in err
        
        valid, err = _validate_workflow_json('"string"')
        assert not valid
        assert "JSON object" in err
    
    def test_validate_timeout_with_bool_rejected(self):
        """Test that boolean values are rejected for timeout_sec."""
        valid, err = _validate_timeout_sec(True)
        assert not valid
        assert "integer" in err
        
        valid, err = _validate_timeout_sec(False)
        assert not valid
        assert "integer" in err
    
    def test_workflow_json_must_be_string(self):
        """Test that non-string workflow_json is rejected."""
        valid, err = _validate_workflow_json(123)
        assert not valid
        assert "string" in err
        
        valid, err = _validate_workflow_json(None)
        assert not valid
        assert "string" in err
    
    def test_simulate_submission_returns_valid_status(self):
        """Test that _simulate_submission returns a valid status."""
        workflow_json = json.dumps({"nodes": []})
        job_id, status = _simulate_submission(workflow_json, "prod", "A100", 300)
        
        assert job_id.startswith("modal-job-")
        assert status in ["pending", "running", "completed", "failed"]
    
    def test_input_types_structure(self):
        """Test that INPUT_TYPES has the correct structure."""
        input_types = PSN_Modal_Submit_Workflow.INPUT_TYPES()
        
        assert "required" in input_types
        required = input_types["required"]
        
        assert "workflow_json" in required
        assert "modal_env" in required
        assert "gpu_type" in required
        assert "timeout_sec" in required
        
        # Check types
        assert required["workflow_json"][0] == "STRING"
        assert required["modal_env"][0] == ALLOWED_MODAL_ENVS
        assert required["gpu_type"][0] == ALLOWED_GPU_TYPES
        assert required["timeout_sec"][0] == "INT"
    
    def test_return_types_and_names(self):
        """Test that RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_Modal_Submit_Workflow.RETURN_TYPES == ("STRING", "STRING")
        assert PSN_Modal_Submit_Workflow.RETURN_NAMES == ("job_id", "status")
        assert PSN_Modal_Submit_Workflow.FUNCTION == "run"
        assert PSN_Modal_Submit_Workflow.CATEGORY == "ParametricStudio/Modal"
