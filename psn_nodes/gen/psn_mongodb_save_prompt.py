"""PSN_MongoDB_Save_Prompt: pure-logic prompt/params serialization and document-ID generation.

This module implements ONLY the secure, pure-Python part of the "save prompt to MongoDB"
workflow. It does NOT open sockets, import pymongo, or perform any network/file I/O.
Instead it:
  * validates and parses the JSON `params` string,
  * builds a canonical document dict (with schema-version and timestamp fields),
  * generates a deterministic, collision-resistant document ID string,
  * returns the ID plus a JSON-serializable payload that a real driver could insert.

The node wrapper takes plain values (strings) and returns plain values (strings).
"""

import json
import hashlib
import time

CAT = "ParametricStudio/Storage"

# Allowed top-level keys in the params JSON object (allow-list to prevent schema drift)
_ALLOWED_PARAM_KEYS = frozenset({
    "width", "height", "steps", "cfg", "sampler", "scheduler",
    "seed", "model", "lora", "clip_skip", "denoise", "batch_size",
})

_SCHEMA_VERSION = 1


def _psn_validate_params(params_text):
    """Validate and parse the params JSON string.

    Returns (ok, parsed_dict_or_None, error_string).
    """
    if not isinstance(params_text, str):
        return False, None, "params must be a string"
    if params_text.strip() == "":
        return False, None, "params must not be empty"
    try:
        parsed = json.loads(params_text)
    except (json.JSONDecodeError, ValueError) as exc:
        return False, None, "invalid JSON: %s" % exc
    if not isinstance(parsed, dict):
        return False, None, "params must be a JSON object"
    # Allow-list check: reject unknown keys to guard against schema drift
    unknown = set(parsed.keys()) - _ALLOWED_PARAM_KEYS
    if unknown:
        return False, None, "unknown param keys: %s" % ", ".join(sorted(unknown))
    return True, parsed, ""


def _psn_generate_doc_id(prompt, params_dict, timestamp):
    """Generate a deterministic document ID from prompt, params, and timestamp."""
    canonical = json.dumps(
        {"prompt": prompt, "params": params_dict, "ts": timestamp},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return "psn_%s" % digest[:24]


def _psn_build_document(prompt, params_dict, timestamp, doc_id):
    """Build the canonical document dict that would be inserted into MongoDB."""
    return {
        "_id": doc_id,
        "prompt": prompt,
        "params": params_dict,
        "schema_version": _SCHEMA_VERSION,
        "created_at": timestamp,
    }


class PSN_MongoDB_Save_Prompt:
    """Saves a prompt and its parameters by building a canonical document and returning its ID.

    Pure-logic implementation: no network, no pymongo, no file I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "params": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "timestamp": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1e12, "step": 0.001}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("doc_id", "document_json")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, params, timestamp=None):
        if timestamp is None or timestamp <= 0:
            timestamp = time.time()

        if not isinstance(prompt, str):
            return ("", json.dumps({"error": "prompt must be a string"}))

        ok, parsed_params, err = _psn_validate_params(params)
        if not ok:
            return ("", json.dumps({"error": err}))

        doc_id = _psn_generate_doc_id(prompt, parsed_params, timestamp)
        doc = _psn_build_document(prompt, parsed_params, timestamp, doc_id)
        doc_json = json.dumps(doc, sort_keys=True, separators=(",", ":"))
        return (doc_id, doc_json)


NODE_CLASS_MAPPINGS = {
    "PSN_MongoDB_Save_Prompt": PSN_MongoDB_Save_Prompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MongoDB_Save_Prompt": "PSN MongoDB Save Prompt",
}
