"""
PSN_ModelAwareScheduler: A pure-logic node that generates model-aware sigma schedules.

This node implements the core logic for selecting and generating sigma schedules
based on the model family (Krea2, Flux1, SD3). Since we cannot access GPU/torch
internals or model objects directly in this pure-Python environment, the node
accepts a `model_family` hint (COMBO) and generates the schedule parameters
(shift, start, end) and the resulting sigma list based on that family.

The actual tensor generation would happen in a ComfyUI environment with torch,
but here we return the sigma values as a list of floats, which can be converted
to a tensor by the caller.

Inputs:
- steps (INT): Number of sampling steps.
- model_family (COMBO): The model family to use for schedule selection.
- config (STRING, optional): JSON string with optional overrides for schedule parameters.

Outputs:
- sigmas (LIST): A list of sigma values for the given steps and model family.
- schedule_info (STRING): JSON string describing the schedule parameters used.
"""

import json
import math

# Model family options
MODEL_FAMILIES = ["Auto", "Krea2", "Flux1", "SD3"]

# Default schedule parameters for each model family
# Format: { "shift": float, "start": float, "end": float }
DEFAULT_SCHEDULES = {
    "Krea2": {"shift": 3.0, "start": 1.0, "end": 0.001},
    "Flux1": {"shift": 3.5, "start": 1.0, "end": 0.001},
    "SD3": {"shift": 2.5, "start": 1.0, "end": 0.001},
    "Auto": {"shift": 3.0, "start": 1.0, "end": 0.001},
}


def _generate_sigmas(steps, shift, start, end):
    """
    Generate a list of sigma values for the given steps and schedule parameters.
    
    Uses a simple linear interpolation in log-space between start and end,
    with a shift applied to adjust the distribution.
    
    Args:
        steps: Number of sampling steps.
        shift: Shift parameter to adjust the sigma distribution.
        start: Starting sigma value.
        end: Ending sigma value.
    
    Returns:
        A list of sigma values.
    """
    if steps <= 0:
        return []
    
    if steps == 1:
        return [start]
    
    # Generate linearly spaced values in log-space
    log_start = math.log(start)
    log_end = math.log(end)
    
    sigmas = []
    for i in range(steps):
        t = i / (steps - 1)
        log_sigma = log_start + t * (log_end - log_start)
        sigma = math.exp(log_sigma)
        
        # Apply shift: sigma_shifted = sigma / (1 + shift * (1 - sigma))
        # This is a common shift formula used in diffusion models
        if shift != 0:
            sigma = sigma / (1 + shift * (1 - sigma))
        
        sigmas.append(sigma)
    
    return sigmas


def _validate_config(config_json):
    """
    Validate and parse the optional config JSON string.
    
    Args:
        config_json: Optional JSON string with overrides for schedule parameters.
    
    Returns:
        A dict with validated parameters, or None if no config provided.
    """
    if not config_json or not isinstance(config_json, str):
        return None
    
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        return None
    
    if not isinstance(config, dict):
        return None
    
    # Validate and extract parameters
    result = {}
    
    if "shift" in config:
        try:
            shift = float(config["shift"])
            if shift < 0 or shift > 10:
                return None
            result["shift"] = shift
        except (ValueError, TypeError):
            return None
    
    if "start" in config:
        try:
            start = float(config["start"])
            if start <= 0 or start > 10:
                return None
            result["start"] = start
        except (ValueError, TypeError):
            return None
    
    if "end" in config:
        try:
            end = float(config["end"])
            if end <= 0 or end >= start if "start" in result else end <= 0 or end >= 10:
                return None
            result["end"] = end
        except (ValueError, TypeError):
            return None
    
    return result if result else None


class PSN_ModelAwareScheduler:
    """
    Generate model-aware sigma schedules for Krea2, Flux1, and SD3 models.
    
    This node selects the appropriate sigma schedule parameters based on the
    model family and generates the corresponding sigma values.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000, "step": 1}),
                "model_family": (MODEL_FAMILIES,),
            },
            "optional": {
                "config": ("STRING", {"default": "", "multiline": True}),
            },
        }
    
    RETURN_TYPES = ("LIST", "STRING")
    RETURN_NAMES = ("sigmas", "schedule_info")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Schedules"
    
    def run(self, steps, model_family, config=None):
        """
        Generate the sigma schedule for the given model family and steps.
        
        Args:
            steps: Number of sampling steps.
            model_family: The model family to use for schedule selection.
            config: Optional JSON string with overrides for schedule parameters.
        
        Returns:
            A tuple of (sigmas, schedule_info) where sigmas is a list of floats
            and schedule_info is a JSON string describing the parameters used.
        """
        # Validate steps
        if not isinstance(steps, int) or steps < 1:
            steps = 20
        
        # Get default schedule for the model family
        if model_family not in DEFAULT_SCHEDULES:
            model_family = "Auto"
        
        schedule = dict(DEFAULT_SCHEDULES[model_family])
        
        # Apply config overrides if provided
        config_overrides = _validate_config(config)
        if config_overrides:
            schedule.update(config_overrides)
        
        # Generate sigmas
        sigmas = _generate_sigmas(steps, schedule["shift"], schedule["start"], schedule["end"])
        
        # Create schedule info
        schedule_info = json.dumps({
            "model_family": model_family,
            "steps": steps,
            "shift": schedule["shift"],
            "start": schedule["start"],
            "end": schedule["end"],
            "num_sigmas": len(sigmas),
        })
        
        return (sigmas, schedule_info)


NODE_CLASS_MAPPINGS = {
    "PSN_ModelAwareScheduler": PSN_ModelAwareScheduler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_ModelAwareScheduler": "Model-Aware Sigma Scheduler",
}
