"""
PSN Graph Cleaning & Debugging nodes.

This module provides pure-logic utility nodes for cleaning graph structures
and processing lists. It does NOT perform any file I/O, network access,
GPU operations, or ComfyUI internal interactions. All functions operate on
plain Python data structures (dicts, lists, strings, numbers) and are
safe-by-design for use in a sandboxed environment.

Nodes:
- PSN_Graph_Cleaner: Removes orphaned nodes from a graph dictionary.
- PSN_List_Processor: Performs operations (SORT, REVERSE, UNIQUE, SLICE) on lists.
"""

from typing import Any, Dict, List, Tuple

# Module-level constants
CAT = "ParametricStudio/GraphCleaning"

# Allowed operations for PSN_List_Processor
LIST_OPERATIONS = ["SORT", "REVERSE", "UNIQUE", "SLICE"]


def _is_node_orphaned(node_id: str, graph: Dict[str, Any]) -> bool:
    """
    Determine if a node is orphaned (not connected to any other node).
    
    A node is considered orphaned if:
    - It has no inputs that reference other nodes
    - It has no outputs that are referenced by other nodes
    
    Args:
        node_id: The ID of the node to check
        graph: The graph dictionary with 'nodes' key
        
    Returns:
        True if the node is orphaned, False otherwise
    """
    nodes = graph.get("nodes", {})
    if node_id not in nodes:
        return True
    
    node = nodes[node_id]
    
    # Check if this node's outputs are referenced by any other node
    is_referenced = False
    for other_id, other_node in nodes.items():
        if other_id == node_id:
            continue
        # Check inputs of other nodes for references to this node
        other_inputs = other_node.get("inputs", [])
        for inp in other_inputs:
            if isinstance(inp, dict):
                ref_node = inp.get("node", None)
                if ref_node == node_id:
                    is_referenced = True
                    break
        if is_referenced:
            break
    
    if is_referenced:
        return False
    
    # Check if this node has any inputs that reference other nodes
    has_input_connections = False
    node_inputs = node.get("inputs", [])
    for inp in node_inputs:
        if isinstance(inp, dict):
            ref_node = inp.get("node", None)
            if ref_node is not None and ref_node != node_id:
                has_input_connections = True
                break
    
    # A node is orphaned if it has no input connections AND is not referenced
    return not has_input_connections


def clean_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove orphaned nodes from a graph dictionary.
    
    Args:
        graph: The graph dictionary with 'nodes' key
        
    Returns:
        A new graph dictionary with orphaned nodes removed
    """
    if not isinstance(graph, dict):
        raise ValueError("Graph must be a dictionary")
    
    nodes = graph.get("nodes", {})
    if not isinstance(nodes, dict):
        raise ValueError("Graph 'nodes' must be a dictionary")
    
    # Identify orphaned nodes
    orphaned_ids = set()
    for node_id in nodes:
        if _is_node_orphaned(node_id, graph):
            orphaned_ids.add(node_id)
    
    # Build cleaned graph
    cleaned_nodes = {
        node_id: node for node_id, node in nodes.items()
        if node_id not in orphaned_ids
    }
    
    cleaned_graph = dict(graph)
    cleaned_graph["nodes"] = cleaned_nodes
    
    return cleaned_graph


def process_list(input_list: List[Any], operation: str, start: int = 0, end: int = None) -> List[Any]:
    """
    Perform the specified operation on a list.
    
    Args:
        input_list: The input list
        operation: One of SORT, REVERSE, UNIQUE, SLICE
        start: Start index for SLICE operation
        end: End index for SLICE operation (None means to end)
        
    Returns:
        The processed list
    """
    if not isinstance(input_list, list):
        raise ValueError("Input must be a list")
    
    if operation not in LIST_OPERATIONS:
        raise ValueError(f"Operation must be one of {LIST_OPERATIONS}")
    
    if operation == "SORT":
        # Sort in a way that handles mixed types safely
        try:
            return sorted(input_list)
        except TypeError:
            # Fallback: sort by string representation for mixed types
            return sorted(input_list, key=lambda x: str(x))
    
    elif operation == "REVERSE":
        return list(reversed(input_list))
    
    elif operation == "UNIQUE":
        # Preserve order while removing duplicates
        seen = set()
        unique_list = []
        for item in input_list:
            # Use a hashable representation for comparison
            try:
                key = item
            except TypeError:
                key = str(item)
            if key not in seen:
                seen.add(key)
                unique_list.append(item)
        return unique_list
    
    elif operation == "SLICE":
        if end is None:
            return input_list[start:]
        else:
            return input_list[start:end]
    
    raise ValueError(f"Unknown operation: {operation}")


class PSN_Graph_Cleaner:
    """
    Removes orphaned nodes from a graph structure.
    
    Orphaned nodes are those that have no input connections and are not
    referenced by any other node's inputs. This is useful for cleaning up
    workflow graphs before submission.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "graph": ("DICT", {"default": {}}),
            }
        }
    
    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("cleaned_graph",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, graph: Dict[str, Any]) -> Tuple[Dict[str, Any]]:
        """
        Clean the graph by removing orphaned nodes.
        
        Args:
            graph: The input graph dictionary
            
        Returns:
            Tuple containing the cleaned graph
        """
        cleaned = clean_graph(graph)
        return (cleaned,)


class PSN_List_Processor:
    """
    Performs operations on lists: SORT, REVERSE, UNIQUE, or SLICE.
    
    This node provides common list manipulation utilities for workflow
    processing.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list": ("LIST", {"default": []}),
                "operation": (LIST_OPERATIONS,),
            },
            "optional": {
                "start": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "end": ("INT", {"default": -1, "min": -1, "max": 10000}),
            }
        }
    
    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("processed_list",)
    FUNCTION = "run"
    CATEGORY = CAT
    
    def run(self, list: List[Any], operation: str, start: int = 0, end: int = -1) -> Tuple[List[Any]]:
        """
        Process the input list with the specified operation.
        
        Args:
            list: The input list
            operation: The operation to perform (SORT, REVERSE, UNIQUE, SLICE)
            start: Start index for SLICE operation
            end: End index for SLICE operation (-1 means to end)
            
        Returns:
            Tuple containing the processed list
        """
        # Convert end=-1 to None for slice operation
        slice_end = None if end == -1 else end
        processed = process_list(list, operation, start, slice_end)
        return (processed,)


# Module-level mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "PSN_Graph_Cleaner": PSN_Graph_Cleaner,
    "PSN_List_Processor": PSN_List_Processor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Graph_Cleaner": "PSN Graph Cleaner",
    "PSN_List_Processor": "PSN List Processor",
}
