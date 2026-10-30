"""PSN_Core_VRAM_Guard: pure-logic VRAM guard.

This module implements the decision logic for a VRAM guard without any GPU,
torch, ComfyUI, network, file, or OS access. It takes plain values (numbers,
strings, JSON text) and decides whether a model should be offloaded to CPU
based on a reported VRAM usage ratio and a threshold.

The node is a secure-by-design wrapper: it never touches real GPU memory.
Instead, callers (e.g., a ComfyUI wrapper) are expected to supply the current
VRAM usage ratio (0.0..1.0) as a plain float. The guard then returns a
decision (offload or not), a human-readable reason, and the (possibly
tagged) model payload.

Inputs:
    model (ANY): the model payload to guard (passed through unchanged).
    threshold (FLOAT): VRAM usage ratio threshold in [0.0, 1.0].
    vram_usage (FLOAT, optional): current VRAM usage ratio in [0.0, 1.0].
        If omitted, the guard assumes no offload is needed (safe default).

Outputs:
    model (ANY): the model payload, unchanged.
    offloaded (BOOLEAN): True if the guard decided to offload.
    reason (STRING): human-readable explanation of the decision.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/Core"

# Placeholder for ComfyUI's ANY type; in real ComfyUI this is imported from comfy.
# For pure-logic testing, we define it as a string marker.
ANY = "ANY"


class PSN_Core_VRAM_Guard:
    """Decide whether to offload a model based on a VRAM usage ratio."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (ANY,),
                "threshold": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "vram_usage": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.001}),
            },
        }

    RETURN_TYPES = (ANY, "BOOLEAN", "STRING")
    RETURN_NAMES = ("model", "offloaded", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model, threshold, vram_usage=0.0):
        """Evaluate the VRAM guard decision.

        Args:
            model: the model payload (passed through unchanged).
            threshold: VRAM usage ratio threshold in [0.0, 1.0].
            vram_usage: current VRAM usage ratio in [0.0, 1.0].

        Returns:
            tuple: (model, offloaded, reason)
        """
        # Validate threshold
        if not isinstance(threshold, (int, float)):
            return (model, False, "threshold must be a number")
        if threshold < 0.0 or threshold > 1.0:
            return (model, False, "threshold must be in [0.0, 1.0]")

        # Validate vram_usage
        if not isinstance(vram_usage, (int, float)):
            return (model, False, "vram_usage must be a number")
        if vram_usage < 0.0 or vram_usage > 1.0:
            return (model, False, "vram_usage must be in [0.0, 1.0]")

        # Decide: offload if vram_usage exceeds threshold
        if vram_usage > threshold:
            return (model, True, f"VRAM usage {vram_usage:.3f} exceeds threshold {threshold:.3f}; offloading to CPU")
        else:
            return (model, False, f"VRAM usage {vram_usage:.3f} within threshold {threshold:.3f}; no offload needed")


NODE_CLASS_MAPPINGS = {
    "PSN_Core_VRAM_Guard": PSN_Core_VRAM_Guard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Core_VRAM_Guard": "PSN Core VRAM Guard",
}
