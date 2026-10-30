"""ParametricStudio - Text-to-Motion pipeline validation node.

This module implements a *validation* node for the text-to-motion pipeline.
Because the real MDM / Kimodo / MoMask diffusion models, the AnimoFlow Docker
containers and the motion model weights are NOT available
in this sandbox, the node implements the full *core* logic that torch + the
standard library can do:

* deterministic pseudo-diffusion sampling (seeded, reproducible),
* decoding the sampled latent into SMPL-like joint rotations + translations,
* conversion of the parameter stream into a BVH (XML) string,
* a small in-memory ``ANIMOFLOW_NPZ``-style dict (keys ``rotations`` and
  ``translations``) that mirrors what the real node would serialise to ``.npz``.

What is NOT implemented (needs heavy models / external services):
* real text encoding (transformers / CLIP),
* real MDM / Kimodo / MoMask diffusion sampling,
* real SMPL / SOMA decoding,
* AnimoFlow Docker communication,
* actual ``.npz`` file writing (we return an in-memory dict instead).
"""

import math
import xml.etree.ElementTree as ET

import torch

CAT = "ParametricStudio/Motion"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of joints in a simplified humanoid rig (Hips + 13 children).
NUM_JOINTS = 14

# Each joint has a 3D rotation (axis-angle) and a 3D translation.
ROT_DIM = 3
TRANS_DIM = 3

# Frames per second for the generated clip.
FPS = 30

# Supported model backends (the real models are not loaded here).
MODEL_TYPES = ("MDM", "Kimodo", "MoMask")

# Status codes.
STATUS_OK = 0
STATUS_BAD_PROMPT = 1
STATUS_BAD_DURATION = 2
STATUS_BAD_MODEL = 3
STATUS_BAD_SEED = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_prompt(prompt):
    """Return (ok, normalised_prompt)."""
    if not isinstance(prompt, str):
        return False, ""
    p = prompt.strip()
    if not p:
        return False, ""
    return True, p


def _validate_duration(duration):
    """Return (ok, frames)."""
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        return False, 0
    d = float(duration)
    if not math.isfinite(d) or d <= 0.0:
        return False, 0
    frames = max(1, int(round(d * FPS)))
    return True, frames


def _validate_model(model_type):
    if not isinstance(model_type, str) or model_type not in MODEL_TYPES:
        return False
    return True


def _validate_seed(seed):
    if isinstance(seed, bool) or not isinstance(seed, int):
        return False
    if seed < 0:
        return False
    return True


def _pseudo_diffusion_sample(seed, frames, model_type):
    """Deterministic pseudo-diffusion: produce a motion latent tensor.

    In the real pipeline this would be the output of the MDM / Kimodo /
    MoMask diffusion process conditioned on the encoded text.  Here we use a
    seeded ``torch.Generator`` so that the same (seed, frames, model_type)
    always yields the same latent, which is enough to validate the rest of
    the pipeline (decoding, BVH conversion, status codes).

    Returns a tensor of shape [frames, NUM_JOINTS, ROT_DIM + TRANS_DIM].
    """
    gen = torch.Generator(device="cpu")
    gen.manual_seed(seed)

    # A small per-model offset so different model_type values give different
    # (but still deterministic) latents.
    model_offset = MODEL_TYPES.index(model_type)

    latent = torch.randn(frames, NUM_JOINTS, ROT_DIM + TRANS_DIM, generator=gen)
    # Scale down to a plausible joint-parameter range (radians / metres).
    latent = latent * 0.25 + model_offset * 0.01
    return latent


def _decode_latent(latent):
    """Split the latent into rotations and translations tensors.

    Returns (rotations, translations) each of shape [frames, NUM_JOINTS, 3].
    """
    rotations = latent[:, :, :ROT_DIM].clone()
    translations = latent[:, :, ROT_DIM:ROT_DIM + TRANS_DIM].clone()
    return rotations, translations


