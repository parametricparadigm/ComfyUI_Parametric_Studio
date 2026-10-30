"""PSN_Memory_Leak_Detector: pure-logic VRAM leak detector.

Analyzes a numeric history of VRAM usage (a list of numbers) to detect
monotonic increases without corresponding drops. This module performs no
GPU, torch, ComfyUI, network, file, or OS access; it only inspects plain
Python values (numbers, strings, JSON text) passed in as arguments.
"""

import json
import math

CAT = "ParametricStudio/Memory"


def _to_number(value):
    """Coerce a value to a finite float, or return None if invalid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except (ValueError, TypeError):
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _detect_leak(history, min_points=5, min_total_increase=0.0,
                 max_drop_fraction=0.15, min_drop_fraction=0.05):
    """Detect a leak from a numeric history.

    Returns (leak_detected, report) where report is a JSON string.
    """
    if not isinstance(history, (list, tuple)):
        return False, json.dumps({
            "error": "history_data must be a list of numbers",
            "leak_detected": False,
        })

    numbers = []
    for item in history:
        number = _to_number(item)
        if number is None:
            return False, json.dumps({
                "error": "history_data contains a non-numeric value",
                "leak_detected": False,
            })
        numbers.append(number)

    n = len(numbers)
    if n < min_points:
        return False, json.dumps({
            "error": "history_data has fewer than %d points" % min_points,
            "leak_detected": False,
            "points": n,
        })

    first = numbers[0]
    last = numbers[-1]
    total_increase = last - first

    # Count drops: a drop is a step where usage decreases by at least
    # min_drop_fraction of the current value (or a small absolute floor).
    drops = 0
    max_drop = 0.0
    for i in range(1, n):
        delta = numbers[i] - numbers[i - 1]
        if delta < 0:
            magnitude = -delta
            if magnitude >= max_drop:
                max_drop = magnitude
            # Consider it a meaningful drop if it's at least min_drop_fraction
            # of the previous value, or at least 1 unit.
            prev = numbers[i - 1]
            threshold = max(abs(prev) * min_drop_fraction, 1.0)
            if magnitude >= threshold:
                drops += 1

    # A leak is indicated by:
    # 1. Significant total increase (above min_total_increase)
    # 2. Few or no meaningful drops (drops == 0, or max_drop is small
    #    relative to total_increase)
    leak = False
    reasons = []

    if total_increase > min_total_increase:
        reasons.append("total increase of %.2f exceeds threshold %.2f"
                       % (total_increase, min_total_increase))
        # Check if drops are negligible relative to the increase
        if drops == 0:
            reasons.append("no meaningful drops detected")
            leak = True
        else:
            # If the largest drop is less than max_drop_fraction of the
            # total increase, the drops are not "corresponding"
            if max_drop < max_drop_fraction * total_increase:
                reasons.append("largest drop (%.2f) is less than %.0f%% of total increase"
                               % (max_drop, max_drop_fraction * 100))
                leak = True
            else:
                reasons.append("drops are significant relative to increase; not a leak")
    else:
        reasons.append("total increase of %.2f does not exceed threshold %.2f"
                       % (total_increase, min_total_increase))

    report = json.dumps({
        "leak_detected": leak,
        "points": n,
        "first": first,
        "last": last,
        "total_increase": total_increase,
        "drops": drops,
        "max_drop": max_drop,
        "reasons": reasons,
    })
    return leak, report


class PSN_Memory_Leak_Detector:
    """Detects VRAM leaks from a numeric usage history."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "history_data": ("LIST", {"default": []}),
            },
            "optional": {
                "min_points": ("INT", {"default": 5, "min": 2, "max": 10000}),
                "min_total_increase": ("FLOAT", {"default": 100.0, "min": 0.0, "max": 1e9, "step": 1.0}),
                "max_drop_fraction": ("FLOAT", {"default": 0.15, "min": 0.0, "max": 1.0, "step": 0.01}),
                "min_drop_fraction": ("FLOAT", {"default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("leak_detected", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, history_data, min_points=5, min_total_increase=100.0,
            max_drop_fraction=0.15, min_drop_fraction=0.05):
        leak, report = _detect_leak(
            history_data,
            min_points=min_points,
            min_total_increase=min_total_increase,
            max_drop_fraction=max_drop_fraction,
            min_drop_fraction=min_drop_fraction,
        )
        return (leak, report)


NODE_CLASS_MAPPINGS = {
    "PSN_Memory_Leak_Detector": PSN_Memory_Leak_Detector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Memory_Leak_Detector": "PSN Memory Leak Detector",
}
