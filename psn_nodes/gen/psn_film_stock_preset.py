"""
PSN_Film_Stock_Preset: Applies a consistent color grading profile based on a selected film stock name.

This module implements the pure-logic part of film stock color grading. It does NOT use torch, numpy,
or any GPU operations. Instead, it works with plain Python lists of RGB values (0.0-1.0) to represent
image data. The LUTs are embedded as pure Python data structures.

Inputs:
- image: A flat list of RGB values (0.0-1.0), length must be a multiple of 3.
- film_stock: One of the predefined film stock names or "Custom".
- intensity: A float between 0.0 and 1.0 controlling the strength of the grade.
- custom_lut: Optional LUT data as a list of lists (3D LUT structure) for "Custom" mode.

Outputs:
- graded_image: A flat list of RGB values (0.0-1.0) after applying the film stock grade.
- lut_data: The LUT data used for grading, as a list of lists.
"""

import math

# Embedded LUT data for each film stock.
# Each LUT is a 3D structure: [R][G][B] -> [R, G, B]
# For simplicity, we use a 2x2x2 LUT (8 entries) for the pure logic implementation.
# In a real implementation, this would be a 33x33x33 LUT loaded from .cube files.

def _build_identity_lut(size=2):
    """Build an identity LUT of given size."""
    lut = []
    for r in range(size):
        r_val = r / (size - 1) if size > 1 else 0.0
        row = []
        for g in range(size):
            g_val = g / (size - 1) if size > 1 else 0.0
            col = []
            for b in range(size):
                b_val = b / (size - 1) if size > 1 else 0.0
                col.append([r_val, g_val, b_val])
            row.append(col)
        lut.append(row)
    return lut

def _build_portra_400_lut(size=2):
    """Build a Kodak Portra 400 LUT with warm shift (R > B)."""
    lut = []
    for r in range(size):
        r_val = r / (size - 1) if size > 1 else 0.0
        row = []
        for g in range(size):
            g_val = g / (size - 1) if size > 1 else 0.0
            col = []
            for b in range(size):
                b_val = b / (size - 1) if size > 1 else 0.0
                # Warm shift: boost R, slightly reduce B
                new_r = min(1.0, r_val * 1.05 + 0.02)
                new_g = min(1.0, g_val * 1.02)
                new_b = max(0.0, b_val * 0.95 - 0.02)
                col.append([new_r, new_g, new_b])
            row.append(col)
        lut.append(row)
    return lut

def _build_hp5_plus_lut(size=2):
    """Build an Ilford HP5 Plus LUT (monochrome, slight contrast)."""
    lut = []
    for r in range(size):
        r_val = r / (size - 1) if size > 1 else 0.0
        row = []
        for g in range(size):
            g_val = g / (size - 1) if size > 1 else 0.0
            col = []
            for b in range(size):
                b_val = b / (size - 1) if size > 1 else 0.0
                # Convert to grayscale with slight contrast
                gray = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
                # Apply slight S-curve for contrast
                gray = gray * gray * (3 - 2 * gray)  # smoothstep
                col.append([gray, gray, gray])
            row.append(col)
        lut.append(row)
    return lut

def _build_velvia_50_lut(size=2):
    """Build a Fujifilm Velvia 50 LUT (high saturation, cool shift)."""
    lut = []
    for r in range(size):
        r_val = r / (size - 1) if size > 1 else 0.0
        row = []
        for g in range(size):
            g_val = g / (size - 1) if size > 1 else 0.0
            col = []
            for b in range(size):
                b_val = b / (size - 1) if size > 1 else 0.0
                # High saturation: boost R and B, reduce G
                new_r = min(1.0, r_val * 1.1)
                new_g = max(0.0, g_val * 0.9)
                new_b = min(1.0, b_val * 1.08 + 0.01)
                col.append([new_r, new_g, new_b])
            row.append(col)
        lut.append(row)
    return lut

FILM_STOCKS = ["Kodak Portra 400", "Ilford HP5 Plus", "Fujifilm Velvia 50", "Custom"]

_LUT_CACHE = {
    "Kodak Portra 400": _build_portra_400_lut(),
    "Ilford HP5 Plus": _build_hp5_plus_lut(),
    "Fujifilm Velvia 50": _build_velvia_50_lut(),
}

def _get_lut(film_stock):
    """Get the LUT for a given film stock name."""
    if film_stock in _LUT_CACHE:
        return _LUT_CACHE[film_stock]
    return _build_identity_lut()

