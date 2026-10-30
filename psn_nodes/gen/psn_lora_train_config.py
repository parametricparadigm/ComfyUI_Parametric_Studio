"""PSN LoRA training configuration nodes.

This module implements the pure-logic, secure-by-design portion of the
HunYuan LoRA training workflow. It does NOT execute kohya-ss, does NOT
touch the filesystem, and does NOT import torch or ComfyUI internals.

- PSN_LoRA_Param_Set validates hyperparameters (rank power-of-two, batch
  size capped at 4 for HunYuan VRAM safety, positive steps, etc.) and
  emits a plain configuration dictionary.
- PSN_LoRA_Train_HunYuan formats a job payload (JSON text) that a
  downstream studio backend would submit, and returns a deterministic
  placeholder path plus a synthetic loss curve description. It never
  opens sockets, files, or subprocesses.
"""

import json
import math

CAT = "ParametricStudio/Training"


def _is_power_of_two(value):
    """Return True if value is a positive integer power of two."""
    if not isinstance(value, int) or isinstance(value, bool):
        return False
    if value <= 0:
        return False
    return (value & (value - 1)) == 0


def _validate_params(learning_rate, batch_size, steps, rank, alpha, network_module):
    """Validate LoRA training parameters.

    Returns (ok, config_or_error_string).
    """
    # learning_rate
    if not isinstance(learning_rate, (int, float)) or isinstance(learning_rate, bool):
        return False, "learning_rate must be a number"
    if learning_rate <= 0:
        return False, "learning_rate must be positive"

    # batch_size
    if not isinstance(batch_size, int) or isinstance(batch_size, bool):
        return False, "batch_size must be an integer"
    if batch_size < 1:
        return False, "batch_size must be at least 1"
    if batch_size > 4:
        return False, "batch_size must be at most 4 for HunYuan VRAM safety"

    # steps
    if not isinstance(steps, int) or isinstance(steps, bool):
        return False, "steps must be an integer"
    if steps < 1:
        return False, "steps must be at least 1"

    # rank
    if not _is_power_of_two(rank):
        return False, "rank must be a positive power of two (e.g. 1, 2, 4, 8, 16, 32, 64)"

    # alpha
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool):
        return False, "alpha must be a number"
    if alpha <= 0:
        return False, "alpha must be positive"

    # network_module
    if not isinstance(network_module, str):
        return False, "network_module must be a string"
    allowed_modules = {"lora", "locon", "lycoris"}
    if network_module not in allowed_modules:
        return False, "network_module must be one of: " + ", ".join(sorted(allowed_modules))

    config = {
        "learning_rate": float(learning_rate),
        "batch_size": int(batch_size),
        "steps": int(steps),
        "rank": int(rank),
        "alpha": float(alpha),
        "network_module": network_module,
        "model": "hunyuan",
        "output_format": "safetensors",
    }
    return True, config


class PSN_LoRA_Param_Set:
    """Validates LoRA training hyperparameters and emits a config dict."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "learning_rate": ("FLOAT", {"default": 1e-4, "min": 1e-8, "max": 1e-1, "step": 1e-6}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4}),
                "steps": ("INT", {"default": 1000, "min": 1, "max": 100000}),
                "rank": ("INT", {"default": 16, "min": 1, "max": 256}),
                "alpha": ("FLOAT", {"default": 16.0, "min": 0.001, "max": 256.0, "step": 0.001}),
                "network_module": (["lora", "locon", "lycoris"],),
            }
        }

    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("config", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, learning_rate, batch_size, steps, rank, alpha, network_module):
        ok, result = _validate_params(learning_rate, batch_size, steps, rank, alpha, network_module)
        if ok:
            return (result, "ok")
        return ({}, result)


class PSN_LoRA_Train_HunYuan:
    """Formats a HunYuan LoRA training job payload.

    This node does NOT execute training. It constructs a JSON payload
    that a studio backend would use to submit the kohya-ss script, and
    returns a deterministic placeholder path and a synthetic loss curve
    description. No file, network, or subprocess access is performed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("DICT",),
                "base_model_path": ("STRING", {"default": "/models/hunyuan-diffusion-v1.2"}),
                "output_dir": ("STRING", {"default": "/outputs/lora"}),
            },
            "optional": {
                "dataset": ("DATASET",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("lora_path", "loss_curve", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, config, base_model_path, output_dir, dataset=None):
        # Validate config is a dict with required keys
        if not isinstance(config, dict):
            return ("", "", "error: config must be a dict")

        required_keys = {"learning_rate", "batch_size", "steps", "rank", "alpha", "network_module"}
        missing = required_keys - set(config.keys())
        if missing:
            return ("", "", "error: config missing keys: " + ", ".join(sorted(missing)))

        # Re-validate core constraints
        ok, _ = _validate_params(
            config.get("learning_rate"),
            config.get("batch_size"),
            config.get("steps"),
            config.get("rank"),
            config.get("alpha"),
            config.get("network_module"),
        )
        if not ok:
            return ("", "", "error: config validation failed")

        # Build job payload
        job_payload = {
            "script": "train_network.py",
            "model": "hunyuan",
            "base_model_path": base_model_path,
            "output_dir": output_dir,
            "params": {
                "learning_rate": config["learning_rate"],
                "batch_size": config["batch_size"],
                "steps": config["steps"],
                "rank": config["rank"],
                "alpha": config["alpha"],
                "network_module": config["network_module"],
            },
            "output_format": "safetensors",
        }

        # Deterministic placeholder path
        lora_filename = "hunyuan_lora_rank{}_step{}.safetensors".format(
            config["rank"], config["steps"]
        )
        lora_path = output_dir.rstrip("/") + "/" + lora_filename

        # Synthetic loss curve description (no actual training)
        loss_curve = json.dumps({
            "type": "synthetic",
            "note": "No training executed. This is a placeholder loss curve.",
            "steps": config["steps"],
            "initial_loss": 1.0,
            "final_loss": 0.1,
        })

        status = "payload_ready"
        return (lora_path, loss_curve, status)


NODE_CLASS_MAPPINGS = {
    "PSN_LoRA_Param_Set": PSN_LoRA_Param_Set,
    "PSN_LoRA_Train_HunYuan": PSN_LoRA_Train_HunYuan,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LoRA_Param_Set": "PSN LoRA Param Set",
    "PSN_LoRA_Train_HunYuan": "PSN LoRA Train HunYuan",
}
