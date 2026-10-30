"""
PSN Drift Correction Loop (pure-logic core).

This module implements the *decision* and *planning* logic for identity-drift
detection and face-repair triggering in multi-frame video generation.

Because the full pipeline requires GPU tensors, face-embedding models
(insightface / buffalo_l), and restoration models (GFPGAN / CodeFormer),
this module exposes ONLY the pure-Python, secure-by-design parts:

  * PSN_IdentityDriftDetector  -- compares per-frame similarity scores against
    a threshold and produces a drift mask + per-frame scores.
  * PSN_FaceRepairTrigger      -- validates the repair plan (which frames need
    repair, blend parameters, model selection) and returns a structured
    repair-plan dict.  No actual image manipulation is performed.

All functions accept plain Python values (lists of floats, strings, numbers)
and return plain Python values.  No torch, no file I/O, no network, no
subprocess, no eval/exec.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAT = "ParametricStudio/DriftCorrection"

_VALID_REPAIR_MODELS = ("internal_gfpgan", "internal_codeformer", "external")
_VALID_BLEND_MODES = ("semantic", "feather", "hard")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_scores(scores: Any) -> List[float]:
    """Coerce *scores* to a list of finite floats; raise on bad input."""
    if scores is None:
        raise ValueError("scores must be a list of floats, got None")
    if isinstance(scores, (int, float)):
        scores = [scores]
    if not isinstance(scores, (list, tuple)):
        raise TypeError(f"scores must be a list or tuple, got {type(scores).__name__}")
    out: List[float] = []
    for i, s in enumerate(scores):
        if isinstance(s, bool) or not isinstance(s, (int, float)):
            raise TypeError(f"scores[{i}] must be a number, got {type(s).__name__}")
        v = float(s)
        if not math.isfinite(v):
            raise ValueError(f"scores[{i}] is not finite: {v}")
        out.append(v)
    return out


def _validate_threshold(threshold: Any) -> float:
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise TypeError(f"threshold must be a number, got {type(threshold).__name__}")
    t = float(threshold)
    if not math.isfinite(t):
        raise ValueError(f"threshold is not finite: {t}")
    if t < 0.0 or t > 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {t}")
    return t


def _validate_blend_mode(mode: Any) -> str:
    if not isinstance(mode, str):
        raise TypeError(f"blend_mode must be a string, got {type(mode).__name__}")
    m = mode.strip().lower()
    if m not in _VALID_BLEND_MODES:
        raise ValueError(f"blend_mode must be one of {_VALID_BLEND_MODES}, got {mode!r}")
    return m


def _validate_repair_model(model: Any) -> str:
    if model is None:
        return "internal_gfpgan"
    if not isinstance(model, str):
        raise TypeError(f"repair_model must be a string or None, got {type(model).__name__}")
    m = model.strip().lower()
    if m not in _VALID_REPAIR_MODELS:
        raise ValueError(f"repair_model must be one of {_VALID_REPAIR_MODELS}, got {model!r}")
    return m


def _validate_feather_radius(radius: Any) -> float:
    if isinstance(radius, bool) or not isinstance(radius, (int, float)):
        raise TypeError(f"feather_radius must be a number, got {type(radius).__name__}")
    r = float(radius)
    if not math.isfinite(r) or r < 0.0:
        raise ValueError(f"feather_radius must be a non-negative finite number, got {r}")
    return r


def _validate_strength(strength: Any) -> float:
    if isinstance(strength, bool) or not isinstance(strength, (int, float)):
        raise TypeError(f"strength must be a number, got {type(strength).__name__}")
    s = float(strength)
    if not math.isfinite(s) or s < 0.0 or s > 1.0:
        raise ValueError(f"strength must be in [0, 1], got {s}")
    return s


# ---------------------------------------------------------------------------
# Node 1: PSN_IdentityDriftDetector
# ---------------------------------------------------------------------------

class PSN_IdentityDriftDetector:
    """
    Compare per-frame face-similarity scores against a reference threshold.

    In a full ComfyUI deployment the VIDEO and REFERENCE_FACE inputs would be
    IMAGE tensors processed by insightface to produce per-frame similarity
    scores.  This pure-logic node accepts those scores directly (as a JSON
    string or a list) and produces:

      * DRIFT_MASK  -- list of 0/1 floats (1 where drift detected)
      * DRIFT_SCORES -- the validated per-frame similarity scores
      * DRIFT_COUNT -- number of frames flagged as drifted
      * REASON      -- human-readable summary

    The VIDEO / REFERENCE_FACE inputs are accepted for interface compatibility
    but are not used in the pure-logic path (they would be IMAGE tensors in
    the full pipeline).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "drift_scores": ("STRING", {
                    "default": "[]",
                    "multiline": True,
                    "tooltip": "JSON list of per-frame similarity scores (0-1). "
                               "e.g. [0.92, 0.91, 0.45, 0.93, 0.88]",
                }),
                "drift_threshold": ("FLOAT", {
                    "default": 0.85,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001,
                }),
            },
            "optional": {
                "video": (None,),   # IMAGE in full pipeline; unused here
                "reference_face": (None,),  # IMAGE in full pipeline; unused here
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("drift_mask", "drift_scores", "drift_count", "reason")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(
        self,
        drift_scores: str,
        drift_threshold: float,
        video: Any = None,
        reference_face: Any = None,
    ) -> Tuple[List[float], List[float], int, str]:
        # Parse the JSON scores string
        raw = drift_scores.strip() if isinstance(drift_scores, str) else drift_scores
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"drift_scores is not valid JSON: {exc}") from exc
        else:
            parsed = raw

        scores = _validate_scores(parsed)
        threshold = _validate_threshold(drift_threshold)

        if len(scores) == 0:
            return ([], [], 0, "No frames provided; nothing to detect.")

        mask: List[float] = []
        for s in scores:
            mask.append(0.0 if s >= threshold else 1.0)

        count = sum(1 for m in mask if m == 1.0)
        reason = (
            f"{count}/{len(scores)} frame(s) below threshold {threshold:.3f}. "
            f"Min score: {min(scores):.4f}, Max score: {max(scores):.4f}."
        )
        return (mask, scores, count, reason)


