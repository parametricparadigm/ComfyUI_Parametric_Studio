"""ComfyUI nodes: verified prompt enhancement with a deterministic fallback, and deterministic rotation (original). Logic in psn/."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class PSN_PromptEnhance:
    """Turn a short idea into a model-ready prompt. The local model's answer is used only if its checks pass (subject kept, length, SFW, at most one camera move for video); otherwise a deterministic formula writes the prompt. `source` says which."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"idea": ("STRING", {"multiline": True, "default": "a red fox in fresh snow at sunrise"}), "kind": (["image", "video"],), "seed": ("INT", {"default": 0, "min": 0, "max": 2**31})},
                                  "optional": {"subject": ("STRING", {"default": ""}), "setting": ("STRING", {"default": ""}), "camera": ("STRING", {"default": ""})}}
    RETURN_TYPES = ("STRING", "STRING", "STRING"); RETURN_NAMES = ("prompt", "negative", "source"); FUNCTION = "run"; CATEGORY = "ParametricStudio/Prompts"
    def run(self, idea, kind, seed, subject="", setting="", camera=""):
        from psn.fallback_prompt import enhance_or_fallback
        r = enhance_or_fallback(idea, {k: v for k, v in (("subject", subject), ("setting", setting), ("camera", camera)) if v}, seed, kind == "video"); return (r["prompt"], r["negative"], r["source"])
class PSN_Rotate:
    """Pick one option from a list (one per line) by unit and index, deterministically: the same inputs always give the same pick, and nothing repeats within a unit until the list is used up."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"options": ("STRING", {"multiline": True, "default": "red coat\nblue jacket\ngreen scarf"}), "unit": ("INT", {"default": 0, "min": 0, "max": 100000}), "index": ("INT", {"default": 0, "min": 0, "max": 100000}), "offset": ("INT", {"default": 0, "min": 0, "max": 100000})}}
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("choice",); FUNCTION = "run"; CATEGORY = "ParametricStudio/Prompts"
    def run(self, options, unit, index, offset):
        from psn.rotation import rotate
        return (rotate([x.strip() for x in options.splitlines() if x.strip()], unit, index, offset),)
NODE_CLASS_MAPPINGS = {"PSN_PromptEnhance": PSN_PromptEnhance, "PSN_Rotate": PSN_Rotate}; NODE_DISPLAY_NAME_MAPPINGS = {"PSN_PromptEnhance": "PSN Prompt Enhance (verified + fallback)", "PSN_Rotate": "PSN Rotate (deterministic)"}
