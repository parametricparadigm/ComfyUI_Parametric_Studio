"""ComfyUI nodes for the CPU-only image checks (original). Logic in psn/imagecheck.py."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from psn import imagecheck as IC
def _arrays(image): return [(image[i].detach().cpu().numpy()) for i in range(image.shape[0])]
class PSN_ImageQuality:
    """Judge each image of a batch on the CPU: sharpness, grain, clipped shadows/highlights, contrast. Passes the images through unchanged; `all_pass` is false if any image fails, `report_json` says why."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"image": ("IMAGE",), "min_sharpness": ("FLOAT", {"default": 40.0, "min": 0.0, "max": 5000.0, "step": 1.0}), "max_clipped_pct": ("FLOAT", {"default": 25.0, "min": 0.0, "max": 100.0, "step": 1.0})}}
    RETURN_TYPES = ("IMAGE", "STRING", "BOOLEAN"); RETURN_NAMES = ("image", "report_json", "all_pass"); FUNCTION = "run"; CATEGORY = "ParametricStudio/Quality"
    def run(self, image, min_sharpness, max_clipped_pct):
        rows = []
        for i, a in enumerate(_arrays(image)): m = IC.measure(a); ok, why = IC.assess(m, min_sharpness, max_clipped_pct); rows.append({"index": i, "ok": ok, "why": why, **{k: round(v, 2) for k, v in m.items() if k != "size"}})
        return (image, json.dumps(rows), all(r["ok"] for r in rows))
class PSN_ImageDedupe:
    """Drop near-duplicate images from a batch (perceptual hash; keeps the first of each group). Returns the kept batch and the kept/dropped indices."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"images": ("IMAGE",), "max_distance": ("INT", {"default": 5, "min": 0, "max": 32})}}
    RETURN_TYPES = ("IMAGE", "STRING"); RETURN_NAMES = ("unique_images", "kept_dropped_json"); FUNCTION = "run"; CATEGORY = "ParametricStudio/Quality"
    def run(self, images, max_distance):
        import torch
        keep, drop = IC.near_duplicates([IC.dhash(a) for a in _arrays(images)], max_distance)
        return (images.index_select(0, torch.tensor(keep, device=images.device)), json.dumps({"kept": keep, "dropped": drop}))
NODE_CLASS_MAPPINGS = {"PSN_ImageQuality": PSN_ImageQuality, "PSN_ImageDedupe": PSN_ImageDedupe}; NODE_DISPLAY_NAME_MAPPINGS = {"PSN_ImageQuality": "PSN Image Quality (CPU)", "PSN_ImageDedupe": "PSN Image Dedupe"}
