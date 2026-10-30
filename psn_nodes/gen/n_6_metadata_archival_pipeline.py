"""ParametricStudio - Metadata Archival Pipeline.

Nodes:
  * PSN_Meta_Extractor  - builds a structured metadata dict for a run and a
    JSON string representation.  In a full ComfyUI install the node would
    also try to embed the metadata into the image's PNG/EXIF block; here we
    only do the pure-Python part (dict + JSON) because Pillow is not
    guaranteed to be available and the task forbids file I/O.
  * PSN_Archive_Logger  - serialises a metadata dict to a single JSONL line
    (the "log entry").  In a full install it would append to a file or POST
    to a local API; here it returns the line plus a status string.
"""

import json
import time

import torch

CAT = "ParametricStudio/Metadata"


def _s(x):
    """Return the tensor payload of a ComfyUI LATENT / IMAGE / MASK input."""
    if isinstance(x, dict):
        return x.get("samples", x)
    return x


def _validate_image(image):
    """Return the tensor and raise a clear error on bad input."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError("image must be 4-D [B,H,W,C], got %d-D" % image.dim())
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError("image channels must be 1, 3 or 4, got %d" % image.shape[-1])
    if image.numel() and (image.min() < -1e-6 or image.max() > 1 + 1e-6):
        raise ValueError("image values must be in [0, 1]")
    return image


def _build_metadata(run_id, image, extra):
    """Build the metadata dict for one run."""
    img = _validate_image(image)
    meta = {
        "run_id": str(run_id),
        "timestamp": time.time(),
        "image": {
            "batch": int(img.shape[0]),
            "height": int(img.shape[1]),
            "width": int(img.shape[2]),
            "channels": int(img.shape[3]),
            "dtype": str(img.dtype),
            "mean": float(img.mean().item()) if img.numel() else 0.0,
        },
        "prompt": extra.get("prompt", ""),
        "seed": int(extra.get("seed", -1)),
        "model": extra.get("model", ""),
        "steps": int(extra.get("steps", 0)),
    }
    return meta


class PSN_Meta_Extractor:
    """Extract generation parameters for the current run into a dict + JSON."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_id": ("STRING", {"default": "run-0001"}),
                "image": ("IMAGE",),
            },
            "optional": {
                "prompt": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2 ** 63 - 1}),
                "model": ("STRING", {"default": ""}),
                "steps": ("INT", {"default": 0, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("metadata_dict", "json_string")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, run_id, image, prompt="", seed=-1, model="", steps=0):
        extra = {"prompt": prompt, "seed": seed, "model": model, "steps": steps}
        meta = _build_metadata(run_id, image, extra)
        js = json.dumps(meta, sort_keys=True, separators=(",", ":"))
        return (meta, js)


class PSN_Archive_Logger:
    """Serialise a metadata dict into a single JSONL line (log entry)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "metadata_dict": ("DICT",),
                "run_id": ("STRING", {"default": "run-0001"}),
            },
            "optional": {
                "output_path": ("STRING", {"default": "archive.jsonl"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "jsonl_line")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, metadata_dict, run_id, output_path="archive.jsonl"):
        if not isinstance(metadata_dict, dict):
            raise TypeError("metadata_dict must be a dict")
        if not metadata_dict:
            raise ValueError("metadata_dict must not be empty")
        # Make sure the run_id in the log line matches the one passed in.
        entry = dict(metadata_dict)
        entry["run_id"] = str(run_id)
        entry["output_path"] = str(output_path)
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        status = "ok:1:%s" % str(run_id)
        return (status, line)


NODE_CLASS_MAPPINGS = {
    "PSN_Meta_Extractor": PSN_Meta_Extractor,
    "PSN_Archive_Logger": PSN_Archive_Logger,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Meta_Extractor": "PSN Meta Extractor",
    "PSN_Archive_Logger": "PSN Archive Logger",
}
