"""
PSN_Modal_Submit_Workflow

This module implements the pure-logic, secure-by-design portion of a ComfyUI
custom node that would normally offload a sub-graph to a remote Modal GPU
instance.

Because the specification requires network access (Modal API, requests) and
external SDKs (modal), which are prohibited in this environment, this
implementation ONLY handles:
1. Validation of inputs (workflow_json, modal_env, gpu_type, timeout_sec).
2. Serialization/formatting of the payload that *would* be sent to Modal.
3. Simulation of job submission and status polling using deterministic,
   in-memory logic (no actual network calls).
4. Generation of a mock job_id and status based on input validity.

The node does NOT open sockets, make HTTP requests, or import torch/comfy/modal.
It returns a job_id and a status string as per the spec, but the "submission"
is simulated locally.

Inputs:
    workflow_json (STRING): JSON string representing the ComfyUI workflow.
    modal_env (STRING): Environment name for Modal (e.g., "prod", "dev").
    gpu_type (COMBO): One of ["A100", "H100", "L4"].
    timeout_sec (INT): Timeout in seconds for the job.

Outputs:
    job_id (STRING): A generated job identifier.
    status (STRING): One of ["pending", "running", "completed", "failed"].
"""

import json
import hashlib
import time
import uuid

# Allowed GPU types
ALLOWED_GPU_TYPES = ["A100", "H100", "L4"]

# Allowed statuses
ALLOWED_STATUSES = ["pending", "running", "completed", "failed"]

# Allowed modal environments (simple allow-list for security)
ALLOWED_MODAL_ENVS = ["prod", "dev", "staging", "test"]


def _validate_workflow_json(workflow_json: str) -> tuple[bool, str]:
    """
    Validate that workflow_json is a valid JSON string and represents a dict.
    Returns (is_valid, error_message).
    """
    if not isinstance(workflow_json, str):
        return False, "workflow_json must be a string"
    if not workflow_json.strip():
        return False, "workflow_json must not be empty"
    try:
        parsed = json.loads(workflow_json)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    if not isinstance(parsed, dict):
        return False, "workflow_json must parse to a JSON object (dict)"
    return True, ""


def _validate_modal_env(modal_env: str) -> tuple[bool, str]:
    """
    Validate that modal_env is in the allow-list.
    Returns (is_valid, error_message).
    """
    if not isinstance(modal_env, str):
        return False, "modal_env must be a string"
    if modal_env not in ALLOWED_MODAL_ENVS:
        return False, f"modal_env must be one of {ALLOWED_MODAL_ENVS}, got '{modal_env}'"
    return True, ""


def _validate_gpu_type(gpu_type: str) -> tuple[bool, str]:
    """
    Validate that gpu_type is in the allow-list.
    Returns (is_valid, error_message).
    """
    if not isinstance(gpu_type, str):
        return False, "gpu_type must be a string"
    if gpu_type not in ALLOWED_GPU_TYPES:
        return False, f"gpu_type must be one of {ALLOWED_GPU_TYPES}, got '{gpu_type}'"
    return True, ""


def _validate_timeout_sec(timeout_sec: int) -> tuple[bool, str]:
    """
    Validate that timeout_sec is a positive integer.
    Returns (is_valid, error_message).
    """
    if not isinstance(timeout_sec, int) or isinstance(timeout_sec, bool):
        return False, "timeout_sec must be an integer"
    if timeout_sec <= 0:
        return False, "timeout_sec must be positive"
    if timeout_sec > 86400:  # Max 24 hours
        return False, "timeout_sec must not exceed 86400 seconds"
    return True, ""


def _generate_job_id(workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> str:
    """
    Generate a deterministic job ID based on the inputs.
    Uses a hash of the inputs to create a unique but reproducible ID.
    """
    content = f"{workflow_json}|{modal_env}|{gpu_type}|{timeout_sec}"
    hash_obj = hashlib.sha256(content.encode("utf-8")).hexdigest()
    # Use first 16 chars of hash + a uuid suffix for uniqueness in real scenarios
    # For deterministic testing, we use just the hash prefix
    return f"modal-job-{hash_obj[:16]}"


def _simulate_submission(workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> tuple[str, str]:
    """
    Simulate submitting a job to Modal and polling for status.
    Returns (job_id, status).
    
    In a real implementation, this would:
    1. Serialize the workflow
    2. Send to Modal API
    3. Poll for completion
    
    Here, we simulate:
    - If the workflow is valid, the job is "completed" (simulating success)
    - The job_id is generated deterministically
    """
    job_id = _generate_job_id(workflow_json, modal_env, gpu_type, timeout_sec)
    
    # Simulate a successful completion for valid inputs
    # In a real scenario, this would depend on the actual Modal response
    status = "completed"
    
    return job_id, status


class PSN_Modal_Submit_Workflow:
    """
    ComfyUI custom node that simulates submitting a workflow to a Modal GPU instance.
    
    This is a pure-logic implementation that validates inputs and simulates
    the submission process without making actual network calls.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_json": ("STRING", {"default": "{}", "multiline": True}),
                "modal_env": (ALLOWED_MODAL_ENVS, {"default": "prod"}),
                "gpu_type": (ALLOWED_GPU_TYPES, {"default": "A100"}),
                "timeout_sec": ("INT", {"default": 300, "min": 1, "max": 86400, "step": 1}),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("job_id", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Modal"
    
    def run(self, workflow_json: str, modal_env: str, gpu_type: str, timeout_sec: int) -> tuple[str, str]:
        """
        Validate inputs and simulate Modal job submission.
        
        Args:
            workflow_json: JSON string of the ComfyUI workflow.
            modal_env: Modal environment name.
            gpu_type: GPU type to use.
            timeout_sec: Timeout in seconds.
            
        Returns:
            Tuple of (job_id, status).
        """
        # Validate all inputs
        valid, err = _validate_workflow_json(workflow_json)
        if not valid:
            return ("", "failed")
        
        valid, err = _validate_modal_env(modal_env)
        if not valid:
            return ("", "failed")
        
        valid, err = _validate_gpu_type(gpu_type)
        if not valid:
            return ("", "failed")
        
        valid, err = _validate_timeout_sec(timeout_sec)
        if not valid:
            return ("", "failed")
        
        # Simulate submission
        job_id, status = _simulate_submission(workflow_json, modal_env, gpu_type, timeout_sec)
        
        return (job_id, status)


NODE_CLASS_MAPPINGS = {
    "PSN_Modal_Submit_Workflow": PSN_Modal_Submit_Workflow,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Modal_Submit_Workflow": "PSN Modal Submit Workflow",
}
