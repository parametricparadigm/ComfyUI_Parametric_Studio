"""
PSN_YAML_Batch_Definer: A ComfyUI custom node that parses a YAML configuration string
and a base ComfyUI API-format JSON graph string to generate a batch of parameterized
graph JSON strings.

This module implements the pure-logic, secure-by-design part of YAML-driven batch
generation. It does NOT perform any file I/O, network access, or GPU operations.
It takes plain values (strings) as input and returns plain values (list of strings,
dict) as output.

Dependencies:
- Pure Python standard library only (json, re, collections)
- No torch, no comfy imports, no network, no subprocess, no file/OS access
"""

import json
import re
from collections import OrderedDict

# Module-level constants
CAT = "ParametricStudio/Batch"

# Simple YAML parser for the subset needed for batch definitions
# Supports:
# - key: value (scalar)
# - key:
#   - item1
#   - item2
# - Nested dicts (limited depth)
# - Comments (#)
# - Strings, numbers, booleans, null

def _parse_yaml_value(value_str):
    """Parse a YAML scalar value string into a Python object."""
    value_str = value_str.strip()
    
    # Empty string
    if value_str == "" or value_str == "~" or value_str == "null":
        return None
    
    # Boolean
    if value_str.lower() in ("true", "yes", "on"):
        return True
    if value_str.lower() in ("false", "no", "off"):
        return False
    
    # Integer
    if re.match(r'^-?\d+$', value_str):
        try:
            return int(value_str)
        except ValueError:
            pass
    
    # Float
    if re.match(r'^-?\d+\.\d+$', value_str):
        try:
            return float(value_str)
        except ValueError:
            pass
    
    # Quoted string
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    
    # Plain string
    return value_str


def _parse_yaml_simple(yaml_content):
    """
    Parse a simple YAML document into a Python dict.
    Supports basic key-value pairs, lists, and nested dicts.
    This is a minimal parser for the subset of YAML needed for batch definitions.
    """
    if not yaml_content or not isinstance(yaml_content, str):
        return {}
    
    lines = yaml_content.split('\n')
    result = {}
    stack = [(0, result)]  # (indent_level, current_dict)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            i += 1
            continue
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        
        # Pop stack to find parent
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        
        parent = stack[-1][1]
        
        # Check if this is a list item
        if stripped.startswith('- '):
            # Find the key that this list belongs to
            # Look back for the key
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                if prev_line and not prev_line.startswith('#') and not prev_line.startswith('- '):
                    break
                j -= 1
            
            if j >= 0:
                prev_stripped = lines[j].strip()
                if ':' in prev_stripped:
                    key = prev_stripped.split(':', 1)[0].strip()
                    # Remove the key from parent if it was set as empty
                    if key in parent and parent[key] is None:
                        parent[key] = []
                    elif key not in parent:
                        parent[key] = []
                    
                    if isinstance(parent[key], list):
                        item_value = stripped[2:].strip()
                        parent[key].append(_parse_yaml_value(item_value))
            i += 1
            continue
        
        # Key-value pair
        if ':' in stripped:
            key, _, value_part = stripped.partition(':')
            key = key.strip()
            value_part = value_part.strip()
            
            if value_part:
                # Scalar value
                parent[key] = _parse_yaml_value(value_part)
            else:
                # Could be a nested dict or list
                # Look ahead to determine
                next_non_empty = None
                for k in range(i + 1, len(lines)):
                    next_stripped = lines[k].strip()
                    if next_stripped and not next_stripped.startswith('#'):
                        next_non_empty = next_stripped
                        break
                
                if next_non_empty and next_non_empty.startswith('- '):
                    parent[key] = []
                    # Don't push to stack, list items will be handled
                else:
                    # Nested dict
                    new_dict = {}
                    parent[key] = new_dict
                    stack.append((indent, new_dict))
        
        i += 1
    
    return result