def _build_bvh_string(rotations, translations, fps=FPS):
    """Build a BVH (XML) string from joint rotations and translations.

    The BVH format is a text-based motion-capture format.  We produce a
    minimal but structurally valid BVH file with a Hips root joint and
    child joints, plus a MOTION section with frame data.

    Returns a string.
    """
    frames = rotations.shape[0]
    joints = rotations.shape[1]

    lines = []
    lines.append("HIERARCHY")
    lines.append("Root Hips")
    lines.append("{")
    lines.append("  OFFSET 0.0 0.0 0.0")
    lines.append("  CHANNELS 6 Zrotation Xposition Yposition Zposition Xrotation Yrotation")

    # Child joints
    for j in range(1, joints):
        lines.append("  Joint Joint_%d" % j)
        lines.append("  {")
        lines.append("    OFFSET 0.0 0.0 0.0")
        lines.append("    CHANNELS 3 Zrotation Xrotation Yrotation")
        lines.append("  }")

    lines.append("}")
    lines.append("")
    lines.append("MOTION")
    lines.append("Frames: %d" % frames)
    lines.append("Frame Time: %.6f" % (1.0 / fps))

    # Frame data: for each frame, Hips has 6 channels (Zrot, Xpos, Ypos, Zpos, Xrot, Yrot)
    # and each child joint has 3 channels (Zrot, Xrot, Yrot).
    for f in range(frames):
        vals = []
        # Hips: Zrotation, Xposition, Yposition, Zposition, Xrotation, Yrotation
        vals.append(rotations[f, 0, 2].item())  # Zrotation
        vals.append(translations[f, 0, 0].item())  # Xposition
        vals.append(translations[f, 0, 1].item())  # Yposition
        vals.append(translations[f, 0, 2].item())  # Zposition
        vals.append(rotations[f, 0, 0].item())  # Xrotation
        vals.append(rotations[f, 0, 1].item())  # Yrotation
        # Child joints: Zrotation, Xrotation, Yrotation
        for j in range(1, joints):
            vals.append(rotations[f, j, 2].item())
            vals.append(rotations[f, j, 0].item())
            vals.append(rotations[f, j, 1].item())
        lines.append(" ".join("%.6f" % v for v in vals))

    return "\n".join(lines) + "\n"


def _make_animoflow_npz(rotations, translations):
    """Create an in-memory dict that mirrors the keys of an ANIMOFLOW_NPZ.

    In the real pipeline this would be a ``numpy.savez`` file.  Here we return
    a plain dict with tensor values so the rest of the ComfyUI graph can
    consume it without file I/O.
    """
    return {
        "rotations": rotations.clone(),
        "translations": translations.clone(),
    }


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PSN_TextToMotion_Generate:
    """Validate the text-to-motion pipeline: prompt -> pseudo-diffusion ->
    joint parameters -> BVH string + in-memory NPZ dict + status code.

    NOTE: This is a *validation* node.  The real MDM / Kimodo / MoMask models,
    text encoders, SMPL decoder and AnimoFlow Docker backend are NOT used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "a person walking forward", "multiline": True}),
                "duration": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 60.0, "step": 0.1}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 2 ** 32 - 1}),
                "model_type": (MODEL_TYPES,),
            }
        }

    RETURN_TYPES = ("ANIMOFLOW_NPZ", "ANIMOFLOW_BVH", "INT")
    RETURN_NAMES = ("motion_data", "rigged_animation", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, duration, seed, model_type):
        # --- validate inputs ------------------------------------------------
        ok, norm_prompt = _validate_prompt(prompt)
        if not ok:
            return ({"error": "bad prompt"}, "", STATUS_BAD_PROMPT)

        ok, frames = _validate_duration(duration)
        if not ok:
            return ({"error": "bad duration"}, "", STATUS_BAD_DURATION)

        if not _validate_model(model_type):
            return ({"error": "bad model_type"}, "", STATUS_BAD_MODEL)

        if not _validate_seed(seed):
            return ({"error": "bad seed"}, "", STATUS_BAD_SEED)

        # --- pseudo-diffusion sampling --------------------------------------
        latent = _pseudo_diffusion_sample(seed, frames, model_type)

        # --- decode to joint parameters -------------------------------------
        rotations, translations = _decode_latent(latent)

        # --- build outputs ---------------------------------------------------
        motion_data = _make_animoflow_npz(rotations, translations)
        bvh_string = _build_bvh_string(rotations, translations, FPS)

        return (motion_data, bvh_string, STATUS_OK)


# ---------------------------------------------------------------------------
# ComfyUI registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_TextToMotion_Generate": PSN_TextToMotion_Generate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_TextToMotion_Generate": "Text-to-Motion Generate (Validation)",
}
