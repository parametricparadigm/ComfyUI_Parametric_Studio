"""CPU-only image quality checks (numpy + PIL): sharpness (variance of the Laplacian), grain / high-frequency energy, clipped shadows and highlights, colourfulness, and a 64-bit difference hash for near-duplicate detection.
No GPU, no model: a render can be judged without re-running anything. Idea carried over from the home studio's image checks; original code."""
import numpy as np
from PIL import Image

def to_gray(img, max_side=512):
    """img: path, PIL image, or an HxWxC array (uint8, or float in 0..1). -> float32 grey array in 0..255, long side <= max_side."""
    if isinstance(img, str): img = Image.open(img)
    if isinstance(img, np.ndarray):
        a = img.astype(np.float32) * (255.0 if img.dtype != np.uint8 and img.max() <= 1.0 else 1.0); img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img = img.convert("RGB"); w, h = img.size
    if max(w, h) > max_side: s = max_side / max(w, h); img = img.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32), np.asarray(img.convert("L"), dtype=np.float32)

def _blur(g): k = np.array([1, 2, 1], np.float32) / 4; p = np.pad(g, 1, mode="edge"); t = k[0] * p[:, :-2] + k[1] * p[:, 1:-1] + k[2] * p[:, 2:]; return k[0] * t[:-2] + k[1] * t[1:-1] + k[2] * t[2:]

def measure(img):
    rgb, g = to_gray(img); lap = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    resid = g - _blur(g); rg, yb = rgb[..., 0] - rgb[..., 1], 0.5 * (rgb[..., 0] + rgb[..., 1]) - rgb[..., 2]
    return {"sharpness": float(lap.var()), "grain": float(resid.std()), "clipped_dark_pct": float((g <= 5).mean() * 100), "clipped_bright_pct": float((g >= 250).mean() * 100),
            "colorfulness": float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean())), "contrast": float(g.std()), "size": list(g.shape[::-1])}

def dhash(img, size=8):
    _, g = to_gray(img, max_side=4096); im = Image.fromarray(g.astype(np.uint8)).resize((size + 1, size), Image.LANCZOS); a = np.asarray(im, np.float32)
    bits = (a[:, 1:] > a[:, :-1]).flatten(); return int("".join("1" if b else "0" for b in bits), 2)

def distance(a, b): return bin(a ^ b).count("1")

def near_duplicates(hashes, max_distance=5):
    """-> (keep, drop): indices to keep (first of each group) and indices that are near-duplicates of an earlier kept one."""
    keep, drop = [], []
    for i, h in enumerate(hashes):
        (drop if any(distance(h, hashes[k]) <= max_distance for k in keep) else keep).append(i)
    return keep, drop

def assess(m, min_sharpness=40.0, max_clipped_pct=25.0, min_contrast=12.0):
    """-> (ok, reasons). Thresholds are for a 512-px long side; tune per model."""
    r = []
    if m["sharpness"] < min_sharpness: r.append(f"soft/blurry (sharpness {m['sharpness']:.0f} < {min_sharpness:.0f})")
    if m["clipped_dark_pct"] > max_clipped_pct: r.append(f"{m['clipped_dark_pct']:.0f}% crushed shadows")
    if m["clipped_bright_pct"] > max_clipped_pct: r.append(f"{m['clipped_bright_pct']:.0f}% blown highlights")
    if m["contrast"] < min_contrast: r.append(f"flat/low contrast ({m['contrast']:.0f})")
    return (not r), r
