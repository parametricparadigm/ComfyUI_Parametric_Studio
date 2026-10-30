"""ParametricStudio - Production Asset Metadata Standardizer.

ComfyUI custom nodes that standardize production metadata (studio_id, shot_id,
version, ...) on image/video assets.  Because ComfyUI passes tensors (IMAGE,
MASK, LATENT) between nodes rather than files, the metadata is carried in the
standard ComfyUI ``metadata`` dict that travels with the tensor (this is the
same mechanism ComfyUI uses to attach prompt info to saved images).  The
nodes therefore implement the *core* of the idea - inject, overwrite, validate
and size-check production tags - in a lossless, in-memory way.

What is NOT implemented (needs file I/O / third-party libs that are not
available here): writing EXIF/XMP into actual image files (Pillow) and audio
/video container tags (mutagen).  The metadata dict produced here can be
handed to a save node that performs the real file-level tagging.
"""

import json

import torch

CAT = "ParametricStudio/Metadata"

# Standard production keys every asset must carry.
REQUIRED_KEYS = ("studio_id", "shot_id", "version")

# Hard cap on the serialized metadata payload (bytes) to avoid corrupting
# files whose metadata segment has a fixed size limit.
MAX_METADATA_BYTES = 65536


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _as_tensor(asset):
    """Return the tensor payload of an IMAGE/MASK/LATENT input.

    Raises ``ValueError`` for anything that is not a tensor or a LATENT dict
    with a tensor under ``"samples"``.
    """
    if isinstance(asset, dict):
        if "samples" not in asset:
            raise ValueError("LATENT dict must contain a 'samples' tensor")
        return asset["samples"]
    if isinstance(asset, torch.Tensor):
        return asset
    raise ValueError("asset must be a torch.Tensor (IMAGE/MASK) or a LATENT dict")


def _existing_meta(asset):
    """Extract the current metadata dict from an asset, never mutating it."""
    if isinstance(asset, dict):
        meta = asset.get("metadata")
    else:
        meta = getattr(asset, "metadata", None)
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return dict(meta)
    raise ValueError("asset metadata must be a dict when present")


def _attach(asset, tensor, meta):
    """Return a *new* asset of the same kind carrying ``meta`` (never in place)."""
    if isinstance(asset, dict):
        out = dict(asset)
        out["samples"] = tensor
        out["metadata"] = meta
        return out
    new = tensor.clone() if tensor.is_leaf else tensor.detach().clone()
    new.metadata = meta
    return new


def _check_size(meta):
    """Raise if the serialized metadata would exceed the safe limit."""
    size = len(json.dumps(meta, separators=(",", ":")).encode("utf-8"))
    if size > MAX_METADATA_BYTES:
        raise ValueError(
            "metadata payload of %d bytes exceeds the %d byte limit" % (size, MAX_METADATA_BYTES)
        )


def _parse_metadata_dict(raw):
    """Parse the JSON ``metadata_dict`` input into a dict of str->str values."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        parsed = raw
    else:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata_dict is not valid JSON: %s" % exc)
    if not isinstance(parsed, dict):
        raise ValueError("metadata_dict must be a JSON object (dict)")
    cleaned = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("metadata keys must be non-empty strings")
        cleaned[key] = "" if value is None else str(value)
    return cleaned


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------

class PSN_MetadataInjector:
    """Write standard production tags (studio_id, shot_id, version, ...) into
    the asset's metadata, losslessly.  With ``overwrite`` False existing keys
    are preserved; with True the supplied keys replace any previous values."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset": ("IMAGE",),
                "metadata_dict": ("STRING", {"default": "{}", "multiline": True}),
                "overwrite": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("tagged_asset",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, asset, metadata_dict, overwrite):
        tensor = _as_tensor(asset)
        incoming = _parse_metadata_dict(metadata_dict)
        if not overwrite:
            merged = _existing_meta(asset)
            merged.update(incoming)
        else:
            merged = dict(incoming)
        _check_size(merged)
        return (_attach(asset, tensor, merged),)


class PSN_MetadataValidator:
    """Check that the required production tags are present on the asset.

    Returns ``is_valid`` (BOOLEAN) and ``missing_keys`` (STRING, comma
    separated, empty when valid)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "asset": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("is_valid", "missing_keys")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, asset):
        _as_tensor(asset)  # validate the payload is a real tensor
        meta = _existing_meta(asset)
        missing = [k for k in REQUIRED_KEYS if not str(meta.get(k, "")).strip()]
        return (len(missing) == 0, ",".join(missing))


NODE_CLASS_MAPPINGS = {
    "PSN_MetadataInjector": PSN_MetadataInjector,
    "PSN_MetadataValidator": PSN_MetadataValidator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MetadataInjector": "PSN Metadata Injector",
    "PSN_MetadataValidator": "PSN Metadata Validator",
}
