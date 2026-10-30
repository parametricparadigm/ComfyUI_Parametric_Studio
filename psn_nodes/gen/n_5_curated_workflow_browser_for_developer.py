"""
PSN_Workflow_Browser: A pure-logic, secure-by-design workflow browser for developers.

This module implements the indexing, filtering, and selection logic for a curated
workflow browser. It does NOT perform file system access, network I/O, or ComfyUI
graph manipulation. Instead, it operates on in-memory JSON text representations
of workflow definitions, allowing developers to search, filter, and select
workflows based on category and search terms.

The node accepts a JSON string representing a list of workflow metadata objects
and returns a filtered JSON list and the selected workflow's JSON representation.
"""

import json
import re

# Allowed categories for filtering
CATEGORIES = ["All", "Image", "Video", "Audio"]

# Maximum allowed length for search terms to prevent abuse
MAX_SEARCH_TERM_LENGTH = 100

# Maximum allowed length for workflow descriptions in the index
MAX_DESCRIPTION_LENGTH = 500


def _sanitize_search_term(term):
    """
    Sanitize the search term by stripping whitespace and limiting length.
    Returns None if the term is invalid.
    """
    if not isinstance(term, str):
        return None
    term = term.strip()
    if len(term) > MAX_SEARCH_TERM_LENGTH:
        return None
    return term


def _sanitize_category(category):
    """
    Validate the category against the allowed list.
    Returns 'All' if invalid.
    """
    if category not in CATEGORIES:
        return "All"
    return category


def _parse_workflow_index(json_text):
    """
    Parse the JSON text representing the workflow index.
    Returns a list of workflow dicts, or an empty list if parsing fails.
    Each workflow dict must have 'id', 'name', 'description', and 'category'.
    """
    if not isinstance(json_text, str):
        return []
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    
    if not isinstance(data, list):
        return []
    
    valid_workflows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Ensure required fields exist and are strings
        wf_id = item.get("id")
        name = item.get("name")
        description = item.get("description", "")
        category = item.get("category", "All")
        
        if not isinstance(wf_id, str) or not isinstance(name, str):
            continue
        if not isinstance(description, str):
            description = str(description)
        if not isinstance(category, str):
            category = "All"
        
        # Truncate description to prevent excessive memory usage
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH]
        
        valid_workflows.append({
            "id": wf_id,
            "name": name,
            "description": description,
            "category": category
        })
    
    return valid_workflows


def _filter_workflows(workflows, category, search_term):
    """
    Filter workflows by category and search term.
    Search term is matched against name and description (case-insensitive).
    """
    filtered = []
    search_lower = search_term.lower() if search_term else ""
    
    for wf in workflows:
        # Category filter
        if category != "All" and wf["category"] != category:
            continue
        
        # Search term filter
        if search_lower:
            name_lower = wf["name"].lower()
            desc_lower = wf["description"].lower()
            if search_lower not in name_lower and search_lower not in desc_lower:
                continue
        
        filtered.append(wf)
    
    return filtered


def _select_workflow(workflows, selection_index):
    """
    Select a workflow by index. Returns the workflow dict or None.
    """
    if not isinstance(selection_index, int):
        return None
    if selection_index < 0 or selection_index >= len(workflows):
        return None
    return workflows[selection_index]


class PSN_Workflow_Browser:
    """
    Browser node for curated workflows. Filters and selects workflows
    from an in-memory JSON index.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workflow_index_json": ("STRING", {
                    "default": "[]",
                    "multiline": True,
                    "tooltip": "JSON array of workflow objects with id, name, description, category"
                }),
                "category": (CATEGORIES, {
                    "default": "All",
                    "tooltip": "Filter by media type"
                }),
                "search_term": ("STRING", {
                    "default": "",
                    "tooltip": "Keyword to search in workflow names/descriptions"
                }),
                "selection_index": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 10000,
                    "step": 1,
                    "tooltip": "Index of selected workflow (-1 for none)"
                })
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("workflow_list", "selected_workflow")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Workflow"
    
    def run(self, workflow_index_json, category, search_term, selection_index):
        # Sanitize inputs
        category = _sanitize_category(category)
        search_term = _sanitize_search_term(search_term)
        if search_term is None:
            search_term = ""
        
        # Parse and filter
        workflows = _parse_workflow_index(workflow_index_json)
        filtered = _filter_workflows(workflows, category, search_term)
        
        # Serialize filtered list
        workflow_list_json = json.dumps(filtered, indent=2)
        
        # Select workflow
        selected = _select_workflow(filtered, selection_index)
        selected_json = json.dumps(selected, indent=2) if selected else "null"
        
        return (workflow_list_json, selected_json)


NODE_CLASS_MAPPINGS = {
    "PSN_Workflow_Browser": PSN_Workflow_Browser
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Workflow_Browser": "Workflow Browser"
}
