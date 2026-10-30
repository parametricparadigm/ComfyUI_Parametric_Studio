"""PSN_Model_Merger: pure-logic model merging and inspection.

This module implements the *pure-logic, secure-by-design* part of a model
merger. It does NOT import torch, ComfyUI, or any GPU/IO library. Instead it
operates on plain Python values:

  * A "model" is represented as a JSON text string mapping layer names to
    flat lists of numeric weights (e.g. '{"conv1": [1.0, 2.0], "fc": [0.5]}').
  * Merging is a linear interpolation (lerp) of the weight vectors.
  * Inspection lists layer names and counts total parameters.

All functions take plain values (strings, numbers) and return plain values
(strings, ints, tuples). No sockets, files, network, subprocess, eval/exec,
or dunder tricks are used.
"""

import json

CAT = "ParametricStudio/Model"


def _parse_model(model_text):
    """Parse a JSON model string into a dict of layer -> list of floats.

    Returns (model_dict, error_string). On success error_string is None.
    """
    if not isinstance(model_text, str):
        return None, "model must be a JSON string"
    try:
        data = json.loads(model_text)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, "invalid JSON: %s" % exc
    if not isinstance(data, dict):
        return None, "model JSON must be an object mapping layers to weight lists"
    for name, weights in data.items():
        if not isinstance(name, str):
            return None, "layer names must be strings"
        if not isinstance(weights, list):
            return None, "weights for layer '%s' must be a list" % name
        for w in weights:
            if not isinstance(w, (int, float)) or isinstance(w, bool):
                return None, "weights must be numbers, got %r" % (w,)
    return data, None


def _lerp(a, b, weight_a, weight_b):
    """Linearly interpolate two weight lists.

    If lengths differ, the shorter list is zero-padded to the longer length.
    """
    n = max(len(a), len(b))
    out = []
    for i in range(n):
        va = a[i] if i < len(a) else 0.0
        vb = b[i] if i < len(b) else 0.0
        out.append(weight_a * va + weight_b * vb)
    return out


def merge_models(model_a_text, model_b_text, weight_a, weight_b):
    """Merge two model JSON strings via linear interpolation.

    Returns (merged_json_string, error_string).
    """
    model_a, err_a = _parse_model(model_a_text)
    if err_a:
        return None, "model_a: %s" % err_a
    model_b, err_b = _parse_model(model_b_text)
    if err_b:
        return None, "model_b: %s" % err_b

    if not isinstance(weight_a, (int, float)) or isinstance(weight_a, bool):
        return None, "weight_a must be a number"
    if not isinstance(weight_b, (int, float)) or isinstance(weight_b, bool):
        return None, "weight_b must be a number"

    # Union of all layer names, sorted for determinism
    all_layers = sorted(set(model_a.keys()) | set(model_b.keys()))
    merged = {}
    for layer in all_layers:
        wa = model_a.get(layer, [])
        wb = model_b.get(layer, [])
        merged[layer] = _lerp(wa, wb, weight_a, weight_b)

    return json.dumps(merged), None


def inspect_model(model_text):
    """Inspect a model JSON string.

    Returns (layer_names_string, param_count, error_string).
    """
    model, err = _parse_model(model_text)
    if err:
        return None, 0, err
    layer_names = ", ".join(sorted(model.keys()))
    param_count = sum(len(w) for w in model.values())
    return layer_names, param_count, None


class PSN_Merge_Checkpoints:
    """Linearly interpolates the weights of two models represented as JSON text."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_a": ("STRING", {"default": "{}", "multiline": True}),
                "model_b": ("STRING", {"default": "{}", "multiline": True}),
                "weight_a": ("FLOAT", {"default": 0.5, "min": -1e9, "max": 1e9, "step": 0.001}),
                "weight_b": ("FLOAT", {"default": 0.5, "min": -1e9, "max": 1e9, "step": 0.001}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("merged_model", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_a, model_b, weight_a, weight_b):
        merged, err = merge_models(model_a, model_b, weight_a, weight_b)
        return (merged if merged is not None else "{}", err if err else "")


class PSN_Inspect_Model:
    """Lists all layer names and counts total parameters for a model JSON string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("layer_names", "param_count", "error")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model):
        layer_names, param_count, err = inspect_model(model)
        return (
            layer_names if layer_names is not None else "",
            param_count,
            err if err else "",
        )


NODE_CLASS_MAPPINGS = {
    "PSN_Merge_Checkpoints": PSN_Merge_Checkpoints,
    "PSN_Inspect_Model": PSN_Inspect_Model,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Merge_Checkpoints": "PSN Merge Checkpoints",
    "PSN_Inspect_Model": "PSN Inspect Model",
}
