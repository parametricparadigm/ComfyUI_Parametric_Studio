"""PSN_MotionClean_Smooth — pure-logic motion-data cleaning pipeline.

This module implements the *logic* of a motion-data cleaning pipeline as a
ComfyUI-style custom node, but it is deliberately **pure Python standard
library only**.  It does NOT import numpy, scipy, torch, or any ComfyUI
internal, and it performs no file, network, or OS access.

The spec's ``ANIMOFLOW_NPZ`` tensor is represented here as a plain JSON
string (or a list of numbers) describing a 1-D motion signal, e.g.
``[0.1, 0.2, 0.15, ...]``.  The node:

  1. parses the raw motion data,
  2. computes a jitter metric (mean absolute second-difference),
  3. applies a selected smoothing method (moving_average, kalman, spline),
  4. recomputes the jitter metric,
  5. returns the cleaned signal (as JSON text) plus the before/after jitter.

All functions take plain values (numbers, strings, JSON text) and return
plain values, so the module is safe to run in any sandbox.
"""

import json
import math

# ---------------------------------------------------------------------------
# Category / constants
# ---------------------------------------------------------------------------
CAT = "ParametricStudio/Motion"

# Allowed smoothing methods (allow-list).
_METHODS = ("moving_average", "kalman", "spline")

# Smoothing window bounds.
_WIN_MIN = 1
_WIN_MAX = 1001


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------
def _parse_motion(motion_data):
    """Parse ``motion_data`` into a list of floats.

    Accepts either a JSON array string (``"[1.0, 2.0]"``) or an actual
    list/tuple of numbers.  Raises ``ValueError`` on bad input.
    """
    if motion_data is None:
        raise ValueError("motion_data is required")

    if isinstance(motion_data, (list, tuple)):
        seq = list(motion_data)
    elif isinstance(motion_data, str):
        text = motion_data.strip()
        if not text:
            raise ValueError("motion_data string is empty")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("motion_data is not valid JSON: %s" % exc)
        if not isinstance(parsed, list):
            raise ValueError("motion_data JSON must be an array of numbers")
        seq = parsed
    else:
        raise ValueError("motion_data must be a JSON array string or a list")

    if len(seq) == 0:
        raise ValueError("motion_data must contain at least one sample")

    out = []
    for i, v in enumerate(seq):
        if isinstance(v, bool):  # bool is a subclass of int; reject it
            raise ValueError("motion_data[%d] is a boolean, not a number" % i)
        if isinstance(v, (int, float)):
            f = float(v)
        elif isinstance(v, str):
            try:
                f = float(v)
            except ValueError:
                raise ValueError("motion_data[%d] is not a number: %r" % (i, v))
        else:
            raise ValueError("motion_data[%d] has unsupported type: %s" % (i, type(v).__name__))
        if not math.isfinite(f):
            raise ValueError("motion_data[%d] is not finite: %r" % (i, v))
        out.append(f)
    return out


def _jitter_metric(seq):
    """Mean absolute second-difference (a simple jitter/noise metric).

    For a sequence ``x``, the second difference at index ``i`` is
    ``x[i+1] - 2*x[i] + x[i-1]``.  The metric is the mean of the absolute
    values of these second differences.  A perfectly smooth (linear) signal
    has a jitter metric of 0.
    """
    n = len(seq)
    if n < 3:
        return 0.0
    total = 0.0
    count = 0
    for i in range(1, n - 1):
        second = seq[i + 1] - 2.0 * seq[i] + seq[i - 1]
        total += abs(second)
        count += 1
    if count == 0:
        return 0.0
    return total / count


