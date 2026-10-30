"""Expose Studio Workflows as Plugins.

Pure-logic, secure-by-design implementation of a workflow plugin exposer.
This module wraps a ComfyUI-style graph (provided as JSON text) into a
standardized plugin descriptor, validates input/output schemas against the
graph's actual nodes, and simulates an endpoint URL.

No network, file, OS, subprocess, eval/exec, or torch/comfy imports are used.
All functions take plain values (strings, dicts) and return plain values.
"""

import json
import re
import hashlib

# Allowed node types for plugin exposure (allow-list for security)
ALLOWED_NODE_TYPES = frozenset({
    "KSampler", "CheckpointLoaderSimple", "CLIPTextEncode", "VAEDecode",
    "VAEEncode", "LoadImage", "SaveImage", "PreviewImage", "LoraLoader",
    "ControlNetLoader", "ControlNetApplyAdvanced", "CLIPSetLastLayer",
    "EmptyLatentImage", "LatentUpscale", "ImageScale", "ImageCompositeMasked",
    "MaskComposite", "InvertMask", "GrowMask", "FeatherMask", "ImageBlur",
    "ImageSharpen", "ImageDenoise", "ImageUpscaleWithModel", "UpscaleModelLoader",
    "ModelSamplingSD3", "ModelSamplingAuraFlow", "ModelSamplingFlux",
    "ModelSamplingSD3Turbo", "ModelSamplingAuraFlowTurbo", "ModelSamplingFluxTurbo",
})

# Maximum allowed graph size in characters to prevent abuse
MAX_GRAPH_JSON_LENGTH = 1_000_000

# Maximum number of nodes allowed in a plugin graph
MAX_NODE_COUNT = 500

# Plugin API version
PLUGIN_API_VERSION = "1.0.0"

# Simulated base URL for plugin endpoints
SIMULATED_BASE_URL = "https://plugins.parametricstudio.local/v1"