def _inject_parameters(graph_dict, params, iteration_index):
    """
    Inject batch parameters into a cloned graph dict.
    
    params structure:
    - seed_offset: int
    - seed_base: int (optional, default 0)
    - prompt_list: list of strings (optional)
    - prompt_node_id: str (optional, default "1")
    - seed_node_id: str (optional, default "3")
    - seed_param_name: str (optional, default "seed")
    - prompt_param_name: str (optional, default "text")
    """
    seed_offset = params.get('seed_offset', 0)
    seed_base = params.get('seed_base', 0)
    prompt_list = params.get('prompt_list', [])
    prompt_node_id = str(params.get('prompt_node_id', '1'))
    seed_node_id = str(params.get('seed_node_id', '3'))
    seed_param_name = params.get('seed_param_name', 'seed')
    prompt_param_name = params.get('prompt_param_name', 'text')
    
    # Inject seed
    if seed_node_id in graph_dict:
        node = graph_dict[seed_node_id]
        if 'inputs' in node and isinstance(node['inputs'], dict):
            node['inputs'][seed_param_name] = seed_base + (iteration_index * seed_offset)
    
    # Inject prompt
    if prompt_list and iteration_index < len(prompt_list):
        if prompt_node_id in graph_dict:
            node = graph_dict[prompt_node_id]
            if 'inputs' in node and isinstance(node['inputs'], dict):
                node['inputs'][prompt_param_name] = prompt_list[iteration_index]
    
    return graph_dict


class PSN_YAML_Batch_Definer:
    """
    Parses a YAML batch definition and a base ComfyUI API-format JSON graph,
    then generates a list of parameterized graph JSON strings for batch execution.
    
    The YAML should contain:
    - count: number of batch iterations
    - seed_offset: offset to add to seed for each iteration
    - seed_base: base seed value (optional, default 0)
    - prompt_list: list of prompts to cycle through (optional)
    - prompt_node_id: node ID for prompt injection (optional, default "1")
    - seed_node_id: node ID for seed injection (optional, default "3")
    - seed_param_name: parameter name for seed (optional, default "seed")
    - prompt_param_name: parameter name for prompt (optional, default "text")
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_content": ("STRING", {"default": "count: 1\nseed_offset: 1\n", "multiline": True}),
                "base_graph": ("STRING", {"default": "{}", "multiline": True}),
            },
            "optional": {
                "seed_base": ("INT", {"default": 0, "min": 0, "max": 2**32 - 1}),
            }
        }
    
    RETURN_TYPES = ("LIST", "DICT")
    RETURN_NAMES = ("batch_graphs", "metadata")
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, yaml_content, base_graph, seed_base=None):
        """
        Generate batch graphs from YAML config and base graph.
        
        Args:
            yaml_content: YAML string with batch parameters
            base_graph: JSON string of base ComfyUI API-format graph
            seed_base: Optional override for base seed
            
        Returns:
            tuple: (list of JSON strings, metadata dict)
        """
        # Parse YAML
        metadata = _parse_yaml_simple(yaml_content)
        
        # Validate base graph
        try:
            base_graph_dict = json.loads(base_graph)
            if not isinstance(base_graph_dict, dict):
                raise ValueError("Base graph must be a JSON object")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid base_graph JSON: {e}")
        
        # Extract batch parameters
        count = metadata.get('count', 1)
        if not isinstance(count, int) or count < 1:
            count = 1
        
        seed_offset = metadata.get('seed_offset', 1)
        if not isinstance(seed_offset, int):
            seed_offset = 1
        
        if seed_base is not None:
            metadata['seed_base'] = seed_base
        else:
            metadata.setdefault('seed_base', 0)
        
        prompt_list = metadata.get('prompt_list', [])
        if not isinstance(prompt_list, list):
            prompt_list = []
        
        # Generate batch graphs
        batch_graphs = []
        for i in range(count):
            # Deep clone the base graph
            graph_clone = json.loads(json.dumps(base_graph_dict))
            
            # Inject parameters
            graph_clone = _inject_parameters(graph_clone, metadata, i)
            
            # Serialize to JSON string
            batch_graphs.append(json.dumps(graph_clone, separators=(',', ':')))
        
        return (batch_graphs, metadata)


# Module-level mappings
NODE_CLASS_MAPPINGS = {
    "PSN_YAML_Batch_Definer": PSN_YAML_Batch_Definer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_YAML_Batch_Definer": "PSN YAML Batch Definer"
}
