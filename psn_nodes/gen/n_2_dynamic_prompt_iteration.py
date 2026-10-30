"""ComfyUI custom nodes: Dynamic Prompt Iteration.

Nodes:
- PSN_PromptIterator: returns the prompt at a given index, the next index, and is_done.
- PSN_ListToPromptQueue: normalizes various inputs into a standard list of strings.
"""

CAT = "ParametricStudio/Prompt"


def _normalize_prompt_list(raw):
    """Normalize raw input into a list of strings.

    Accepts:
      - list / tuple of strings
      - a single string (treated as one prompt)
      - a comma-separated string (split into multiple prompts)
    Raises ValueError for unsupported types or non-string elements.
    """
    if raw is None:
        raise ValueError("prompt_list must not be None")

    if isinstance(raw, str):
        # A single string: if it contains commas, split; otherwise one item.
        if "," in raw:
            parts = [p.strip() for p in raw.split(",")]
            parts = [p for p in parts if p]
            if not parts:
                raise ValueError("prompt_list string produced no non-empty items")
            return parts
        return [raw]

    if isinstance(raw, (list, tuple)):
        out = []
        for i, item in enumerate(raw):
            if not isinstance(item, str):
                raise ValueError(
                    f"prompt_list item {i} is {type(item).__name__}, expected str"
                )
            out.append(item)
        return out

    raise ValueError(f"prompt_list must be str, list, or tuple; got {type(raw).__name__}")


class PSN_ListToPromptQueue:
    """Normalize input into a standard list of prompt strings for iteration."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_input": ("LIST[STRING]",),
            }
        }

    RETURN_TYPES = ("LIST[STRING]",)
    RETURN_NAMES = ("queue",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, list_input):
        queue = _normalize_prompt_list(list_input)
        return (queue,)


class PSN_PromptIterator:
    """Return the prompt at the current index, the next index, and is_done.

    Stateless: the caller passes `index` explicitly each call, so there is no
    hidden mutable state and no risk of infinite loops from lost counters.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_list": ("LIST[STRING]",),
                "index": ("INT", {"default": 0, "min": 0, "max": 100000}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN")
    RETURN_NAMES = ("current_prompt", "next_index", "is_done")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt_list, index):
        prompts = _normalize_prompt_list(prompt_list)
        n = len(prompts)

        if n == 0:
            return ("", 0, True)

        if index < 0:
            raise ValueError(f"index must be >= 0, got {index}")

        if index >= n:
            # Past the end: return last prompt, next_index stays at n, is_done True.
            return (prompts[-1], n, True)

        current = prompts[index]
        next_index = index + 1
        is_done = next_index >= n
        return (current, next_index, is_done)


NODE_CLASS_MAPPINGS = {
    "PSN_PromptIterator": PSN_PromptIterator,
    "PSN_ListToPromptQueue": PSN_ListToPromptQueue,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PromptIterator": "PSN Prompt Iterator",
    "PSN_ListToPromptQueue": "PSN List To Prompt Queue",
}
