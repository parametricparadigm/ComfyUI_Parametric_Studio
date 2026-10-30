"""PSN_One_Click_Prompt_Generator: deterministic, curated one-click prompt builder.

Pure-logic node: builds a Stable Diffusion prompt and a negative prompt from
curated word lists per theme, using a seeded PRNG for reproducibility.
No torch, no ComfyUI imports, no I/O, no network.
"""

import random

CAT = "ParametricStudio/Generation"

THEMES = ["fantasy", "sci-fi", "realistic", "anime"]

_SUBJECTS = {
    "fantasy": ["a lone knight", "an ancient dragon", "a forest spirit", "a wandering mage", "a crystal golem"],
    "sci-fi": ["a cybernetic android", "a deep space explorer", "a rogue AI core", "a plasma mech", "a holographic navigator"],
    "realistic": ["a weathered fisherman", "a city street vendor", "a mountain hiker", "a jazz musician", "a vintage car"],
    "anime": ["a wandering swordfighter", "a mecha pilot", "a spirit fox", "a ramen chef", "a starship captain"],
}

_STYLES = {
    "fantasy": ["epic fantasy art", "dark fantasy illustration", "storybook painting", "mythic concept art"],
    "sci-fi": ["cyberpunk aesthetic", "retro-futurism", "hard sci-fi realism", "neon noir"],
    "realistic": ["photorealistic", "cinematic photography", "documentary style", "hyperrealistic"],
    "anime": ["anime style", "cel shaded", "manga inspired", "90s anime aesthetic"],
}

_LIGHTING = {
    "fantasy": ["moonlit glow", "torchlight flicker", "ethereal aura", "dawn mist light"],
    "sci-fi": ["neon glow", "holographic light", "plasma flare", "cold starlight"],
    "realistic": ["golden hour", "overcast soft light", "harsh midday sun", "candlelight"],
    "anime": ["vibrant sunset", "soft studio light", "rainy night glow", "pastel daylight"],
}

_DETAILS = {
    "fantasy": ["intricate armor", "runes glowing", "misty forest backdrop", "ancient ruins", "flowing cape"],
    "sci-fi": ["chrome plating", "holographic displays", "circuit etchings", "zero gravity", "data streams"],
    "realistic": ["shallow depth of field", "natural skin texture", "reflections", "film grain", "lens flare"],
    "anime": ["expressive eyes", "dynamic pose", "speed lines", "chibi proportions", "vivid colors"],
}

_QUALITY = ["masterpiece", "best quality", "highly detailed", "sharp focus", "8k resolution"]

_NEGATIVE_BASE = ["low quality", "blurry", "deformed", "bad anatomy", "extra limbs", "watermark", "text", "signature"]

_NEGATIVE_THEME = {
    "fantasy": ["modern clothing", "cars", "technology"],
    "sci-fi": ["medieval", "organic skin", "hand-drawn"],
    "realistic": ["cartoon", "anime", "stylized"],
    "anime": ["photorealistic", "3d render", "live action"],
}


class PSN_One_Click_Prompt_Generator:
    """Generate a curated, reproducible SD prompt + negative prompt from theme, complexity, and seed."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "theme": (THEMES,),
                "complexity": ("INT", {"default": 3, "min": 1, "max": 5, "step": 1}),
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "negative_prompt")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, theme, complexity, seed):
        if theme not in THEMES:
            raise ValueError(f"theme must be one of {THEMES}, got {theme!r}")
        if not isinstance(complexity, int) or isinstance(complexity, bool):
            raise TypeError("complexity must be an int")
        if not (1 <= complexity <= 5):
            raise ValueError("complexity must be between 1 and 5")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an int")

        rng = random.Random(seed)

        subject = rng.choice(_SUBJECTS[theme])
        style = rng.choice(_STYLES[theme])
        lighting = rng.choice(_LIGHTING[theme])

        parts = [subject, style, lighting]

        # complexity controls how many extra detail tokens are added
        detail_count = max(0, complexity - 1)
        if detail_count > 0:
            details = rng.sample(_DETAILS[theme], k=min(detail_count, len(_DETAILS[theme])))
            parts.extend(details)

        # always append a quality tag
        parts.append(rng.choice(_QUALITY))

        prompt = ", ".join(parts)

        neg_parts = list(_NEGATIVE_BASE)
        neg_parts.extend(_NEGATIVE_THEME[theme])
        rng.shuffle(neg_parts)
        negative_prompt = ", ".join(neg_parts)

        return (prompt, negative_prompt)


NODE_CLASS_MAPPINGS = {
    "PSN_One_Click_Prompt_Generator": PSN_One_Click_Prompt_Generator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_One_Click_Prompt_Generator": "One Click Prompt Generator",
}
