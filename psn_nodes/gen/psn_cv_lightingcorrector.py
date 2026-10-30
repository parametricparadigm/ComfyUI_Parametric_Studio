"""PSN_CV_LightingCorrector: pure-logic lighting correction for ComfyUI.

This module implements the *pure-logic, secure-by-design* part of a lighting
corrector node. It does NOT import torch, ComfyUI, numpy, opencv, or any
network/file/OS APIs. Instead it operates on plain Python values:

- ``image`` and ``normal_map`` are passed as JSON text describing a small
  grid of pixels (a list of rows, each row a list of [r, g, b] values in
  0..1). This keeps the node testable with the standard library only.
- The node estimates a light direction, computes an exposure delta, and
  returns a corrected image (same JSON text format), the estimated light
  direction as a human-readable string, and the exposure delta as a float.

The heavy CV work (real tensor ops, gamma curves, white balance on GPU) is
left to the host; here we implement the deterministic math: normal-based
light vector estimation, a simple Lambertian intrinsic decomposition
fallback, color-temperature estimation, and a white-balance + exposure
adjustment.
"""

import json
import math

CAT = "ParametricStudio/CV"

# Allowed light direction labels (8 compass directions + center).
_DIRECTIONS = [
    "Top-Left", "Top", "Top-Right",
    "Left", "Center", "Right",
    "Bottom-Left", "Bottom", "Bottom-Right",
]

# Kelvin range we allow for target white balance.
_KELVIN_MIN = 1000
_KELVIN_MAX = 40000


def _clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _parse_image_json(text):
    """Parse a JSON image payload into a list of rows of [r,g,b] floats.

    Accepts either a JSON string or an already-parsed list. Returns (rows,
    height, width) where rows is a list of lists of 3 floats in 0..1.
    Raises ValueError on malformed input.
    """
    if isinstance(text, str):
        try:
            data = json.loads(text)
        except (ValueError, TypeError) as exc:
            raise ValueError("image must be valid JSON text") from exc
    else:
        data = text

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("image must be a non-empty list of rows")

    rows = []
    for r_idx, row in enumerate(data):
        if not isinstance(row, list) or len(row) == 0:
            raise ValueError("each row must be a non-empty list of pixels")
        parsed_row = []
        for p_idx, px in enumerate(row):
            if not isinstance(px, (list, tuple)) or len(px) != 3:
                raise ValueError("each pixel must be a 3-element [r,g,b] list")
            try:
                r, g, b = (float(px[0]), float(px[1]), float(px[2]))
            except (TypeError, ValueError) as exc:
                raise ValueError("pixel channels must be numeric") from exc
            if not (math.isfinite(r) and math.isfinite(g) and math.isfinite(b)):
                raise ValueError("pixel channels must be finite numbers")
            parsed_row.append([_clamp(r, 0.0, 1.0), _clamp(g, 0.0, 1.0), _clamp(b, 0.0, 1.0)])
        rows.append(parsed_row)

    height = len(rows)
    width = len(rows[0])
    for row in rows:
        if len(row) != width:
            raise ValueError("all rows must have the same width")
    return rows, height, width


def _rows_to_json(rows):
    return json.dumps(rows)


def _estimate_light_from_normals(rows, height, width):
    """Estimate a light direction vector from a normal map.

    Each pixel in the normal map is treated as a unit-ish normal vector
    (x, y, z) encoded in [r, g, b]. We accumulate the vector weighted by
    the z component (front-facing normals contribute more) and normalize.
    Returns a (lx, ly, lz) tuple.
    """
    sx, sy, sz = 0.0, 0.0, 0.0
    count = 0
    for row in rows:
        for px in row:
            nx, ny, nz = px[0], px[1], px[2]
            # Map 0..1 to -1..1 for x and y; keep z in 0..1 as facing.
            vx = nx * 2.0 - 1.0
            vy = ny * 2.0 - 1.0
            vz = nz
            weight = max(0.0, vz)
            sx += vx * weight
            sy += vy * weight
            sz += vz * weight
            count += 1
    if count == 0:
        return (0.0, 0.0, 1.0)
    # Normalize the accumulated vector.
    norm = math.sqrt(sx * sx + sy * sy + sz * sz)
    if norm < 1e-9:
        return (0.0, 0.0, 1.0)
    return (sx / norm, sy / norm, sz / norm)


def _estimate_light_from_intrinsic(rows, height, width):
    """Fallback: estimate light direction from a lit image using a simple
    Lambertian assumption. We treat brightness as a proxy for shading and
    use horizontal/vertical gradients to infer direction.

    Returns a (lx, ly, lz) tuple.
    """
    if height < 2 or width < 2:
        return (0.0, 0.0, 1.0)

    def brightness(px):
        return (px[0] + px[1] + px[2]) / 3.0

    # Compute average horizontal and vertical brightness gradients.
    grad_x_sum = 0.0
    grad_y_sum = 0.0
    gx_count = 0
    gy_count = 0
    for y in range(height):
        for x in range(width):
            b = brightness(rows[y][x])
            if x + 1 < width:
                grad_x_sum += brightness(rows[y][x + 1]) - b
                gx_count += 1
            if y + 1 < height:
                grad_y_sum += brightness(rows[y + 1][x]) - b
                gy_count += 1

    avg_gx = grad_x_sum / gx_count if gx_count else 0.0
    avg_gy = grad_y_sum / gy_count if gy_count else 0.0

    # Light comes from the direction of increasing brightness.
    lx = avg_gx
    ly = avg_gy
    lz = 1.0  # assume mostly front-facing
    norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    if norm < 1e-9:
        return (0.0, 0.0, 1.0)
    return (lx / norm, ly / norm, lz / norm)


