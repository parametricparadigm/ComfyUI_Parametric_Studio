"""
PSN_Random_Asset_Selector: Randomly selects a subset of assets from a provided list for A/B testing.

This module implements a pure-logic node that takes a JSON-formatted list of asset paths (strings),
a random seed, and a count, and returns a JSON-formatted list of selected asset paths.
It uses Python's standard library `random` module for reproducible selection.

No file I/O, network, or GPU operations are performed. The input `asset_list` is expected to be
a JSON array of strings (e.g., '["path/to/a.png", "path/to/b.png"]').
"""

import json
import random

# Module-level constants
CAT = "ParametricStudio/Assets"

class PSN_Random_Asset_Selector:
    """
    Randomly selects `count` assets from `asset_list` using a fixed `seed` for reproducibility.
    
    Inputs:
        asset_list (STRING): A JSON array of strings representing file paths.
        seed (INT): The random seed for reproducibility.
        count (INT): The number of assets to select.
        
    Outputs:
        selected_assets (STRING): A JSON array of strings representing the selected file paths.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset_list": ("STRING", {"default": "[]", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": -2**31, "max": 2**31 - 1}),
                "count": ("INT", {"default": 1, "min": 0, "max": 10000}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_assets",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, asset_list, seed, count):
        # Parse the asset list from JSON
        try:
            assets = json.loads(asset_list)
        except json.JSONDecodeError:
            raise ValueError("asset_list must be a valid JSON array of strings")

        # Validate that assets is a list of strings
        if not isinstance(assets, list):
            raise ValueError("asset_list must be a JSON array")
        
        for i, asset in enumerate(assets):
            if not isinstance(asset, str):
                raise ValueError(f"Asset at index {i} is not a string: {type(asset)}")

        # Handle edge cases
        if count <= 0:
            return (json.dumps([]),)
        
        if not assets:
            return (json.dumps([]),)
        
        # Clamp count to the length of the list
        actual_count = min(count, len(assets))
        
        # Use a dedicated Random instance for reproducibility
        rng = random.Random(seed)
        
        # Select without replacement
        selected = rng.sample(assets, actual_count)
        
        return (json.dumps(selected),)


NODE_CLASS_MAPPINGS = {
    "PSN_Random_Asset_Selector": PSN_Random_Asset_Selector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Random_Asset_Selector": "Random Asset Selector"
}
