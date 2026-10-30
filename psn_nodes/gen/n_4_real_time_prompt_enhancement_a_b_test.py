"""
Real-Time Prompt Enhancement A/B Test nodes.

This module provides pure-logic nodes for selecting between original and
enhanced prompts (A/B testing) and for preparing a deterministic generation
request payload.

Because this environment cannot access GPU/torch/ComfyUI internals, the
`PSN_RealTime_A_B_Generator` node does NOT perform actual image generation.
Instead, it validates the generation parameters and returns a deterministic
JSON payload that represents the generation request. This allows the A/B
testing logic to be tested and verified without requiring a GPU.

The `PSN_Prompt_Enhancer_Interface` node selects the active prompt based on
a boolean toggle.
"""

import json
import hashlib

CAT = "ParametricStudio/RealTimeABTest"

# Allowed prompt sources
ALLOWED_SOURCES = ("original", "enhanced")


class PSN_Prompt_Enhancer_Interface:
    """
    Selects either the original or enhanced prompt based on the boolean toggle.
    Outputs the selected prompt and a label indicating which one is active.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_prompt": ("STRING", {"default": "", "multiline": True}),
                "enhanced_prompt": ("STRING", {"default": "", "multiline": True}),
                "toggle": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("active_prompt", "prompt_source")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, original_prompt, enhanced_prompt, toggle):
        if toggle:
            active = enhanced_prompt
            source = "enhanced"
        else:
            active = original_prompt
            source = "original"
        return (active, source)


class PSN_RealTime_A_B_Generator:
    """
    Validates generation parameters and returns a deterministic JSON payload
    representing the generation request. This is a pure-logic stand-in for
    actual GPU image generation, allowing A/B testing logic to be verified
    without a GPU.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "active_prompt": ("STRING", {"default": "", "multiline": True}),
                "prompt_source": ("STRING", {"default": "original"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 1000}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0, "max": 100.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("payload", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, active_prompt, prompt_source, seed, steps, cfg):
        # Validate prompt_source
        if prompt_source not in ALLOWED_SOURCES:
            return (json.dumps({"error": f"Invalid prompt_source: {prompt_source}"}), "error")

        # Validate steps
        if steps < 1 or steps > 1000:
            return (json.dumps({"error": f"Invalid steps: {steps}"}), "error")

        # Validate cfg
        if cfg < 0.0 or cfg > 100.0:
            return (json.dumps({"error": f"Invalid cfg: {cfg}"}), "error")

        # Validate seed
        if seed < 0 or seed > 2**32 - 1:
            return (json.dumps({"error": f"Invalid seed: {seed}"}), "error")

        # Build deterministic payload
        payload = {
            "prompt": active_prompt,
            "source": prompt_source,
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
        }

        # Compute a deterministic hash for verification
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        payload["hash"] = payload_hash

        return (json.dumps(payload), "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Enhancer_Interface": PSN_Prompt_Enhancer_Interface,
    "PSN_RealTime_A_B_Generator": PSN_RealTime_A_B_Generator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Enhancer_Interface": "Prompt Enhancer Interface",
    "PSN_RealTime_A_B_Generator": "Real-Time A/B Generator",
}