def _validate_graph_json(graph_json: str) -> dict:
    """Parse and validate the graph JSON structure.

    Returns the parsed graph dict. Raises ValueError on invalid input.
    """
    if not isinstance(graph_json, str):
        raise ValueError("graph_json must be a string")
    if len(graph_json) > MAX_GRAPH_JSON_LENGTH:
        raise ValueError(f"graph_json exceeds maximum length of {MAX_GRAPH_JSON_LENGTH} characters")
    try:
        graph = json.loads(graph_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in graph_json: {e}")
    if not isinstance(graph, dict):
        raise ValueError("graph_json must parse to a JSON object")
    if "nodes" not in graph:
        raise ValueError("graph_json must contain a 'nodes' key")
    nodes = graph["nodes"]
    if not isinstance(nodes, list):
        raise ValueError("'nodes' must be a list")
    if len(nodes) > MAX_NODE_COUNT:
        raise ValueError(f"Graph contains {len(nodes)} nodes; maximum allowed is {MAX_NODE_COUNT}")
    return graph


def _extract_node_ids(graph: dict) -> list:
    """Extract node IDs from the graph, validating each node entry."""
    node_ids = []
    for i, node in enumerate(graph["nodes"]):
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {i} is not an object")
        if "id" not in node:
            raise ValueError(f"Node at index {i} is missing 'id'")
        node_id = node["id"]
        if not isinstance(node_id, (int, str)):
            raise ValueError(f"Node id at index {i} must be an integer or string")
        node_ids.append(str(node_id))
    return node_ids


def _validate_node_types(graph: dict) -> list:
    """Validate that all node types are in the allow-list. Returns list of node types."""
    node_types = []
    for i, node in enumerate(graph["nodes"]):
        if "type" not in node:
            raise ValueError(f"Node at index {i} is missing 'type'")
        node_type = node["type"]
        if not isinstance(node_type, str):
            raise ValueError(f"Node type at index {i} must be a string")
        if node_type not in ALLOWED_NODE_TYPES:
            raise ValueError(
                f"Node type '{node_type}' at index {i} is not in the allowed node types list"
            )
        node_types.append(node_type)
    return node_types


def _validate_schema(schema_json: str, schema_name: str) -> dict:
    """Parse and validate a JSON schema string. Returns the parsed schema dict.

    An empty object '{}' is treated as a valid empty schema (no constraints).
    """
    if not isinstance(schema_json, str):
        raise ValueError(f"{schema_name} must be a string")
    if not schema_json.strip():
        raise ValueError(f"{schema_name} must not be empty")
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {schema_name}: {e}")
    if not isinstance(schema, dict):
        raise ValueError(f"{schema_name} must parse to a JSON object")
    # Allow empty object as a valid "no constraints" schema
    if schema == {}:
        return schema
    if "type" not in schema:
        raise ValueError(f"{schema_name} must contain a 'type' key")
    if schema["type"] not in ("object", "array", "string", "number", "integer", "boolean"):
        raise ValueError(f"{schema_name} has unsupported type: {schema['type']}")
    return schema


def _validate_schema_against_graph(schema: dict, graph: dict, schema_name: str) -> None:
    """Validate that the schema is compatible with the graph structure.

    For input schemas: checks that referenced node IDs exist in the graph.
    For output schemas: checks that referenced node IDs exist in the graph.
    """
    if schema.get("type") != "object":
        return
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError(f"{schema_name} 'properties' must be an object")
    node_ids = set(_extract_node_ids(graph))
    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            continue
        source_node = prop_def.get("source_node")
        if source_node is not None:
            source_node_str = str(source_node)
            if source_node_str not in node_ids:
                raise ValueError(
                    f"{schema_name} property '{prop_name}' references node '{source_node_str}' "
                    f"which does not exist in the graph"
                )


def _generate_plugin_id(plugin_name: str, graph: dict) -> str:
    """Generate a deterministic plugin ID from the plugin name and graph content."""
    graph_str = json.dumps(graph, sort_keys=True)
    combined = f"{plugin_name}:{graph_str}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def _generate_endpoint_url(plugin_id: str) -> str:
    """Generate a simulated endpoint URL for the plugin."""
    return f"{SIMULATED_BASE_URL}/plugins/{plugin_id}"


def _sanitize_plugin_name(plugin_name: str) -> str:
    """Validate and sanitize the plugin name."""
    if not isinstance(plugin_name, str):
        raise ValueError("plugin_name must be a string")
    if not plugin_name.strip():
        raise ValueError("plugin_name must not be empty")
    if len(plugin_name) > 128:
        raise ValueError("plugin_name must not exceed 128 characters")
    # Allow alphanumeric, underscores, hyphens, and dots
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', plugin_name):
        raise ValueError(
            "plugin_name may only contain alphanumeric characters, underscores, hyphens, and dots"
        )
    return plugin_name


def build_plugin_descriptor(
    graph_json: str,
    plugin_name: str,
    input_schema: str,
    output_schema: str,
) -> dict:
    """Build a plugin descriptor from a workflow graph and schemas.

    Args:
        graph_json: JSON string of the ComfyUI workflow graph.
        plugin_name: Name of the plugin.
        input_schema: JSON string defining the plugin's input schema.
        output_schema: JSON string defining the plugin's output schema.

    Returns:
        A dict containing the plugin descriptor with graph, schemas, and metadata.

    Raises:
        ValueError: If any input is invalid.
    """
    # Validate and parse graph
    graph = _validate_graph_json(graph_json)
    node_ids = _extract_node_ids(graph)
    node_types = _validate_node_types(graph)

    # Validate plugin name
    sanitized_name = _sanitize_plugin_name(plugin_name)

    # Validate schemas
    input_schema_dict = _validate_schema(input_schema, "input_schema")
    output_schema_dict = _validate_schema(output_schema, "output_schema")

    # Validate schemas against graph
    _validate_schema_against_graph(input_schema_dict, graph, "input_schema")
    _validate_schema_against_graph(output_schema_dict, graph, "output_schema")

    # Generate plugin ID and endpoint URL
    plugin_id = _generate_plugin_id(sanitized_name, graph)
    endpoint_url = _generate_endpoint_url(plugin_id)

    # Build descriptor
    descriptor = {
        "plugin_id": plugin_id,
        "plugin_name": sanitized_name,
        "api_version": PLUGIN_API_VERSION,
        "graph": graph,
        "node_ids": node_ids,
        "node_types": node_types,
        "input_schema": input_schema_dict,
        "output_schema": output_schema_dict,
        "endpoint_url": endpoint_url,
        "metadata": {
            "node_count": len(node_ids),
            "graph_hash": hashlib.sha256(json.dumps(graph, sort_keys=True).encode("utf-8")).hexdigest(),
            "created_by": "PSN_Workflow_Plugin_Exposer",
        },
    }
    return descriptor


class PSN_Workflow_Plugin_Exposer:
    """Expose a ComfyUI workflow graph as a standardized plugin descriptor.

    Validates the graph structure, node types, and input/output schemas,
    then wraps everything into a plugin descriptor with a simulated endpoint URL.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph_json": ("STRING", {"default": "{}", "multiline": True}),
                "plugin_name": ("STRING", {"default": "my_plugin"}),
                "input_schema": ("STRING", {"default": "{}", "multiline": True}),
                "output_schema": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("plugin_descriptor", "endpoint_url")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Plugins"

    def run(self, graph_json, plugin_name, input_schema, output_schema):
        descriptor = build_plugin_descriptor(
            graph_json=graph_json,
            plugin_name=plugin_name,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        return (descriptor, descriptor["endpoint_url"])


NODE_CLASS_MAPPINGS = {
    "PSN_Workflow_Plugin_Exposer": PSN_Workflow_Plugin_Exposer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Workflow_Plugin_Exposer": "Workflow Plugin Exposer",
}
