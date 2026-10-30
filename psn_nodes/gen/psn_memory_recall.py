"""PSN_Memory_Recall: pure-logic memory recall.

This node implements the secure, pure-logic part of a memory recall workflow.
Because the spec requires reading a JSON file (file I/O), which is disallowed
here, the node operates on an in-memory JSON text payload instead of a file
handle. The `store_handle` input is treated as a JSON string containing a list
of memory entries (each a dict with at least a "text" key). The `query` input
is a substring filter; an empty query returns all entries.

No file, network, subprocess, or OS access is performed.
"""

import json

CAT = "ParametricStudio/Memory"

# Placeholder type name for the handle (in real ComfyUI this would be a custom type)
MEMORY_HANDLE = "MEMORY_HANDLE"


def _parse_store(store_handle):
    """Parse the store_handle JSON text into a list of memory entries.

    Returns (entries, error_string). entries is a list of dicts on success.
    """
    if not isinstance(store_handle, str):
        return None, "store_handle must be a JSON string"
    try:
        data = json.loads(store_handle)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, "invalid JSON in store_handle: %s" % exc
    if not isinstance(data, list):
        return None, "store_handle JSON must be a list of entries"
    # Validate each entry is a dict with a "text" key
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            return None, "entry %d is not an object" % i
        if "text" not in entry:
            return None, "entry %d missing 'text' key" % i
    return data, None


def _filter_entries(entries, query):
    """Filter entries by substring match on the 'text' field.

    If query is empty or None, return all entries.
    """
    if not query:
        return entries
    q = query.lower()
    return [e for e in entries if q in e["text"].lower()]


def _format_output(entries):
    """Format filtered entries back into a JSON string for output."""
    return json.dumps(entries, ensure_ascii=False)


class PSN_Memory_Recall:
    """Recall stored memories by keyword substring match.

    Inputs:
        store_handle (MEMORY_HANDLE): JSON string of a list of memory entries.
        query (STRING): Substring to search for; empty string returns all.

    Outputs:
        memories (STRING): JSON string of matching memory entries.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "store_handle": (MEMORY_HANDLE,),
                "query": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("memories",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, store_handle, query):
        entries, err = _parse_store(store_handle)
        if err is not None:
            return (json.dumps({"error": err}),)
        filtered = _filter_entries(entries, query)
        return (_format_output(filtered),)


NODE_CLASS_MAPPINGS = {
    "PSN_Memory_Recall": PSN_Memory_Recall,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Memory_Recall": "PSN Memory Recall",
}
