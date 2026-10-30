"""
PSN_Video_Storyboarder: Multi-scene video storyboarder.

This node manages multi-scene stories and key-value templates for structured video prompts.
It takes a scene count, a JSON array of template strings, a global style, and a transition type.
It fills each template with the global style and outputs a JSON array of fully formed prompts
along with metadata describing the scene indices and transition info.

Pure Python standard library only. No GPU, no network, no file I/O.
"""

import json

CAT = "ParametricStudio/Video"

_TRANSITIONS = ["cut", "fade", "dissolve"]


class PSN_Video_Storyboarder:
    """
    Fills scene templates with a global style and produces a JSON array of prompts
    plus metadata about scene indices and transitions.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_count": ("INT", {"default": 1, "min": 1, "max": 100, "step": 1}),
                "scene_templates": ("STRING", {"default": '["Scene {i}: {style}"]', "multiline": True}),
                "global_style": ("STRING", {"default": "cinematic", "multiline": False}),
                "transition_type": (_TRANSITIONS,),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("scene_prompts", "metadata")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, scene_count, scene_templates, global_style, transition_type):
        # Validate scene_count
        if not isinstance(scene_count, int) or scene_count < 1:
            raise ValueError("scene_count must be a positive integer")

        # Parse scene_templates JSON
        try:
            templates = json.loads(scene_templates)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"scene_templates must be valid JSON: {e}")

        if not isinstance(templates, list):
            raise ValueError("scene_templates must be a JSON array")

        # Validate transition_type
        if transition_type not in _TRANSITIONS:
            raise ValueError(f"transition_type must be one of {_TRANSITIONS}")

        # Build prompts
        prompts = []
        for i in range(scene_count):
            # Cycle through templates if scene_count > len(templates)
            template = templates[i % len(templates)] if templates else "Scene {i}: {style}"
            if not isinstance(template, str):
                template = str(template)
            prompt = template.replace("{style}", global_style).replace("{i}", str(i))
            prompts.append(prompt)

        # Build metadata
        metadata = {
            "scene_indices": list(range(scene_count)),
            "transition_type": transition_type,
            "scene_count": scene_count,
            "global_style": global_style,
        }

        return (json.dumps(prompts), json.dumps(metadata))


NODE_CLASS_MAPPINGS = {
    "PSN_Video_Storyboarder": PSN_Video_Storyboarder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Storyboarder": "Video Storyboarder",
}