# ---------------------------------------------------------------------------
# Node 2: PSN_FaceRepairTrigger
# ---------------------------------------------------------------------------

class PSN_FaceRepairTrigger:
    """
    Build a structured repair plan for frames flagged by the drift mask.

    In a full ComfyUI deployment this node would invoke GFPGAN / CodeFormer
    on the masked frames.  This pure-logic node validates all parameters and
    returns a JSON-serialisable repair-plan dict describing:

      * which frame indices need repair
      * the selected repair model
      * the blend mode and feather radius
      * the restoration strength
      * a summary string

    The VIDEO and DRIFT_MASK inputs are accepted for interface compatibility.
    DRIFT_MASK is expected as a JSON string (list of 0/1 floats) or a list.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "drift_mask": ("STRING", {
                    "default": "[]",
                    "multiline": True,
                    "tooltip": "JSON list of 0/1 floats from PSN_IdentityDriftDetector.",
                }),
                "repair_model": (list(_VALID_REPAIR_MODELS), {
                    "default": "internal_gfpgan",
                }),
                "blend_mode": (list(_VALID_BLEND_MODES), {
                    "default": "semantic",
                }),
                "feather_radius": ("FLOAT", {
                    "default": 8.0,
                    "min": 0.0,
                    "max": 256.0,
                    "step": 0.5,
                }),
                "strength": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                }),
            },
            "optional": {
                "video": (None,),   # IMAGE in full pipeline; unused here
            },
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("repair_plan_json", "frames_to_repair", "summary")
    FUNCTION = "run"
    CATEGORY = _CAT

    def run(
        self,
        drift_mask: str,
        repair_model: str,
        blend_mode: str,
        feather_radius: float,
        strength: float,
        video: Any = None,
    ) -> Tuple[str, int, str]:
        # Parse drift mask
        raw = drift_mask.strip() if isinstance(drift_mask, str) else drift_mask
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"drift_mask is not valid JSON: {exc}") from exc
        else:
            parsed = raw

        mask = _validate_scores(parsed)  # reuses numeric validation

        # Validate mask values are 0 or 1
        for i, m in enumerate(mask):
            if m not in (0.0, 1.0):
                raise ValueError(f"drift_mask[{i}] must be 0 or 1, got {m}")

        model = _validate_repair_model(repair_model)
        blend = _validate_blend_mode(blend_mode)
        radius = _validate_feather_radius(feather_radius)
        s = _validate_strength(strength)

        frames_to_repair = [i for i, m in enumerate(mask) if m == 1.0]

        plan: Dict[str, Any] = {
            "repair_model": model,
            "blend_mode": blend,
            "feather_radius": radius,
            "strength": s,
            "total_frames": len(mask),
            "frames_to_repair": frames_to_repair,
            "repair_count": len(frames_to_repair),
        }

        if len(frames_to_repair) == 0:
            summary = "No drift detected; no repair needed."
        else:
            summary = (
                f"Repairing {len(frames_to_repair)}/{len(mask)} frame(s) "
                f"with {model} ({blend} blend, feather={radius:.1f}, "
                f"strength={s:.2f})."
            )

        return (json.dumps(plan, indent=2), len(frames_to_repair), summary)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_IdentityDriftDetector": PSN_IdentityDriftDetector,
    "PSN_FaceRepairTrigger": PSN_FaceRepairTrigger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_IdentityDriftDetector": "PSN Identity Drift Detector",
    "PSN_FaceRepairTrigger": "PSN Face Repair Trigger",
}
