"""PSN_Lora_Dataset_Loader: pure-logic LoRA dataset loader.

This module implements the secure, pure-logic portion of a LoRA dataset
loader. It does NOT perform any file system, network, or OS access. Instead,
it accepts a JSON manifest (as a string) describing LoRA files and their
metadata, and produces a structured LORA_LIST and a comma-separated list of
names.

Inputs:
  - manifest_json (STRING): JSON text containing a list of LoRA file entries.
    Each entry is an object with at least "name" (str), and optionally
    "path" (str), "size" (int), "date" (str, ISO-8601), "metadata" (dict).
  - filter_extension (STRING): e.g. ".safetensors"; only entries whose
    "name" or "path" ends with this extension are kept.
  - sort_by (COMBO): "name", "date", or "size".

Outputs:
  - lora_list (LORA_LIST): list of dicts, each with keys:
      name, path, size, date, metadata
  - lora_names (STRING): comma-separated list of LoRA names.

All identifiers start with a letter. No file, network, subprocess, eval,
exec, or dunder tricks are used.
"""

import json

CAT = "ParametricStudio/Lora"

# Allowed sort keys
_SORT_KEYS = ("name", "date", "size")

# Allowed extensions (lowercase, with leading dot)
_ALLOWED_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".bin")


def _validate_extension(ext):
    """Validate and normalize the filter extension. Returns None if invalid."""
    if not isinstance(ext, str):
        return None
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    if ext not in _ALLOWED_EXTENSIONS:
        return None
    return ext


def _parse_manifest(manifest_json):
    """Parse the JSON manifest string into a list of LoRA entry dicts.

    Returns (entries, error_message). entries is a list of dicts on success,
    or None on failure. error_message is None on success.
    """
    if not isinstance(manifest_json, str):
        return None, "manifest_json must be a string"
    try:
        data = json.loads(manifest_json)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, "Invalid JSON: {}".format(exc)
    if not isinstance(data, list):
        return None, "Manifest must be a JSON array"
    entries = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return None, "Entry at index {} is not an object".format(idx)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            return None, "Entry at index {} missing valid 'name'".format(idx)
        path = item.get("path", name)
        if not isinstance(path, str):
            return None, "Entry at index {} has invalid 'path'".format(idx)
        size = item.get("size", 0)
        if not isinstance(size, int) or size < 0:
            return None, "Entry at index {} has invalid 'size'".format(idx)
        date = item.get("date", "")
        if not isinstance(date, str):
            return None, "Entry at index {} has invalid 'date'".format(idx)
        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            return None, "Entry at index {} has invalid 'metadata'".format(idx)
        entries.append({
            "name": name.strip(),
            "path": path,
            "size": size,
            "date": date,
            "metadata": metadata,
        })
    return entries, None


def _matches_extension(entry, ext):
    """Check if an entry's name or path ends with the given extension."""
    name_lower = entry["name"].lower()
    path_lower = entry["path"].lower()
    return name_lower.endswith(ext) or path_lower.endswith(ext)


def _sort_entries(entries, sort_by):
    """Sort entries by the given key. Returns a new sorted list."""
    if sort_by == "name":
        return sorted(entries, key=lambda e: e["name"].lower())
    elif sort_by == "date":
        return sorted(entries, key=lambda e: e["date"] or "")
    elif sort_by == "size":
        return sorted(entries, key=lambda e: e["size"])
    return list(entries)


class PSN_Lora_Dataset_Loader:
    """Load a list of LoRA files from a JSON manifest into a LORA_LIST."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_json": ("STRING", {"default": "[]", "multiline": True}),
                "filter_extension": (list(_ALLOWED_EXTENSIONS), {"default": ".safetensors"}),
                "sort_by": (list(_SORT_KEYS), {"default": "name"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("LORA_LIST", "STRING")
    RETURN_NAMES = ("lora_list", "lora_names")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, manifest_json, filter_extension, sort_by):
        """Parse, filter, sort, and return the LoRA list and names."""
        # Validate extension
        ext = _validate_extension(filter_extension)
        if ext is None:
            return ([], "Error: invalid filter_extension '{}'".format(filter_extension))

        # Validate sort key
        if sort_by not in _SORT_KEYS:
            return ([], "Error: invalid sort_by '{}'".format(sort_by))

        # Parse manifest
        entries, err = _parse_manifest(manifest_json)
        if err is not None:
            return ([], "Error: {}".format(err))

        # Filter by extension
        filtered = [e for e in entries if _matches_extension(e, ext)]

        # Sort
        sorted_entries = _sort_entries(filtered, sort_by)

        # Build names string
        names = ", ".join(e["name"] for e in sorted_entries)

        return (sorted_entries, names)


NODE_CLASS_MAPPINGS = {
    "PSN_Lora_Dataset_Loader": PSN_Lora_Dataset_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Lora_Dataset_Loader": "PSN LoRA Dataset Loader",
}
