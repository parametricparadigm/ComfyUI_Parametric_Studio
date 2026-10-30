"""ParametricStudio: Checkpoint Quality Control Loop.

Tags checkpoints with quality scores and tags so downstream nodes can
curate / pick the best model. The registry is an in-memory dict that is
returned as a CUSTOM output; the node never touches the filesystem
(ComfyUI custom nodes should not write arbitrary files from a graph).
"""

import copy

CAT = "ParametricStudio/CheckpointQC"


def _new_registry():
    return {"checkpoints": {}}


def _validate_registry(reg):
    if not isinstance(reg, dict):
        raise TypeError("registry must be a dict")
    if "checkpoints" not in reg or not isinstance(reg["checkpoints"], dict):
        raise ValueError("registry must contain a 'checkpoints' dict")
    return reg


def _validate_score(score):
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise TypeError("quality_score must be a number")
    s = float(score)
    if s < 0.0 or s > 1.0:
        raise ValueError("quality_score must be in [0.0, 1.0]")
    return s


def _parse_tags(tags):
    if tags is None:
        return []
    if not isinstance(tags, str):
        raise TypeError("tags must be a string")
    out = []
    for part in tags.split(","):
        t = part.strip()
        if t and t not in out:
            out.append(t)
    return out


class PSN_CheckpointQualityTagger:
    """Tag a checkpoint with a quality score and tags in the registry."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoint_name": ("STRING", {"default": ""}),
                "quality_score": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "tags": ("STRING", {"default": ""}),
            },
            "optional": {
                "registry": ("CHECKPOINT_REGISTRY",),
            },
        }

    RETURN_TYPES = ("CHECKPOINT_REGISTRY",)
    RETURN_NAMES = ("UPDATED_REGISTRY",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, checkpoint_name, quality_score, tags, registry=None):
        if not isinstance(checkpoint_name, str) or not checkpoint_name.strip():
            raise ValueError("checkpoint_name must be a non-empty string")
        name = checkpoint_name.strip()
        score = _validate_score(quality_score)
        parsed = _parse_tags(tags)

        if registry is None:
            reg = _new_registry()
        else:
            reg = copy.deepcopy(_validate_registry(registry))

        entry = reg["checkpoints"].get(name)
        if entry is None:
            entry = {"quality_score": None, "tags": [], "history": []}
            reg["checkpoints"][name] = entry

        # keep a small history of previous scores (bounded)
        if entry.get("quality_score") is not None:
            entry.setdefault("history", []).append(entry["quality_score"])
            if len(entry["history"]) > 16:
                entry["history"] = entry["history"][-16:]

        entry["quality_score"] = score
        # merge tags, preserving order, no duplicates
        merged = list(entry.get("tags", []))
        for t in parsed:
            if t not in merged:
                merged.append(t)
        entry["tags"] = merged
        entry["updated"] = entry.get("updated", 0) + 1

        return (reg,)


class PSN_CheckpointRegistryLookup:
    """Look up a checkpoint entry; outputs its score, tags and a found flag."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "checkpoint_name": ("STRING", {"default": ""}),
                "registry": ("CHECKPOINT_REGISTRY",),
            },
        }

    RETURN_TYPES = ("FLOAT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("QUALITY_SCORE", "TAGS", "FOUND")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, checkpoint_name, registry):
        if not isinstance(checkpoint_name, str) or not checkpoint_name.strip():
            raise ValueError("checkpoint_name must be a non-empty string")
        reg = _validate_registry(registry)
        entry = reg["checkpoints"].get(checkpoint_name.strip())
        if entry is None:
            return (0.0, "", False)
        score = entry.get("quality_score")
        score = 0.0 if score is None else float(score)
        tags = ",".join(entry.get("tags", []))
        return (score, tags, True)


class PSN_CheckpointBestPicker:
    """Pick the checkpoint with the highest quality score from the registry."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "registry": ("CHECKPOINT_REGISTRY",),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("BEST_NAME", "BEST_SCORE", "HAS_ENTRY")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, registry):
        reg = _validate_registry(registry)
        best_name = ""
        best_score = 0.0
        has = False
        for name, entry in reg["checkpoints"].items():
            s = entry.get("quality_score")
            if s is None:
                continue
            s = float(s)
            if not has or s > best_score:
                best_name = name
                best_score = s
                has = True
        return (best_name, best_score, has)


NODE_CLASS_MAPPINGS = {
    "PSN_CheckpointQualityTagger": PSN_CheckpointQualityTagger,
    "PSN_CheckpointRegistryLookup": PSN_CheckpointRegistryLookup,
    "PSN_CheckpointBestPicker": PSN_CheckpointBestPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CheckpointQualityTagger": "Checkpoint Quality Tagger",
    "PSN_CheckpointRegistryLookup": "Checkpoint Registry Lookup",
    "PSN_CheckpointBestPicker": "Checkpoint Best Picker",
}
