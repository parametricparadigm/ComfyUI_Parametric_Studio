"""PSN Workflow Preset Management nodes for ComfyUI.

Provides PSN_PresetLoader and PSN_PresetSaver nodes that manage
workflow preset graphs as JSON-serializable Python dicts.
"""

import json

CAT = "ParametricStudio/PresetManagement"


def _validate_graph(graph):
    """Validate that a graph dict has the expected structure."""
    if not isinstance(graph, dict):
        raise ValueError("Graph must be a dict, got %s" % type(graph).__name__)
    if "nodes" not in graph:
        raise ValueError("Graph must contain a 'nodes' key")
    if not isinstance(graph["nodes"], list):
        raise ValueError("Graph 'nodes' must be a list")
    for i, node in enumerate(graph["nodes"]):
        if not isinstance(node, dict):
            raise ValueError("Node at index %d must be a dict" % i)
        if "id" not in node:
            raise ValueError("Node at index %d missing 'id'" % i)
        if "type" not in node:
            raise ValueError("Node at index %d missing 'type'" % i)
    return True


def _deep_copy(obj):
    """Deep copy via JSON round-trip (only JSON-serializable data)."""
    return json.loads(json.dumps(obj))


class PSN_PresetLoader:
    """Loads a predefined workflow preset from a JSON string.

    The preset is passed as a JSON-encoded string (since direct file I/O
    is not available in this sandbox). The preset_dir is accepted for
    compatibility but not used for actual I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": ("STRING", {"default": "default"}),
                "preset_dir": ("STRING", {"default": "./presets"}),
                "preset_json": ("STRING", {"default": "{}"}),
            }
        }

    RETURN_TYPES = ("GRAPH",)
    RETURN_NAMES = ("GRAPH",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, preset_name, preset_dir, preset_json):
        if not isinstance(preset_name, str):
            raise ValueError("preset_name must be a string")
        if not isinstance(preset_dir, str):
            raise ValueError("preset_dir must be a string")
        if not isinstance(preset_json, str):
            raise ValueError("preset_json must be a string")

        try:
            graph = json.loads(preset_json)
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON in preset_json: %s" % e)

        _validate_graph(graph)

        # Return a deep copy so the caller cannot mutate our internal state
        return (_deep_copy(graph),)


class PSN_PresetSaver:
    """Saves a workflow graph as a JSON string (preset).

    Serializes the graph dict to a JSON string. The preset_dir is
    accepted for compatibility but not used for actual I/O.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph": ("GRAPH",),
                "preset_name": ("STRING", {"default": "default"}),
                "preset_dir": ("STRING", {"default": "./presets"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("preset_path",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, graph, preset_name, preset_dir):
        if not isinstance(preset_name, str):
            raise ValueError("preset_name must be a string")
        if not isinstance(preset_dir, str):
            raise ValueError("preset_dir must be a string")

        _validate_graph(graph)

        # Serialize to JSON string
        json_str = json.dumps(graph, sort_keys=True, indent=2)

        # Simulate a file path (no actual I/O)
        path = preset_dir.rstrip("/") + "/" + preset_name + ".json"

        return (path,)


NODE_CLASS_MAPPINGS = {
    "PSN_PresetLoader": PSN_PresetLoader,
    "PSN_PresetSaver": PSN_PresetSaver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PresetLoader": "PSN Preset Loader",
    "PSN_PresetSaver": "PSN Preset Saver",
}
