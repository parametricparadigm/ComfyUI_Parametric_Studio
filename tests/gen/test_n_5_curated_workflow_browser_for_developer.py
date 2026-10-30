import json
import pytest
from psn_nodes.gen.n_5_curated_workflow_browser_for_developer import (
    PSN_Workflow_Browser,
    _sanitize_search_term,
    _sanitize_category,
    _parse_workflow_index,
    _filter_workflows,
    _select_workflow
)


def _make_index(workflows):
    """Helper to create JSON index string from list of workflow dicts."""
    return json.dumps(workflows)


def test_basic_filtering_by_category():
    """Test that category filtering works correctly."""
    workflows = [
        {"id": "wf1", "name": "Image Gen", "description": "Generate images", "category": "Image"},
        {"id": "wf2", "name": "Video Gen", "description": "Generate videos", "category": "Video"},
        {"id": "wf3", "name": "Audio Gen", "description": "Generate audio", "category": "Audio"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, selected_json = node.run(index_json, "Image", "", -1)
    
    result = json.loads(list_json)
    assert len(result) == 1
    assert result[0]["id"] == "wf1"
    assert json.loads(selected_json) is None


def test_search_term_matching():
    """Test that search term matches against name and description."""
    workflows = [
        {"id": "wf1", "name": "Portrait Generator", "description": "Create portraits", "category": "Image"},
        {"id": "wf2", "name": "Landscape Generator", "description": "Create landscapes", "category": "Image"},
        {"id": "wf3", "name": "Portrait Editor", "description": "Edit portraits", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, _ = node.run(index_json, "All", "portrait", -1)
    
    result = json.loads(list_json)
    assert len(result) == 2
    assert result[0]["id"] == "wf1"
    assert result[1]["id"] == "wf3"


def test_search_term_case_insensitive():
    """Test that search is case-insensitive."""
    workflows = [
        {"id": "wf1", "name": "Portrait Generator", "description": "Create portraits", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, _ = node.run(index_json, "All", "PORTRAIT", -1)
    
    result = json.loads(list_json)
    assert len(result) == 1


def test_selection_index_valid():
    """Test that valid selection index returns the correct workflow."""
    workflows = [
        {"id": "wf1", "name": "First", "description": "First workflow", "category": "Image"},
        {"id": "wf2", "name": "Second", "description": "Second workflow", "category": "Video"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    _, selected_json = node.run(index_json, "All", "", 1)
    
    selected = json.loads(selected_json)
    assert selected["id"] == "wf2"
    assert selected["name"] == "Second"


def test_selection_index_out_of_bounds():
    """Test that out-of-bounds selection index returns null."""
    workflows = [
        {"id": "wf1", "name": "First", "description": "First workflow", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    _, selected_json = node.run(index_json, "All", "", 5)
    
    assert json.loads(selected_json) is None


def test_invalid_json_input():
    """Test that invalid JSON input returns empty list."""
    node = PSN_Workflow_Browser()
    list_json, selected_json = node.run("not valid json", "All", "", -1)
    
    result = json.loads(list_json)
    assert result == []
    assert json.loads(selected_json) is None


def test_empty_index():
    """Test that empty index returns empty list."""
    node = PSN_Workflow_Browser()
    list_json, selected_json = node.run("[]", "All", "", -1)
    
    result = json.loads(list_json)
    assert result == []
    assert json.loads(selected_json) is None


def test_invalid_category_defaults_to_all():
    """Test that invalid category defaults to 'All'."""
    workflows = [
        {"id": "wf1", "name": "Test", "description": "Test workflow", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, _ = node.run(index_json, "InvalidCategory", "", -1)
    
    result = json.loads(list_json)
    assert len(result) == 1


def test_search_term_too_long():
    """Test that overly long search term is rejected."""
    workflows = [
        {"id": "wf1", "name": "Test", "description": "Test workflow", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    long_term = "a" * 200
    list_json, _ = node.run(index_json, "All", long_term, -1)
    
    # Long term should be sanitized to empty, so all workflows returned
    result = json.loads(list_json)
    assert len(result) == 1


def test_workflows_with_missing_fields():
    """Test that workflows with missing required fields are filtered out."""
    workflows = [
        {"id": "wf1", "name": "Valid", "description": "Valid workflow", "category": "Image"},
        {"id": "wf2", "description": "Missing name", "category": "Image"},
        {"name": "Missing id", "description": "Missing id workflow", "category": "Image"},
        {"id": "wf3", "name": "Valid2", "description": "Another valid", "category": "Video"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, _ = node.run(index_json, "All", "", -1)
    
    result = json.loads(list_json)
    assert len(result) == 2
    assert result[0]["id"] == "wf1"
    assert result[1]["id"] == "wf3"


def test_combined_category_and_search():
    """Test combined category and search filtering."""
    workflows = [
        {"id": "wf1", "name": "Image Portrait", "description": "Portrait image", "category": "Image"},
        {"id": "wf2", "name": "Video Portrait", "description": "Portrait video", "category": "Video"},
        {"id": "wf3", "name": "Image Landscape", "description": "Landscape image", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    list_json, _ = node.run(index_json, "Image", "portrait", -1)
    
    result = json.loads(list_json)
    assert len(result) == 1
    assert result[0]["id"] == "wf1"


def test_non_string_search_term():
    """Test that non-string search term is handled gracefully."""
    workflows = [
        {"id": "wf1", "name": "Test", "description": "Test workflow", "category": "Image"},
    ]
    index_json = _make_index(workflows)
    
    node = PSN_Workflow_Browser()
    # Pass a non-string (should be handled by sanitization)
    list_json, _ = node.run(index_json, "All", 123, -1)
    
    result = json.loads(list_json)
    assert len(result) == 1