def _moving_average(seq, window):
    """Centered moving-average smoothing with edge handling."""
    n = len(seq)
    if n == 0:
        return []
    if window <= 1:
        return list(seq)
    half = window // 2
    out = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        chunk = seq[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def _kalman(seq, process_noise=0.01, measurement_noise=1.0):
    """Simple 1-D scalar Kalman filter (constant-velocity model).

    This is a lightweight, dependency-free implementation suitable for
    denoising a 1-D signal.  It is *not* a full multi-state pose Kalman
    filter, but it captures the essential smoothing behaviour described in
    the spec.
    """
    n = len(seq)
    if n == 0:
        return []
    if n == 1:
        return [seq[0]]
    # State: [position, velocity]
    x = [seq[0], 0.0]
    # Covariance (2x2), start with reasonable values
    p = [[1.0, 0.0], [0.0, 1.0]]
    out = [x[0]]
    for i in range(1, n):
        # Predict
        # F = [[1, 1], [0, 1]]
        x_pred = [x[0] + x[1], x[1]]
        # P_pred = F P F^T + Q
        p00 = p[0][0] + 2.0 * p[0][1] + p[1][1] + process_noise
        p01 = p[0][1] + p[1][1]
        p10 = p[0][1] + p[1][1]
        p11 = p[1][1]
        p_pred = [[p00, p01], [p10, p11]]
        # Update with measurement z = seq[i], H = [1, 0]
        z = seq[i]
        # S = H P H^T + R = p_pred[0][0] + measurement_noise
        s = p_pred[0][0] + measurement_noise
        # K = P H^T / S  ->  [p_pred[0][0]/s, p_pred[1][0]/s]
        k0 = p_pred[0][0] / s
        k1 = p_pred[1][0] / s
        # Innovation
        y = z - (x_pred[0] + 0.0 * x_pred[1])  # H x_pred = x_pred[0]
        # State update
        x[0] = x_pred[0] + k0 * y
        x[1] = x_pred[1] + k1 * y
        # Covariance update: P = (I - K H) P_pred
        # I - K H = [[1 - k0, 0], [-k1, 1]]
        p_new00 = (1.0 - k0) * p_pred[0][0]
        p_new01 = (1.0 - k0) * p_pred[0][1]
        p_new10 = -k1 * p_pred[0][0] + p_pred[1][0]
        p_new11 = -k1 * p_pred[0][1] + p_pred[1][1]
        p = [[p_new00, p_new01], [p_new10, p_new11]]
        out.append(x[0])
    return out


def _spline(seq, window):
    """Simple cubic-smoothing approximation via weighted local polynomial.

    A true cubic spline requires scipy; here we approximate the smoothing
    effect with a wider, weighted moving average that mimics spline-like
    behaviour (smoother than a plain moving average).  The ``window``
    parameter controls the effective support.
    """
    n = len(seq)
    if n == 0:
        return []
    if window <= 1:
        return list(seq)
    half = max(1, window // 2)
    # Build a simple triangular weight kernel of size (2*half+1)
    kernel = []
    for d in range(-half, half + 1):
        kernel.append(float(half - abs(d) + 1))
    ksum = sum(kernel)
    if ksum == 0:
        return list(seq)
    kernel = [w / ksum for w in kernel]
    out = []
    for i in range(n):
        acc = 0.0
        wsum = 0.0
        for d, w in zip(range(-half, half + 1), kernel):
            j = i + d
            if 0 <= j < n:
                acc += w * seq[j]
                wsum += w
        out.append(acc / wsum if wsum > 0 else seq[i])
    return out


def _smooth(seq, method, window):
    """Dispatch to the selected smoothing method."""
    if method == "moving_average":
        return _moving_average(seq, window)
    if method == "kalman":
        return _kalman(seq)
    if method == "spline":
        return _spline(seq, window)
    raise ValueError("unknown smoothing method: %r" % method)


def _to_json(seq):
    """Serialize a list of floats to a compact JSON string."""
    return json.dumps([round(v, 6) for v in seq])


# ---------------------------------------------------------------------------
# ComfyUI-style node
# ---------------------------------------------------------------------------
class PSN_MotionClean_Smooth:
    """Clean a 1-D motion signal by smoothing and report jitter before/after.

    Pure-logic implementation: no numpy, no scipy, no file/network access.
    ``motion_data`` is a JSON array string (or list) of numbers.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "motion_data": ("STRING", {"default": "[]", "multiline": True}),
                "smoothing_window": ("INT", {"default": 5, "min": _WIN_MIN, "max": _WIN_MAX, "step": 1}),
                "method": (list(_METHODS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "FLOAT", "FLOAT")
    RETURN_NAMES = ("cleaned_motion", "jitter_before", "jitter_after")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, motion_data, smoothing_window, method):
        seq = _parse_motion(motion_data)
        jitter_before = _jitter_metric(seq)
        cleaned = _smooth(seq, method, smoothing_window)
        jitter_after = _jitter_metric(cleaned)
        return (_to_json(cleaned), jitter_before, jitter_after)


# ---------------------------------------------------------------------------
# Module-level mappings (ComfyUI convention)
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "PSN_MotionClean_Smooth": PSN_MotionClean_Smooth,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MotionClean_Smooth": "Motion Clean Smooth",
}
