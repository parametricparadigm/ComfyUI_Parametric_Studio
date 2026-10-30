"""PSN_Quantization_Monitor: pure-logic VRAM savings and quality comparison.

This module implements the reporting logic for quantization monitoring without
any GPU, torch, or ComfyUI imports. It accepts plain numeric values (VRAM
usage in MB, quality scores) and computes:

- vram_savings: percentage of VRAM saved by the quantized model relative to
  the reference (full precision) model.
- quality_metric: a normalized comparison score between the quantized model's
  quality score and the reference model's quality score (0.0 to 1.0, where
  1.0 means identical quality).

All inputs are plain numbers (FLOAT) or strings (JSON text for optional
metadata). No file, network, subprocess, or torch access is performed.
"""

import json
import math

CAT = "ParametricStudio/Quantization"


def _safe_float(value, default=0.0):
    """Convert value to float safely; return default on failure."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return default
        return float(value)
    if isinstance(value, str):
        try:
            f = float(value)
            if math.isnan(f) or math.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default
    return default


def _clamp(value, lo, hi):
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


def compute_vram_savings(quantized_vram_mb, reference_vram_mb):
    """Compute percentage VRAM savings.

    Returns a float in [-100.0, 100.0]. Positive means savings (quantized
    uses less VRAM). Negative means the quantized model uses more VRAM.
    If reference_vram_mb is 0 or negative, returns 0.0.
    """
    q = _safe_float(quantized_vram_mb, 0.0)
    r = _safe_float(reference_vram_mb, 0.0)
    if r <= 0.0:
        return 0.0
    savings = ((r - q) / r) * 100.0
    return _clamp(savings, -100.0, 100.0)


def compute_quality_metric(quantized_score, reference_score):
    """Compute a normalized quality comparison score in [0.0, 1.0].

    If reference_score is 0, returns 1.0 if quantized_score is also 0,
    otherwise 0.0. The score is the ratio quantized/reference clamped to
    [0, 1] when both are non-negative. If either is negative, returns 0.0.
    """
    qs = _safe_float(quantized_score, 0.0)
    rs = _safe_float(reference_score, 0.0)
    if rs < 0.0 or qs < 0.0:
        return 0.0
    if rs == 0.0:
        return 1.0 if qs == 0.0 else 0.0
    ratio = qs / rs
    return _clamp(ratio, 0.0, 1.0)


def parse_metadata(json_text):
    """Parse optional JSON metadata string; return dict or empty dict."""
    if not json_text or not isinstance(json_text, str):
        return {}
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


class PSN_QuantizationMonitor:
    """Monitors VRAM savings and quality impact of quantization.

    Accepts plain numeric VRAM values (in MB) and optional quality scores.
    No model objects, torch tensors, or GPU access are used.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "quantized_vram_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
                "reference_vram_mb": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.1}),
            },
            "optional": {
                "quantized_quality_score": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "reference_quality_score": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e9, "step": 0.001}),
                "metadata_json": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("vram_savings", "quality_metric", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, quantized_vram_mb, reference_vram_mb,
            quantized_quality_score=None, reference_quality_score=None,
            metadata_json=None):
        savings = compute_vram_savings(quantized_vram_mb, reference_vram_mb)

        if quantized_quality_score is not None and reference_quality_score is not None:
            quality = compute_quality_metric(quantized_quality_score, reference_quality_score)
        else:
            quality = 0.0

        meta = parse_metadata(metadata_json)
        report_parts = [
            "vram_savings={:.2f}%".format(savings),
            "quality_metric={:.4f}".format(quality),
        ]
        if meta:
            for key in sorted(meta.keys()):
                report_parts.append("{}={}".format(key, meta[key]))
        report = "; ".join(report_parts)

        return (savings, quality, report)


NODE_CLASS_MAPPINGS = {
    "PSN_QuantizationMonitor": PSN_QuantizationMonitor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_QuantizationMonitor": "PSN Quantization Monitor",
}
