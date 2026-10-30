"""PSN_StudioDatasetLoader: pure-logic loader/validator for storyboard JSON payloads.

This module implements the secure, CPU-only portion of the StudioDatasetLoader spec.
It does NOT open files, sockets, or perform any OS/network I/O. Instead, it accepts
plain JSON text (or a base64-encoded JSON string) as input, parses it, validates the
canonical storyboard schema (shots, characters, assets), normalizes data types, and
returns a validated data structure plus a human-readable list of validation errors.

The node acts as the single entry point for downstream nodes, enforcing required
fields (shot_id, duration, prompt_seed) and schema version compatibility.
"""

import json
import base64
import binascii

# Custom data type identifier for ComfyUI
PSN_STORYBOARD_DATA = "PSN_STORYBOARD_DATA"

# Supported schema versions
SUPPORTED_SCHEMA_VERSIONS = (1, 2)

# Required top-level keys
REQUIRED_TOP_LEVEL_KEYS = ("shots", "characters", "assets", "settings")

# Required fields per shot
REQUIRED_SHOT_FIELDS = ("shot_id", "duration", "prompt_seed")

# Required fields per character
REQUIRED_CHARACTER_FIELDS = ("character_id", "name")

# Required fields per asset
REQUIRED_ASSET_FIELDS = ("asset_id", "name")


def _try_decode_base64(text):
    """Attempt to decode a base64 string. Returns decoded string or None if not valid base64."""
    try:
        decoded_bytes = base64.b64decode(text, validate=True)
        return decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None


def _parse_payload(raw_text):
    """Parse raw text as JSON or base64-encoded JSON. Returns (data, error_message)."""
    if not isinstance(raw_text, str):
        return None, "Input must be a string containing JSON or base64-encoded JSON."

    stripped = raw_text.strip()
    if not stripped:
        return None, "Input string is empty."

    # Try direct JSON parse first
    try:
        data = json.loads(stripped)
        return data, None
    except json.JSONDecodeError:
        pass

    # Try base64 decode then JSON parse
    decoded = _try_decode_base64(stripped)
    if decoded is not None:
        try:
            data = json.loads(decoded)
            return data, None
        except json.JSONDecodeError:
            return None, "Base64-decoded content is not valid JSON."

    return None, "Input is neither valid JSON nor valid base64-encoded JSON."


def _validate_schema_version(data, target_version):
    """Validate schema version. Returns list of error strings."""
    errors = []
    if not isinstance(data, dict):
        errors.append("Top-level JSON must be an object.")
        return errors

    if "schema_version" not in data:
        errors.append("Missing required top-level field: 'schema_version'.")
        return errors

    version = data["schema_version"]
    if not isinstance(version, int):
        errors.append(f"'schema_version' must be an integer, got {type(version).__name__}.")
        return errors

    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(
            f"Unsupported schema_version {version}. Supported versions: {SUPPORTED_SCHEMA_VERSIONS}."
        )

    if version != target_version:
        errors.append(
            f"Schema version mismatch: payload has version {version}, but target is {target_version}."
        )

    return errors


def _validate_shots(data):
    """Validate shots array. Returns list of error strings."""
    errors = []
    if "shots" not in data:
        errors.append("Missing required top-level field: 'shots'.")
        return errors

    shots = data["shots"]
    if not isinstance(shots, list):
        errors.append("'shots' must be an array.")
        return errors

    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{i}] must be an object, got {type(shot).__name__}.")
            continue

        for field in REQUIRED_SHOT_FIELDS:
            if field not in shot:
                errors.append(f"shots[{i}] missing required field: '{field}'.")

        # Type normalization and validation
        if "duration" in shot:
            duration = shot["duration"]
            if not isinstance(duration, (int, float)) or isinstance(duration, bool):
                errors.append(f"shots[{i}].duration must be a number, got {type(duration).__name__}.")
            elif duration < 0:
                errors.append(f"shots[{i}].duration must be non-negative, got {duration}.")

        if "prompt_seed" in shot:
            seed = shot["prompt_seed"]
            if not isinstance(seed, int) or isinstance(seed, bool):
                errors.append(f"shots[{i}].prompt_seed must be an integer, got {type(seed).__name__}.")

        if "shot_id" in shot:
            shot_id = shot["shot_id"]
            if not isinstance(shot_id, str) or not shot_id.strip():
                errors.append(f"shots[{i}].shot_id must be a non-empty string.")

    return errors


