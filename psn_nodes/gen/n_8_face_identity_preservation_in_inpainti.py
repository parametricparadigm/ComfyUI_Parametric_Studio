"""
PSN_Face_Preserve_Inpaint: Pure-logic planning and validation for face identity preservation in inpainting.

This module implements the secure, pure-Python portion of the face identity preservation node.
It does NOT perform actual face detection, embedding extraction, or image inpainting (which require
torch, insightface, and GPU). Instead, it:

1. Validates the face model path against an allow-list of known InsightFace model names.
2. Validates identity_strength is within [0.0, 1.0].
3. Computes a face-region overlap heuristic from the mask (represented as a 2D list of 0/1 values)
   to determine whether the mask intersects a typical face bounding box region.
4. Produces a structured plan (dict) describing how the inpainting should be guided to preserve
   identity, including whether identity constraint is active, the effective strength, and a reason.

All functions take plain values (numbers, strings, lists) and return plain values (dicts, strings,
booleans). No file I/O, no network, no subprocess, no torch, no comfy imports.
"""

from psn import expr, orchestration as _orch

CAT = "ParametricStudio/FaceIdentity"

# Allow-list of known InsightFace model identifiers (pure string matching, no file access)
_KNOWN_FACE_MODELS = frozenset({
    "buffalo_l",
    "buffalo_m",
    "buffalo_s",
    "antelopev2",
    "w600k_r50",
    "w600k_r100",
    "glint360k_r50",
    "glint360k_r100",
})

# Default face bounding box as a fraction of image dimensions (centered, typical portrait)
# (x_min_frac, y_min_frac, x_max_frac, y_max_frac)
_DEFAULT_FACE_BOX = (0.25, 0.15, 0.75, 0.65)


def _validate_face_model(face_model: str) -> tuple:
    """
    Validate the face model identifier against the allow-list.
    Returns (is_valid: bool, reason: str).
    """
    if not isinstance(face_model, str):
        return (False, "face_model must be a string")
    stripped = face_model.strip().lower()
    if not stripped:
        return (False, "face_model must not be empty")
    if stripped in _KNOWN_FACE_MODELS:
        return (True, "valid model")
    return (False, f"face_model '{face_model}' is not in the allow-list of known InsightFace models")


def _validate_identity_strength(identity_strength: float) -> tuple:
    """
    Validate identity_strength is a number in [0.0, 1.0].
    Returns (is_valid: bool, clamped_value: float, reason: str).
    """
    if not isinstance(identity_strength, (int, float)):
        return (False, 0.0, "identity_strength must be a number")
    val = float(identity_strength)
    if val < 0.0:
        return (True, 0.0, "identity_strength clamped to 0.0 (was below 0.0)")
    if val > 1.0:
        return (True, 1.0, "identity_strength clamped to 1.0 (was above 1.0)")
    return (True, val, "identity_strength valid")


def _compute_mask_face_overlap(mask: list, face_box=_DEFAULT_FACE_BOX) -> tuple:
    """
    Compute the fraction of mask pixels that fall within the default face bounding box region.
    mask is a 2D list of 0/1 values (1 = masked region).
    Returns (overlap_fraction: float, mask_has_content: bool).
    """
    if not isinstance(mask, list) or len(mask) == 0:
        return (0.0, False)
    if not all(isinstance(row, list) for row in mask):
        return (0.0, False)
    height = len(mask)
    if height == 0:
        return (0.0, False)
    width = len(mask[0])
    if width == 0:
        return (0.0, False)

    x_min_frac, y_min_frac, x_max_frac, y_max_frac = face_box
    x_min = int(x_min_frac * width)
    x_max = int(x_max_frac * width)
    y_min = int(y_min_frac * height)
    y_max = int(y_max_frac * height)

    total_masked = 0
    masked_in_face = 0
    for y in range(height):
        for x in range(width):
            if mask[y][x] == 1:
                total_masked += 1
                if y_min <= y < y_max and x_min <= x < x_max:
                    masked_in_face += 1

    if total_masked == 0:
        return (0.0, False)
    overlap = masked_in_face / total_masked
    return (overlap, True)


def _build_plan(face_model: str, identity_strength: float, mask: list) -> dict:
    """
    Build the inpainting plan dict based on validated inputs.
    """
    model_valid, model_reason = _validate_face_model(face_model)
    strength_valid, clamped_strength, strength_reason = _validate_identity_strength(identity_strength)
    overlap, has_mask = _compute_mask_face_overlap(mask)

    # Identity constraint is active if:
    # - model is valid
    # - strength > 0
    # - mask has content
    # - mask overlaps face region (overlap > 0)
    identity_active = (
        model_valid
        and clamped_strength > 0.0
        and has_mask
        and overlap > 0.0
    )

    if not model_valid:
        reason = f"Identity preservation disabled: {model_reason}"
    elif not has_mask:
        reason = "Identity preservation disabled: mask is empty or invalid"
    elif overlap == 0.0:
        reason = "Identity preservation disabled: mask does not overlap face region"
    elif clamped_strength == 0.0:
        reason = "Identity preservation disabled: identity_strength is 0.0"
    else:
        reason = (
            f"Identity preservation active: model='{face_model.strip().lower()}', "
            f"strength={clamped_strength:.3f}, face_overlap={overlap:.3f}"
        )

    plan = {
        "face_model": face_model.strip().lower() if isinstance(face_model, str) else "",
        "identity_strength": clamped_strength,
        "face_overlap": round(overlap, 6),
        "identity_active": identity_active,
        "reason": reason,
        "model_valid": model_valid,
        "mask_has_content": has_mask,
    }
    return plan


class PSN_Face_Preserve_Inpaint:
    """
    Plan and validate face identity preservation for inpainting.

    Inputs:
        face_model (STRING): Identifier of the InsightFace model (must be in allow-list).
        identity_strength (FLOAT): 0.0 to 1.0, how strongly to preserve identity.
        mask (STRING): JSON-encoded 2D list of 0/1 values representing the inpaint mask.

    Outputs:
        plan (STRING): JSON-encoded dict with the inpainting plan.
        identity_active (BOOLEAN): Whether identity constraint is active.
        reason (STRING): Human-readable explanation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "face_model": ("STRING", {"default": "buffalo_l", "multiline": False}),
                "identity_strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01}),
                "mask": ("STRING", {"default": "[]", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("plan", "identity_active", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, face_model: str, identity_strength: float, mask: str):
        # Parse mask from JSON string
        try:
            mask_data = expr.parse_json(mask) if hasattr(expr, "parse_json") else None
        except Exception:
            mask_data = None

        if mask_data is None:
            try:
                import json
                mask_data = json.loads(mask)
            except Exception:
                mask_data = []

        # Ensure mask_data is a 2D list of ints
        if not isinstance(mask_data, list):
            mask_data = []

        plan = _build_plan(face_model, identity_strength, mask_data)

        import json
        plan_json = json.dumps(plan, indent=2)

        return (plan_json, plan["identity_active"], plan["reason"])


NODE_CLASS_MAPPINGS = {
    "PSN_Face_Preserve_Inpaint": PSN_Face_Preserve_Inpaint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Face_Preserve_Inpaint": "Face Preserve Inpaint (Plan)",
}
