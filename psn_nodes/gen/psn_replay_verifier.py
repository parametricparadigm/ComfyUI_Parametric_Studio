"""PSN_Replay_Verifier: pure-logic determinism check for ComfyUI pipelines.

This module implements the secure, pure-Python part of a replay verifier.
Because the spec requires hashing an IMAGE tensor (which needs torch/GPU),
this node operates on a *serialized* representation of the image data
(passed as a plain string, e.g. base64 or hex of the raw bytes) rather than
a torch tensor. The caller (a ComfyUI wrapper or a test harness) is
responsible for converting the tensor to bytes and passing them here.

Inputs:
    image_data (STRING): serialized image bytes (hex or base64).
    reference_hash (STRING): the stored reference hash to compare against.
    run_id (STRING): identifier for the current run (used in the reason string).
    algorithm (STRING): "md5" or "sha256".

Outputs:
    image_data (STRING): the same serialized image data, passed through.
    match (BOOLEAN): True if the computed hash equals the reference hash.
    current_hash (STRING): the computed hash of the current image data.
    reason (STRING): human-readable explanation of the result.
"""

import hashlib
import base64
import binascii

CAT = "ParametricStudio/Replay"

_ALGORITHMS = ("md5", "sha256")


def _decode_image_data(image_data):
    """Decode a serialized image string into raw bytes.

    Accepts either hex-encoded or base64-encoded strings.
    Returns (bytes, error_string). If error_string is not None, decoding failed.
    """
    if not isinstance(image_data, str):
        return None, "image_data must be a string"
    if len(image_data) == 0:
        return None, "image_data is empty"

    # Try hex first
    try:
        return bytes.fromhex(image_data), None
    except (ValueError, binascii.Error):
        pass

    # Try base64
    try:
        return base64.b64decode(image_data, validate=True), None
    except (binascii.Error, ValueError):
        pass

    return None, "image_data is neither valid hex nor valid base64"


def _compute_hash(data, algorithm):
    """Compute the hash of the given bytes using the specified algorithm."""
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    else:
        raise ValueError("Unsupported algorithm: %s" % algorithm)


class PSN_Replay_Verifier:
    """Compares the hash of the current run's image data with a stored reference hash."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_data": ("STRING", {"default": "", "multiline": False}),
                "reference_hash": ("STRING", {"default": "", "multiline": False}),
                "run_id": ("STRING", {"default": "run_0", "multiline": False}),
                "algorithm": (list(_ALGORITHMS), {"default": "sha256"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("image_data", "match", "current_hash", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image_data, reference_hash, run_id, algorithm="sha256"):
        # Validate algorithm
        if algorithm not in _ALGORITHMS:
            return (image_data, False, "", "Invalid algorithm: %s" % algorithm)

        # Decode image data
        data, err = _decode_image_data(image_data)
        if err is not None:
            return (image_data, False, "", "Decode error [%s]: %s" % (run_id, err))

        # Compute current hash
        try:
            current_hash = _compute_hash(data, algorithm)
        except Exception as e:
            return (image_data, False, "", "Hash error [%s]: %s" % (run_id, str(e)))

        # Compare with reference
        ref = reference_hash.strip().lower() if isinstance(reference_hash, str) else ""
        cur = current_hash.lower()

        if ref == cur:
            reason = "Match [%s]: hash %s equals reference" % (run_id, current_hash[:16])
            match = True
        else:
            reason = "Mismatch [%s]: current=%s reference=%s" % (
                run_id, current_hash[:16], ref[:16] if ref else "(empty)"
            )
            match = False

        return (image_data, match, current_hash, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Replay_Verifier": PSN_Replay_Verifier,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Replay_Verifier": "PSN Replay Verifier",
}
