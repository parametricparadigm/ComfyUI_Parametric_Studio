"""PSN_Selective_Safetensors_Loader

Pure-logic, secure-by-design implementation of a *selective* safetensors loader.

This module does NOT open files, sockets, or use torch/safetensors. It only:
  * parses a JSON header (the first 8 bytes of a safetensors file are a
    little-endian uint64 length followed by that many bytes of JSON),
  * validates a comma-separated list of layer prefixes,
  * computes which tensor keys would be loaded vs. missing,
  * validates the device string against an allow-list,
  * and returns a deterministic, JSON-serialisable "load plan".

The node is intended to be paired with a downstream node that performs the
actual I/O. All inputs are plain values (strings, floats, ints); no file,
network, subprocess, or GPU access is performed here.
"""

import json
import struct

CAT = "ParametricStudio/Loaders"

_DEVICES = ("cuda", "cpu")


def _parse_safetensors_header(header_text):
    """Parse the JSON header of a safetensors file.

    Returns a dict mapping tensor name -> {"dtype": str, "shape": list[int],
    "data_offsets": [start, end]}. Raises ValueError on malformed input.
    """
    if not isinstance(header_text, str):
        raise ValueError("header must be a string")
    try:
        data = json.loads(header_text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON in safetensors header: %s" % exc) from exc
    if not isinstance(data, dict):
        raise ValueError("safetensors header must be a JSON object")
    # The "__metadata__" key is allowed and must be a dict (or absent).
    if "__metadata__" in data and not isinstance(data["__metadata__"], dict):
        raise ValueError("__metadata__ must be an object")
    tensors = {}
    for key, value in data.items():
        if key == "__metadata__":
            continue
        if not isinstance(value, dict):
            raise ValueError("tensor entry %r must be an object" % key)
        dtype = value.get("dtype")
        shape = value.get("shape")
        offsets = value.get("data_offsets")
        if not isinstance(dtype, str) or not dtype:
            raise ValueError("tensor %r missing valid dtype" % key)
        if not isinstance(shape, list) or not all(isinstance(s, int) and s >= 0 for s in shape):
            raise ValueError("tensor %r missing valid shape" % key)
        if (not isinstance(offsets, list) or len(offsets) != 2
                or not all(isinstance(o, int) and o >= 0 for o in offsets)
                or offsets[0] > offsets[1]):
            raise ValueError("tensor %r missing valid data_offsets" % key)
        tensors[key] = {"dtype": dtype, "shape": list(shape), "data_offsets": list(offsets)}
    return tensors


def _parse_layer_spec(layers):
    """Parse a comma-separated layer prefix list into a clean list of prefixes."""
    if not isinstance(layers, str):
        raise ValueError("layers must be a string")
    parts = [p.strip() for p in layers.split(",")]
    cleaned = [p for p in parts if p]
    if not cleaned:
        raise ValueError("layers list is empty")
    # Reject anything that looks like a path traversal or contains NUL.
    for p in cleaned:
        if "\x00" in p or ".." in p:
            raise ValueError("invalid layer prefix: %r" % p)
    return cleaned


def _select_keys(all_keys, prefixes):
    """Return (selected, missing) key lists given a list of prefixes.

    A key is selected if it equals a prefix or starts with prefix + ".".
    """
    selected = []
    missing = []
    for key in sorted(all_keys):
        hit = False
        for p in prefixes:
            if key == p or key.startswith(p + "."):
                hit = True
                break
        (selected if hit else missing).append(key)
    return selected, missing


def _build_load_plan(header_text, layers, device):
    """Core pure-logic: validate inputs and produce a load plan dict."""
    if device not in _DEVICES:
        raise ValueError("device must be one of %s" % (", ".join(_DEVICES)))
    prefixes = _parse_layer_spec(layers)
    tensors = _parse_safetensors_header(header_text)
    all_keys = list(tensors.keys())
    selected, missing = _select_keys(all_keys, prefixes)
    selected_info = {k: tensors[k] for k in selected}
    return {
        "device": device,
        "requested_prefixes": prefixes,
        "selected_keys": selected,
        "missing_keys": missing,
        "selected_tensors": selected_info,
        "total_keys": len(all_keys),
        "selected_count": len(selected),
        "missing_count": len(missing),
    }


class PSN_SelectiveSafetensorsLoader:
    """Plan a selective safetensors load (pure logic; no I/O).

    Inputs are plain values. The `header` input is the JSON text that would
    appear after the 8-byte length prefix of a real safetensors file. The
    node returns a JSON-serialisable load plan describing which tensor keys
    would be loaded, which would be missing, and the target device.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "", "multiline": False}),
                "header": ("STRING", {"default": "{}", "multiline": True}),
                "layers": ("STRING", {"default": "", "multiline": False}),
                "device": (list(_DEVICES),),
            },
            "optional": {
                "max_keys": ("INT", {"default": 100000, "min": 1, "max": 1000000, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("load_plan_json", "missing_keys", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, path, header, layers, device, max_keys=100000):
        try:
            plan = _build_load_plan(header, layers, device)
        except ValueError as exc:
            return ("{}", "", "error: %s" % exc)
        # Enforce a soft cap on the number of keys reported to keep output bounded.
        if plan["total_keys"] > max_keys:
            plan["selected_keys"] = plan["selected_keys"][:max_keys]
            plan["missing_keys"] = plan["missing_keys"][:max_keys]
            plan["selected_tensors"] = {
                k: plan["selected_tensors"][k] for k in plan["selected_keys"]
            }
            plan["truncated"] = True
        plan["path"] = path
        plan_json = json.dumps(plan, sort_keys=True, separators=(",", ":"))
        missing = ",".join(plan["missing_keys"])
        reason = "ok: %d/%d keys selected on %s" % (
            plan["selected_count"], plan["total_keys"], plan["device"])
        return (plan_json, missing, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_SelectiveSafetensorsLoader": PSN_SelectiveSafetensorsLoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SelectiveSafetensorsLoader": "PSN Selective Safetensors Loader",
}
