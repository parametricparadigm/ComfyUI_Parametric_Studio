"""Pure-logic dynamic prompt generation and iteration for ComfyUI.

This module implements two closely related nodes:

1. PSN_Prompt_Generator: Generates multiple prompt variations from a base
   template by substituting placeholder variables with randomly selected
   values from provided variable lists.

2. PSN_Prompt_Iterator: Yields one prompt at a time from a list, tracking
   the current index and reporting when iteration is complete.

These nodes use only the Python standard library (random, string) and
perform no file I/O, network access, or GPU operations. They are designed
to be chained together in a loop pattern where the iterator's next_index
feeds back into itself until done is True.
"""

import random
import string

CAT = "ParametricStudio/Prompt"


class PSN_Prompt_Generator:
    """Generates multiple prompt variations from a base template.

    The template uses {var_name} placeholders. Each variable name in the
    template must correspond to an entry in the variables list. Each entry
    in variables is a comma-separated list of possible values; one value
    is randomly selected per variation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template": ("STRING", {"default": "a {subject} in a {setting}", "multiline": True}),
                "variables": ("STRING", {"default": "subject:cat,dog,bird;setting:forest,city,beach", "multiline": True}),
                "num_variations": ("INT", {"default": 3, "min": 1, "max": 1000, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompts",)
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_variables(variables_text):
        """Parse the variables string into a dict of name -> list of values.

        Format: name1:val1,val2;name2:val3,val4
        """
        var_map = {}
        if not variables_text or not variables_text.strip():
            return var_map
        for group in variables_text.split(";"):
            group = group.strip()
            if not group:
                continue
            if ":" not in group:
                continue
            name, values_part = group.split(":", 1)
            name = name.strip()
            values = [v.strip() for v in values_part.split(",") if v.strip()]
            if name and values:
                var_map[name] = values
        return var_map

    @staticmethod
    def _extract_placeholders(template):
        """Extract placeholder names from a template string."""
        placeholders = set()
        i = 0
        while i < len(template):
            if template[i] == "{":
                j = template.find("}", i)
                if j != -1:
                    name = template[i + 1:j].strip()
                    if name:
                        placeholders.add(name)
                    i = j + 1
                else:
                    i += 1
            else:
                i += 1
        return placeholders

    def run(self, template, variables, num_variations, seed):
        var_map = self._parse_variables(variables)
        placeholders = self._extract_placeholders(template)

        # Validate that all placeholders have corresponding variables
        missing = placeholders - set(var_map.keys())
        if missing:
            raise ValueError(
                f"Template placeholders {sorted(missing)} have no corresponding variables in the variables input."
            )

        rng = random.Random(seed)
        prompts = []
        for _ in range(num_variations):
            filled = template
            for name, values in var_map.items():
                if name in placeholders:
                    chosen = rng.choice(values)
                    filled = filled.replace("{" + name + "}", chosen)
            prompts.append(filled)

        return (prompts,)


class PSN_Prompt_Iterator:
    """Yields one prompt at a time from a list of prompts.

    Takes the current index and returns the prompt at that index,
    the next index, and whether iteration is complete.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {"default": "", "multiline": True}),
                "current_index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("current_prompt", "next_index", "done")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_prompts(prompts_text):
        """Parse the prompts string into a list of prompt strings.

        Prompts are separated by newlines. Empty lines are skipped.
        """
        if not prompts_text or not prompts_text.strip():
            return []
        lines = [line.strip() for line in prompts_text.splitlines()]
        return [line for line in lines if line]

    def run(self, prompts, current_index):
        prompt_list = self._parse_prompts(prompts)
        total = len(prompt_list)

        if total == 0:
            return ("", 0, True)

        if current_index >= total:
            return ("", current_index, True)

        current_prompt = prompt_list[current_index]
        next_index = current_index + 1
        done = next_index >= total

        return (current_prompt, next_index, done)


NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Generator": PSN_Prompt_Generator,
    "PSN_Prompt_Iterator": PSN_Prompt_Iterator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Generator": "PSN Prompt Generator",
    "PSN_Prompt_Iterator": "PSN Prompt Iterator",
}