def _direction_label(lx, ly, lz):
    """Map a light vector to one of the 8 compass labels + Center.

    The light vector (lx, ly, lz) points in the direction the light is
    coming FROM. In image space, +x is right, +y is down. So if lx is
    negative, the light is from the left; if ly is negative, from the top.
    """
    dx = lx
    dy = ly
    if abs(dx) < 0.25 and abs(dy) < 0.25:
        return "Center"
    # Determine horizontal and vertical components.
    if dx < -0.25:
        h = "Left"
    elif dx > 0.25:
        h = "Right"
    else:
        h = ""
    if dy < -0.25:
        v = "Top"
    elif dy > 0.25:
        v = "Bottom"
    else:
        v = ""
    if v and h:
        return v + "-" + h
    if v:
        return v
    if h:
        return h
    return "Center"


def _estimate_kelvin(rows, height, width):
    """Estimate the color temperature of the image by comparing average R
    and B channels. A simple heuristic: if R > B, the image is warm (lower
    Kelvin); if B > R, it is cool (higher Kelvin)."""
    r_sum = 0.0
    b_sum = 0.0
    count = 0
    for row in rows:
        for px in row:
            r_sum += px[0]
            b_sum += px[2]
            count += 1
    if count == 0:
        return 5500.0
    avg_r = r_sum / count
    avg_b = b_sum / count
    # Map the R-B difference to a Kelvin offset around 5500.
    diff = avg_r - avg_b
    # Scale: a diff of 0.1 corresponds to ~1000K shift.
    kelvin = 5500.0 - diff * 10000.0
    return _clamp(kelvin, _KELVIN_MIN, _KELVIN_MAX)


def _white_balance_factors(current_kelvin, target_kelvin):
    """Compute per-channel white balance factors to shift from current to
    target Kelvin. Simple linear model: warm (low K) means boost blue and
    reduce red; cool (high K) means boost red and reduce blue."""
    delta = target_kelvin - current_kelvin
    # Scale factor: 1000K delta -> 0.1 channel adjustment.
    adj = delta / 10000.0
    r_factor = 1.0 - adj
    g_factor = 1.0
    b_factor = 1.0 + adj
    return (r_factor, g_factor, b_factor)


def _apply_correction(rows, r_factor, g_factor, b_factor, exposure_delta, strength):
    """Apply white balance and exposure correction to the image rows.

    Returns a new list of rows with corrected pixel values.
    """
    corrected = []
    for row in rows:
        new_row = []
        for px in row:
            r = px[0] * r_factor
            g = px[1] * g_factor
            b = px[2] * b_factor
            # Apply exposure delta as a multiplicative factor.
            exp_factor = 1.0 + exposure_delta * strength
            r = r * exp_factor
            g = g * exp_factor
            b = b * exp_factor
            new_row.append([_clamp(r, 0.0, 1.0), _clamp(g, 0.0, 1.0), _clamp(b, 0.0, 1.0)])
        corrected.append(new_row)
    return corrected


class PSN_CV_LightingCorrector:
    """Estimates light direction and adjusts exposure/white balance.

    Pure-logic implementation: operates on JSON-encoded pixel grids, no
    GPU/torch/ComfyUI dependencies.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("STRING", {"default": "[]", "multiline": True}),
                "correction_strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "target_kelvin": ("INT", {"default": 5500, "min": _KELVIN_MIN, "max": _KELVIN_MAX, "step": 100}),
            },
            "optional": {
                "normal_map": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("corrected_image", "estimated_light_dir", "exposure_delta")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, correction_strength, target_kelvin, normal_map=""):
        # Validate correction_strength.
        if not (0.0 <= correction_strength <= 1.0):
            raise ValueError("correction_strength must be between 0.0 and 1.0")
        if not (_KELVIN_MIN <= target_kelvin <= _KELVIN_MAX):
            raise ValueError("target_kelvin out of range")

        rows, height, width = _parse_image_json(image)

        # Estimate light direction.
        if normal_map and normal_map.strip():
            n_rows, n_height, n_width = _parse_image_json(normal_map)
            if n_height != height or n_width != width:
                raise ValueError("normal_map dimensions must match image")
            lx, ly, lz = _estimate_light_from_normals(n_rows, n_height, n_width)
        else:
            lx, ly, lz = _estimate_light_from_intrinsic(rows, height, width)

        light_dir = _direction_label(lx, ly, lz)

        # Estimate current color temperature.
        current_kelvin = _estimate_kelvin(rows, height, width)

        # Compute white balance factors.
        r_factor, g_factor, b_factor = _white_balance_factors(current_kelvin, target_kelvin)

        # Compute exposure delta: based on how far current Kelvin is from target.
        # A simple heuristic: exposure delta proportional to Kelvin difference.
        exposure_delta = (target_kelvin - current_kelvin) / 10000.0
        exposure_delta = _clamp(exposure_delta, -0.5, 0.5)

        # Apply correction.
        corrected_rows = _apply_correction(rows, r_factor, g_factor, b_factor, exposure_delta, correction_strength)
        corrected_json = _rows_to_json(corrected_rows)

        return (corrected_json, light_dir, exposure_delta)


NODE_CLASS_MAPPINGS = {
    "PSN_CV_LightingCorrector": PSN_CV_LightingCorrector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_LightingCorrector": "CV Lighting Corrector",
}
