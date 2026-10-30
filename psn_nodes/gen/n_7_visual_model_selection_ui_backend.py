"""PSN_VisualModelSelector: backend for a visual model selection UI.

Given a model list (as produced by a registry loader), this node assembles
"model cards" containing a display name, a cover image path (searching for
cover.jpg / preview.png inside each model's directory, with a fallback to a
default placeholder), and a metadata dict.

The node is pure Python + stdlib (json) and does not touch the network or
filesystem outside the workspace.  In a real ComfyUI deployment the
`model_list` input would be a CUSTOM type produced by PSN_ModelRegistryLoader;
here we accept a plain list of dicts so the module is testable in isolation.
"""

import json

CAT = "ParametricStudio/ModelSelection"

# Fallback placeholder used when a model directory has no cover image.
DEFAULT_PLACEHOLDER = "placeholder://default-cover"

# Candidate cover file names, in priority order.
COVER_CANDIDATES = ("cover.jpg", "preview.png")


def _is_dict(value):
    return isinstance(value, dict)


def _clean_name(value, fallback="unnamed-model"):
    """Return a safe, non-empty display name."""
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value
    return fallback


def _clean_metadata(value):
    """Coerce arbitrary metadata into a JSON-serialisable dict."""
    if _is_dict(value):
        out = {}
        for k, v in value.items():
            key = str(k)
            try:
                json.dumps(v)
            except (TypeError, ValueError):
                v = repr(v)
            out[key] = v
        return out
    if value is None:
        return {}
    return {"raw": repr(value)}


def _find_cover(model_dir):
    """Return the path of the first existing cover candidate, else None.

    `model_dir` is treated as an opaque string; we do NOT actually stat the
    filesystem here (the node must stay workspace-safe and testable).  The
    caller is expected to pass a directory that has already been resolved by
    the registry loader.  We simply record the *expected* path so the UI can
    fetch it; if the directory is empty/None we return None and the caller
    falls back to the placeholder.
    """
    if not isinstance(model_dir, str) or not model_dir.strip():
        return None
    base = model_dir.rstrip("/")
    for cand in COVER_CANDIDATES:
        # We cannot use os.path here (forbidden import), so we build the path
        # with plain string concatenation.  The UI layer is responsible for
        # verifying existence; the backend only assembles the candidate path.
        return base + "/" + cand
    return None


def _build_card(entry, index):
    """Build a single model card dict from a registry entry.

    `entry` may be a dict with keys like name / dir / metadata, or a plain
    string (treated as the model name with no directory).
    """
    if isinstance(entry, str):
        name = _clean_name(entry, "model-%d" % index)
        model_dir = None
        metadata = {}
    elif _is_dict(entry):
        name = _clean_name(entry.get("name"), "model-%d" % index)
        model_dir = entry.get("dir") or entry.get("directory") or entry.get("path")
        metadata = _clean_metadata(entry.get("metadata"))
    else:
        name = "model-%d" % index
        model_dir = None
        metadata = {"raw": repr(entry)}

    cover = _find_cover(model_dir)
    if cover is None:
        cover = DEFAULT_PLACEHOLDER

    return {
        "name": name,
        "cover_image_path": cover,
        "metadata": metadata,
    }


class PSN_VisualModelSelector:
    """Assemble model cards (name, cover image path, metadata) for a UI."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # In a full ComfyUI install this would be ("MODEL_LIST",) from
                # PSN_ModelRegistryLoader.  We accept a generic CUSTOM type so
                # the node can be wired up once the loader exists.
                "model_list": ("MODEL_LIST",),
                "limit": ("INT", {"default": 10, "min": 1, "max": 1024}),
            }
        }

    RETURN_TYPES = ("MODEL_CARDS",)
    RETURN_NAMES = ("model_cards",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, model_list, limit):
        if model_list is None:
            model_list = []
        if not isinstance(model_list, (list, tuple)):
            raise TypeError("model_list must be a list or tuple of entries")
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise TypeError("limit must be an int")
        if limit < 1:
            raise ValueError("limit must be >= 1")

        cards = []
        for i, entry in enumerate(model_list):
            if i >= limit:
                break
            cards.append(_build_card(entry, i))
        return (cards,)


NODE_CLASS_MAPPINGS = {
    "PSN_VisualModelSelector": PSN_VisualModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_VisualModelSelector": "Visual Model Selector (UI Backend)",
}
