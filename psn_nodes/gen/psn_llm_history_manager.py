"""PSN_LLM_History_Manager: manages conversation history for multi-turn LLM interactions.

This module implements a pure-logic, secure-by-design node that appends messages to a
conversation history and trims it when it exceeds a maximum length. It does not perform
any network, file, OS, or GPU operations. The 'context' is represented as a plain JSON
string (or a dict) containing a 'history' list of {"role": ..., "content": ...} objects
and an optional 'max_length' integer. All inputs and outputs are plain values (strings,
dicts, numbers) so the node can be used without ComfyUI or torch.
"""

import json

CAT = "ParametricStudio/LLM"

VALID_ROLES = ("user", "assistant")


def _normalize_context(context):
    """Normalize a context value into a dict with 'history' list and 'max_length' int.

    Accepts a dict, a JSON string, or None. Returns a new dict.
    """
    if context is None:
        return {"history": [], "max_length": 100}
    if isinstance(context, dict):
        data = dict(context)
    elif isinstance(context, str):
        try:
            data = json.loads(context)
        except (ValueError, TypeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}

    history = data.get("history", [])
    if not isinstance(history, list):
        history = []

    # Sanitize history entries: keep only dicts with role/content strings
    clean_history = []
    for entry in history:
        if isinstance(entry, dict):
            role = entry.get("role", "")
            content = entry.get("content", "")
            if isinstance(role, str) and isinstance(content, str):
                clean_history.append({"role": role, "content": content})

    max_length = data.get("max_length", 100)
    try:
        max_length = int(max_length)
    except (ValueError, TypeError):
        max_length = 100
    if max_length < 0:
        max_length = 0

    return {"history": clean_history, "max_length": max_length}


def _trim_history(history, max_length):
    """Trim history to at most max_length entries, keeping the most recent ones."""
    if max_length <= 0:
        return []
    if len(history) <= max_length:
        return list(history)
    return list(history[-max_length:])


def _context_to_json(context_dict):
    """Serialize a context dict to a JSON string."""
    return json.dumps(context_dict, ensure_ascii=False)


class PSN_LLM_History_Manager:
    """Appends a message to conversation history and trims if it exceeds max length."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "context": ("STRING", {"default": "{}", "multiline": True}),
                "new_message": ("STRING", {"default": "", "multiline": True}),
                "role": (list(VALID_ROLES),),
            },
            "optional": {
                "max_length": ("INT", {"default": 100, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("updated_context",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, context, new_message, role, max_length=None):
        ctx = _normalize_context(context)

        # If max_length is provided via optional input, override
        if max_length is not None:
            try:
                ctx["max_length"] = int(max_length)
            except (ValueError, TypeError):
                pass
            if ctx["max_length"] < 0:
                ctx["max_length"] = 0

        # Validate role
        if role not in VALID_ROLES:
            role = "user"

        # Sanitize new_message
        if not isinstance(new_message, str):
            new_message = str(new_message) if new_message is not None else ""

        # Append the new message
        ctx["history"].append({"role": role, "content": new_message})

        # Trim history
        ctx["history"] = _trim_history(ctx["history"], ctx["max_length"])

        return (_context_to_json(ctx),)


NODE_CLASS_MAPPINGS = {
    "PSN_LLM_History_Manager": PSN_LLM_History_Manager,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_LLM_History_Manager": "PSN LLM History Manager",
}