def _validate_characters(data):
    """Validate characters array. Returns list of error strings."""
    errors = []
    if "characters" not in data:
        errors.append("Missing required top-level field: 'characters'.")
        return errors

    characters = data["characters"]
    if not isinstance(characters, list):
        errors.append("'characters' must be an array.")
        return errors

    for i, char in enumerate(characters):
        if not isinstance(char, dict):
            errors.append(f"characters[{i}] must be an object, got {type(char).__name__}.")
            continue

        for field in REQUIRED_CHARACTER_FIELDS:
            if field not in char:
                errors.append(f"characters[{i}] missing required field: '{field}'.")

        if "character_id" in char:
            cid = char["character_id"]
            if not isinstance(cid, str) or not cid.strip():
                errors.append(f"characters[{i}].character_id must be a non-empty string.")

        if "name" in char:
            name = char["name"]
            if not isinstance(name, str) or not name.strip():
                errors.append(f"characters[{i}].name must be a non-empty string.")

    return errors


def _validate_assets(data):
    """Validate assets array. Returns list of error strings."""
    errors = []
    if "assets" not in data:
        errors.append("Missing required top-level field: 'assets'.")
        return errors

    assets = data["assets"]
    if not isinstance(assets, list):
        errors.append("'assets' must be an array.")
        return errors

    for i, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{i}] must be an object, got {type(asset).__name__}.")
            continue

        for field in REQUIRED_ASSET_FIELDS:
            if field not in asset:
                errors.append(f"assets[{i}] missing required field: '{field}'.")

        if "asset_id" in asset:
            aid = asset["asset_id"]
            if not isinstance(aid, str) or not aid.strip():
                errors.append(f"assets[{i}].asset_id must be a non-empty string.")

        if "name" in asset:
            name = asset["name"]
            if not isinstance(name, str) or not name.strip():
                errors.append(f"assets[{i}].name must be a non-empty string.")

    return errors


def _validate_settings(data):
    """Validate settings object. Returns list of error strings."""
    errors = []
    if "settings" not in data:
        errors.append("Missing required top-level field: 'settings'.")
        return errors

    settings = data["settings"]
    if not isinstance(settings, dict):
        errors.append("'settings' must be an object.")
        return errors

    return errors


def _normalize_data(data):
    """Normalize data types in the validated storyboard data. Returns normalized dict."""
    normalized = {
        "schema_version": data.get("schema_version"),
        "shots": [],
        "characters": [],
        "assets": [],
        "settings": data.get("settings", {}),
    }

    for shot in data.get("shots", []):
        norm_shot = dict(shot)
        if "duration" in norm_shot and isinstance(norm_shot["duration"], int):
            norm_shot["duration"] = float(norm_shot["duration"])
        normalized["shots"].append(norm_shot)

    for char in data.get("characters", []):
        normalized["characters"].append(dict(char))

    for asset in data.get("assets", []):
        normalized["assets"].append(dict(asset))

    return normalized


def validate_storyboard(raw_text, schema_version):
    """
    Validate a storyboard JSON payload.

    Args:
        raw_text: JSON string or base64-encoded JSON string.
        schema_version: Target schema version (int).

    Returns:
        Tuple of (normalized_data_or_None, list_of_error_strings).
    """
    data, parse_error = _parse_payload(raw_text)
    if parse_error:
        return None, [parse_error]

    all_errors = []

    # Validate schema version
    all_errors.extend(_validate_schema_version(data, schema_version))

    # Only validate sub-structures if top-level is a dict
    if isinstance(data, dict):
        all_errors.extend(_validate_shots(data))
        all_errors.extend(_validate_characters(data))
        all_errors.extend(_validate_assets(data))
        all_errors.extend(_validate_settings(data))

    if all_errors:
        return None, all_errors

    # Normalize and return
    normalized = _normalize_data(data)
    return normalized, []


class PSN_StudioDatasetLoader:
    """
    Loads and validates the canonical storyboard JSON structure from a JSON text payload.

    Accepts either raw JSON text or a base64-encoded JSON string. Validates required
    fields (shot_id, duration, prompt_seed), schema version, and normalizes data types.
    Returns validated storyboard data and a list of validation errors.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "", "multiline": True}),
                "schema_version": ("INT", {"default": 1, "min": 1, "max": 10}),
            },
            "optional": {},
        }

    RETURN_TYPES = (PSN_STORYBOARD_DATA, "STRING")
    RETURN_NAMES = ("storyboard_data", "validation_errors")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Dataset"

    def run(self, path, schema_version):
        """
        Validate and normalize a storyboard JSON payload.

        Args:
            path: JSON string or base64-encoded JSON string.
            schema_version: Target schema version for validation.

        Returns:
            Tuple of (storyboard_data, validation_errors_string).
        """
        data, errors = validate_storyboard(path, schema_version)

        if errors:
            error_string = "\n".join(errors)
            return (None, error_string)

        return (data, "")


NODE_CLASS_MAPPINGS = {
    "PSN_StudioDatasetLoader": PSN_StudioDatasetLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StudioDatasetLoader": "Studio Dataset Loader",
}
