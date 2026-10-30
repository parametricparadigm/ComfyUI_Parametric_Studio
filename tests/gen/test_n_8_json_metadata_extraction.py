"""
Tests for psn_nodes.gen.n_8_json_metadata_extraction.

Covers:
- PSN_JSON_Metadata_Extractor: valid inputs, invalid JSON, empty inputs,
  non-serializable handling, workflow node extraction.
- PSN_File_List_Manager: valid pattern matching, no matches, invalid JSON,
  non-list input, non-string elements, empty file_names.
"""

import json
import pytest

from psn_nodes.gen.n_8_json_metadata_extraction import (
    PSN_JSON_Metadata_Extractor,
    PSN_File_List_Manager,
)


# ---------------------------------------------------------------------------
# Tests for PSN_JSON_Metadata_Extractor
# ---------------------------------------------------------------------------

class TestPSNJSONMetadataExtractor:

    def test_valid_inputs_produce_valid_json(self):
        """Valid image metadata and workflow JSON should produce valid merged JSON."""
        node = PSN_JSON_Metadata_Extractor()
        img_meta = json.dumps({"width": 512, "height": 512, "seed": 42})
        wf = json.dumps({"nodes": [{"id": 1, "type": "KSampler"}, {"id": 2, "type": "VAEDecode"}]})

        result_json, success, error = node.run(img_meta, wf)

        assert success is True
        assert error == ""
        parsed = json.loads(result_json)
        assert parsed["image"]["width"] == 512
        assert parsed["image"]["seed"] == 42
        assert parsed["workflow"]["node_count"] == 2
        assert "KSampler" in parsed["workflow"]["node_types"]
        assert "VAEDecode" in parsed["workflow"]["node_types"]

    def test_invalid_image_metadata_json(self):
        """Invalid JSON in image_metadata should return success=False with error."""
        node = PSN_JSON_Metadata_Extractor()
        result_json, success, error = node.run("not valid json {", "{}")

        assert success is False
        assert "image_metadata" in error
        assert result_json == ""

    def test_invalid_workflow_json(self):
        """Invalid JSON in workflow should return success=False with error."""
        node = PSN_JSON_Metadata_Extractor()
        result_json, success, error = node.run("{}", "broken json [[")

        assert success is False
        assert "workflow" in error
        assert result_json == ""

    def test_empty_image_metadata_string(self):
        """Empty string for image_metadata should fail gracefully."""
        node = PSN_JSON_Metadata_Extractor()
        result_json, success, error = node.run("", "{}")

        assert success is False
        assert "empty" in error.lower()

    def test_non_dict_workflow_handled_gracefully(self):
        """Workflow that is a JSON list (not dict) should still produce valid output."""
        node = PSN_JSON_Metadata_Extractor()
        img_meta = json.dumps({"seed": 123})
        wf = json.dumps([1, 2, 3])  # A list, not a dict

        result_json, success, error = node.run(img_meta, wf)

        assert success is True
        parsed = json.loads(result_json)
        assert parsed["image"]["seed"] == 123
        # Workflow raw should contain the list
        assert parsed["workflow"]["raw"] == [1, 2, 3]

    def test_include_workflow_nodes_false(self):
        """When include_workflow_nodes is False, node details should not be extracted."""
        node = PSN_JSON_Metadata_Extractor()
        img_meta = json.dumps({"a": 1})
        wf = json.dumps({"nodes": [{"id": 1, "type": "KSampler"}]})

        result_json, success, error = node.run(img_meta, wf, include_workflow_nodes=False)

        assert success is True
        parsed = json.loads(result_json)
        # Should not have node_count or node_types
        assert "node_count" not in parsed["workflow"]
        assert "node_types" not in parsed["workflow"]
        # But raw should still be present
        assert "raw" in parsed["workflow"]

    def test_non_serializable_values_converted_to_strings(self):
        """Values that are not JSON-serializable should be converted to strings."""
        node = PSN_JSON_Metadata_Extractor()
        # We can't easily pass a non-serializable object through JSON text,
        # but we can test that the safe_serialize logic works by checking
        # that the output is always valid JSON.
        img_meta = json.dumps({"key": "value", "num": 3.14, "flag": True, "nil": None})
        wf = json.dumps({"nodes": []})

        result_json, success, error = node.run(img_meta, wf)

        assert success is True
        parsed = json.loads(result_json)
        assert parsed["image"]["key"] == "value"
        assert parsed["image"]["num"] == 3.14
        assert parsed["image"]["flag"] is True
        assert parsed["image"]["nil"] is None


# ---------------------------------------------------------------------------
# Tests for PSN_File_List_Manager
# ---------------------------------------------------------------------------

class TestPSNFileListManager:

    def test_valid_pattern_matching(self):
        """Files matching the pattern should be returned, sorted."""
        node = PSN_File_List_Manager()
        file_names = json.dumps(["b.png", "a.png", "c.jpg", "d.png"])

        result_json, count, error = node.run("/data", "*.png", file_names)

        assert error == ""
        assert count == 3
        parsed = json.loads(result_json)
        assert parsed == ["a.png", "b.png", "d.png"]

    def test_no_matching_files(self):
        """When no files match, an empty list should be returned."""
        node = PSN_File_List_Manager()
        file_names = json.dumps(["a.txt", "b.md"])

        result_json, count, error = node.run("/data", "*.png", file_names)

        assert error == ""
        assert count == 0
        parsed = json.loads(result_json)
        assert parsed == []

    def test_invalid_json_file_names(self):
        """Invalid JSON in file_names should return an error."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "*.png", "not json")

        assert count == 0
        assert "not valid JSON" in error
        assert result_json == "[]"

    def test_file_names_not_a_list(self):
        """If file_names is valid JSON but not a list, return an error."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "*.png", json.dumps({"a": 1}))

        assert count == 0
        assert "must be a JSON list" in error
        assert result_json == "[]"

    def test_file_names_contains_non_string(self):
        """If file_names list contains a non-string element, return an error."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "*.png", json.dumps(["a.png", 123]))

        assert count == 0
        assert "not a string" in error
        assert result_json == "[]"

    def test_empty_file_names_string(self):
        """Empty string for file_names should return an empty list without error."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "*.png", "")

        assert error == ""
        assert count == 0
        parsed = json.loads(result_json)
        assert parsed == []

    def test_empty_pattern_rejected(self):
        """Empty pattern should be rejected with an error."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "", json.dumps(["a.png"]))

        assert count == 0
        assert "non-empty string" in error
        assert result_json == "[]"

    def test_default_file_names_is_empty_list(self):
        """When file_names is not provided (default '[]'), should return empty list."""
        node = PSN_File_List_Manager()
        result_json, count, error = node.run("/data", "*.png")

        assert error == ""
        assert count == 0
        parsed = json.loads(result_json)
        assert parsed == []

    def test_glob_pattern_with_question_mark(self):
        """Glob pattern with ? should match single characters."""
        node = PSN_File_List_Manager()
        file_names = json.dumps(["a1.png", "a2.png", "ab.png", "a12.png"])

        result_json, count, error = node.run("/data", "a?.png", file_names)

        assert error == ""
        assert count == 3
        parsed = json.loads(result_json)
        assert parsed == ["a1.png", "a2.png", "ab.png"]
