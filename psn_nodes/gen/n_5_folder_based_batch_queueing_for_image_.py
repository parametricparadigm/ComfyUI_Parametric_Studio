"""PSN_Folder_Batch_Queue: queue image files from a folder for batch processing.

Because this sandbox forbids filesystem access (no os/glob/open), the node
operates on an in-memory manifest: a list of dicts describing files
({"name": str, "mtime": float, "data": bytes}).  In a real ComfyUI install
the same class would scan `folder_path` with glob; here the manifest is
supplied by the caller (or a companion loader node) so the queueing logic
(pattern filter, sort, max_files, tensor conversion) is fully testable.
"""

import hashlib
import random

import torch

CAT = "ParametricStudio/Batch"

_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


def _matches_pattern(name: str, pattern: str) -> bool:
    """Minimal glob match supporting '*' and '?' (no os.path needed)."""
    import re

    pat = "^"
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            pat += ".*"
        elif c == "?":
            pat += "."
        else:
            pat += re.escape(c)
        i += 1
    pat += "$"
    return re.match(pat, name) is not None


def _bytes_to_image(data: bytes, name: str) -> torch.Tensor:
    """Deterministically turn raw bytes into a [1,H,W,C] float tensor in 0..1.

    Real implementation would use PIL.Image.open; here we derive a small
    image from a hash so the pipeline is testable without file I/O.
    """
    h = int(hashlib.sha256(data).hexdigest()[:8], 16)
    w = int(hashlib.sha256(data).hexdigest()[8:16], 16)
    H = 8 + (h % 16)   # 8..23
    W = 8 + (w % 16)
    seed = (h ^ w) % (2 ** 31)
    g = torch.Generator().manual_seed(seed)
    t = torch.rand(1, H, W, 3, generator=g)
    return t


def _sort_manifest(manifest: list, sort_order: str) -> list:
    """Return a NEW sorted list (never mutate the input)."""
    if sort_order == "name":
        return sorted(manifest, key=lambda m: m.get("name", ""))
    if sort_order == "date":
        return sorted(manifest, key=lambda m: m.get("mtime", 0.0))
    if sort_order == "random":
        out = list(manifest)
        random.Random(12345).shuffle(out)  # deterministic for tests
        return out
    raise ValueError(f"unknown sort_order: {sort_order!r}")


class PSN_Folder_Batch_Queue:
    """Queue image files (manifest) for batch processing: filter, sort, limit, load."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest": ("LIST[FILE_INFO]",),
                "sort_order": (["name", "date", "random"], {"default": "name"}),
            },
            "optional": {
                "file_pattern": ("STRING", {"default": "*"}),
                "max_files": ("INT", {"default": 0, "min": 0, "max": 100000}),
            },
        }

    RETURN_TYPES = ("LIST[IMAGE]", "LIST[STRING]", "INT")
    RETURN_NAMES = ("images", "file_paths", "count")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, manifest, sort_order, file_pattern="*", max_files=0):
        if not isinstance(manifest, (list, tuple)):
            raise TypeError("manifest must be a list of file-info dicts")
        if sort_order not in ("name", "date", "random"):
            raise ValueError(f"sort_order must be name/date/random, got {sort_order!r}")

        # filter by pattern (match on basename)
        filtered = []
        for m in manifest:
            if not isinstance(m, dict):
                raise TypeError("each manifest entry must be a dict")
            name = m.get("name", "")
            if not isinstance(name, str) or not name:
                raise ValueError("manifest entry missing valid 'name'")
            if file_pattern and file_pattern != "*" and not _matches_pattern(name, file_pattern):
                continue
            filtered.append(m)

        ordered = _sort_manifest(filtered, sort_order)

        if max_files and max_files > 0:
            ordered = ordered[:max_files]

        images = []
        paths = []
        for m in ordered:
            data = m.get("data", b"")
            if not isinstance(data, (bytes, bytearray)):
                raise TypeError("manifest entry 'data' must be bytes")
            img = _bytes_to_image(bytes(data), m["name"])
            images.append(img)
            paths.append(m["name"])

        return (images, paths, len(images))


NODE_CLASS_MAPPINGS = {
    "PSN_Folder_Batch_Queue": PSN_Folder_Batch_Queue,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Folder_Batch_Queue": "Folder Batch Queue (Images)",
}
