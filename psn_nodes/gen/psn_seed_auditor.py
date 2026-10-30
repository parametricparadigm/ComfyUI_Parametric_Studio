"""PSN_Seed_Auditor: Captures the effective seed used in a run and verifies it against an expected value.

This module implements a pure-logic ComfyUI custom node that audits seed values.
It logs the seed, optionally compares it against an expected value, and generates
a SHA256 hash of the seed + model name for unique run identification.

No GPU, torch, ComfyUI internals, network, file I/O, or subprocess usage.
Only pure Python standard library (hashlib, json) is used.
"""

import hashlib
import json

CAT = "ParametricStudio/Seed"


class PSN_Seed_Auditor:
    """Audits a seed value: logs it, optionally compares to expected, and hashes seed+model."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1, "step": 1}),
                "run_id": ("STRING", {"default": "run_001", "multiline": False}),
                "model_name": ("STRING", {"default": "sd_xl_base", "multiline": False}),
            },
            "optional": {
                "expected_seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1, "step": 1}),
            },
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("seed", "audit_result", "hash")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, seed, run_id, model_name, expected_seed=None):
        """
        Audit the seed value.

        Args:
            seed: The effective seed used in the run.
            run_id: Identifier for the run.
            model_name: Name of the model used (for hash generation).
            expected_seed: Optional expected seed to compare against.

        Returns:
            tuple: (seed, audit_result, hash)
                - seed: The input seed (passed through).
                - audit_result: JSON string with audit details.
                - hash: SHA256 hex digest of seed + model_name.
        """
        # Generate SHA256 hash of seed + model_name
        hash_input = f"{seed}:{model_name}"
        digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        # Build audit result
        audit = {
            "seed": seed,
            "run_id": run_id,
            "model_name": model_name,
            "hash": digest,
        }

        if expected_seed is not None:
            match = (seed == expected_seed)
            audit["expected_seed"] = expected_seed
            audit["match"] = match
            audit["status"] = "PASS" if match else "FAIL"
        else:
            audit["expected_seed"] = None
            audit["match"] = None
            audit["status"] = "NO_EXPECTED"

        audit_result = json.dumps(audit, sort_keys=True)

        return (seed, audit_result, digest)


NODE_CLASS_MAPPINGS = {
    "PSN_Seed_Auditor": PSN_Seed_Auditor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Seed_Auditor": "PSN Seed Auditor",
}