def _validate_lut(lut):
    """Validate that a LUT is a proper 3D structure with valid values."""
    if not isinstance(lut, list) or len(lut) == 0:
        return False
    size_r = len(lut)
    if size_r < 2:
        return False
    for r in range(size_r):
        if not isinstance(lut[r], list) or len(lut[r]) != size_r:
            return False
        for g in range(size_r):
            if not isinstance(lut[r][g], list) or len(lut[r][g]) != size_r:
                return False
            for b in range(size_r):
                entry = lut[r][g][b]
                if not isinstance(entry, list) or len(entry) != 3:
                    return False
                for val in entry:
                    if not isinstance(val, (int, float)):
                        return False
                    if val < 0.0 or val > 1.0:
                        return False
    return True

def _lerp(a, b, t):
    """Linear interpolation between a and b by t."""
    return a + (b - a) * t

def _apply_lut_to_pixel(r, g, b, lut, intensity):
    """Apply a 3D LUT to a single pixel with intensity blending."""
    size = len(lut)
    if size < 2:
        return [r, g, b]
    
    # Scale pixel values to LUT index space
    r_idx = r * (size - 1)
    g_idx = g * (size - 1)
    b_idx = b * (size - 1)
    
    # Get integer and fractional parts
    r0 = int(math.floor(r_idx))
    g0 = int(math.floor(g_idx))
    b0 = int(math.floor(b_idx))
    r1 = min(r0 + 1, size - 1)
    g1 = min(g0 + 1, size - 1)
    b1 = min(b0 + 1, size - 1)
    
    fr = r_idx - r0
    fg = g_idx - g0
    fb = b_idx - b0
    
    # Trilinear interpolation
    c000 = lut[r0][g0][b0]
    c100 = lut[r1][g0][b0]
    c010 = lut[r0][g1][b0]
    c110 = lut[r1][g1][b0]
    c001 = lut[r0][g0][b1]
    c101 = lut[r1][g0][b1]
    c011 = lut[r0][g1][b1]
    c111 = lut[r1][g1][b1]
    
    # Interpolate along B
    c00 = [_lerp(c000[i], c001[i], fb) for i in range(3)]
    c10 = [_lerp(c100[i], c101[i], fb) for i in range(3)]
    c01 = [_lerp(c010[i], c011[i], fb) for i in range(3)]
    c11 = [_lerp(c110[i], c111[i], fb) for i in range(3)]
    
    # Interpolate along G
    c0 = [_lerp(c00[i], c01[i], fg) for i in range(3)]
    c1 = [_lerp(c10[i], c11[i], fg) for i in range(3)]
    
    # Interpolate along R
    result = [_lerp(c0[i], c1[i], fr) for i in range(3)]
    
    # Blend with original based on intensity
    blended = [_lerp([r, g, b][i], result[i], intensity) for i in range(3)]
    
    # Clamp to [0, 1]
    return [max(0.0, min(1.0, v)) for v in blended]

def _apply_film_stock(image, film_stock, intensity, custom_lut=None):
    """Apply film stock grading to an image represented as a flat list of RGB values."""
    if not isinstance(image, list):
        raise ValueError("image must be a list")
    if len(image) % 3 != 0:
        raise ValueError("image length must be a multiple of 3")
    if not (0.0 <= intensity <= 1.0):
        raise ValueError("intensity must be between 0.0 and 1.0")
    
    if film_stock == "Custom":
        if custom_lut is None:
            raise ValueError("custom_lut is required when film_stock is 'Custom'")
        if not _validate_lut(custom_lut):
            raise ValueError("custom_lut is invalid")
        lut = custom_lut
    else:
        if film_stock not in FILM_STOCKS:
            raise ValueError(f"Unknown film stock: {film_stock}")
        lut = _get_lut(film_stock)
    
    graded = []
    for i in range(0, len(image), 3):
        r, g, b = image[i], image[i+1], image[i+2]
        if not all(isinstance(v, (int, float)) for v in (r, g, b)):
            raise ValueError("image values must be numeric")
        if not all(0.0 <= v <= 1.0 for v in (r, g, b)):
            raise ValueError("image values must be in [0, 1]")
        graded_pixel = _apply_lut_to_pixel(r, g, b, lut, intensity)
        graded.extend(graded_pixel)
    
    return graded, lut

class PSN_Film_Stock_Preset:
    """Applies a consistent color grading profile based on a selected film stock name."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("LIST", {"default": []}),
                "film_stock": (FILM_STOCKS,),
                "intensity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "custom_lut": ("LIST", {"default": None}),
            }
        }
    
    RETURN_TYPES = ("LIST", "LIST")
    RETURN_NAMES = ("graded_image", "lut_data")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Film"
    
    def run(self, image, film_stock, intensity, custom_lut=None):
        graded, lut = _apply_film_stock(image, film_stock, intensity, custom_lut)
        return (graded, lut)

NODE_CLASS_MAPPINGS = {
    "PSN_Film_Stock_Preset": PSN_Film_Stock_Preset,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Film_Stock_Preset": "PSN Film Stock Preset",
}
