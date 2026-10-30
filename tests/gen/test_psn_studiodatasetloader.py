"""Tests for PSN_StudioDatasetLoader node."""

import json
import base64
import pytest

from psn_nodes.gen.psn_studiodatasetloader import (
    PSN_StudioDatasetLoader,
    validate_storyboard,
    PSN_STORYBOARD_DATA,
)


def _make_valid_storyboard(version=1):
    """Create a valid storyboard dict for testing."""
    return {
        "schema_version": version,
        "shots": [
            {"shot_id": "shot_001", "duration": 2.5, "prompt_seed": 42},
            {"shot_id": "shot_002", "duration": 3.0, "prompt_seed": 123},
        ],
        "characters": [
            {"character_id": "char_001", "name": "Alice"},
            {"character_id": "char_002", "name": "Bob"},
        ],
        "assets": [
            {"asset_id": "asset_001", "name": "Background"},
        ],
        "settings": {"fps": 24, "resolution": "1920x1080"},
    }


def _to_json(data):
    return json.dumps(data)


def _to_base64(data):
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")


class TestPSN_StudioDatasetLoader:
    """Test suite for PSN_StudioDatasetLoader."""

    def test_valid_storyboard_no_errors(self):
        """Load a valid storyboard; assert no errors and correct data structure."""
        valid_data = _make_valid_storyboard(version=1)
        raw = _to_json(valid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert errors == ""
        assert storyboard_data is not None
        assert storyboard_data["schema_version"] == 1
        assert len(storyboard_data["shots"]) == 2
        assert len(storyboard_data["characters"]) == 2
        assert len(storyboard_data["assets"]) == 1
        assert storyboard_data["settings"]["fps"] == 24

    def test_missing_shot_id_reports_specific_error(self):
        """Load invalid fixture missing shot_id; assert specific error message."""
        invalid_data = _make_valid_storyboard(version=1)
        # Remove shot_id from first shot
        del invalid_data["shots"][0]["shot_id"]
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[0] missing required field: 'shot_id'" in errors

    def test_missing_duration_reports_error(self):
        """Load invalid fixture missing duration; assert error."""
        invalid_data = _make_valid_storyboard(version=1)
        del invalid_data["shots"][1]["duration"]
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[1] missing required field: 'duration'" in errors

    def test_missing_prompt_seed_reports_error(self):
        """Load invalid fixture missing prompt_seed; assert error."""
        invalid_data = _make_valid_storyboard(version=1)
        del invalid_data["shots"][0]["prompt_seed"]
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[0] missing required field: 'prompt_seed'" in errors

    def test_base64_encoded_valid_storyboard(self):
        """Load a base64-encoded valid storyboard; assert no errors."""
        valid_data = _make_valid_storyboard(version=1)
        raw = _to_base64(valid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert errors == ""
        assert storyboard_data is not None
        assert len(storyboard_data["shots"]) == 2

    def test_invalid_json_reports_parse_error(self):
        """Load invalid JSON; assert parse error is reported."""
        raw = "{not valid json"

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "neither valid JSON nor valid base64-encoded JSON" in errors

    def test_empty_string_reports_error(self):
        """Load empty string; assert error."""
        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run("", schema_version=1)

        assert storyboard_data is None
        assert "Input string is empty" in errors

    def test_schema_version_mismatch_reports_error(self):
        """Load valid storyboard with version 1 but target version 2; assert mismatch error."""
        valid_data = _make_valid_storyboard(version=1)
        raw = _to_json(valid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=2)

        assert storyboard_data is None
        assert "Schema version mismatch" in errors

    def test_unsupported_schema_version_reports_error(self):
        """Load storyboard with unsupported version; assert error."""
        invalid_data = _make_valid_storyboard(version=99)
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=99)

        assert storyboard_data is None
        assert "Unsupported schema_version 99" in errors

    def test_negative_duration_reports_error(self):
        """Load storyboard with negative duration; assert error."""
        invalid_data = _make_valid_storyboard(version=1)
        invalid_data["shots"][0]["duration"] = -1.0
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[0].duration must be non-negative" in errors

    def test_non_integer_prompt_seed_reports_error(self):
        """Load storyboard with non-integer prompt_seed; assert error."""
        invalid_data = _make_valid_storyboard(version=1)
        invalid_data["shots"][0]["prompt_seed"] = 42.5
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[0].prompt_seed must be an integer" in errors

    def test_missing_top_level_shots_reports_error(self):
        """Load storyboard missing 'shots' key; assert error."""
        invalid_data = _make_valid_storyboard(version=1)
        del invalid_data["shots"]
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "Missing required top-level field: 'shots'" in errors

    def test_multiple_errors_all_reported(self):
        """Load storyboard with multiple errors; assert all are reported."""
        invalid_data = _make_valid_storyboard(version=1)
        del invalid_data["shots"][0]["shot_id"]
        del invalid_data["characters"][0]["name"]
        invalid_data["assets"][0]["asset_id"] = ""
        raw = _to_json(invalid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert storyboard_data is None
        assert "shots[0] missing required field: 'shot_id'" in errors
        assert "characters[0] missing required field: 'name'" in errors
        assert "assets[0].asset_id must be a non-empty string" in errors

    def test_duration_normalized_to_float(self):
        """Load storyboard with integer duration; assert it's normalized to float."""
        valid_data = _make_valid_storyboard(version=1)
        valid_data["shots"][0]["duration"] = 2  # integer
        raw = _to_json(valid_data)

        node = PSN_StudioDatasetLoader()
        storyboard_data, errors = node.run(raw, schema_version=1)

        assert errors == ""
        assert storyboard_data is not None
        assert isinstance(storyboard_data["shots"][0]["duration"], float)
        assert storyboard_data["shots"][0]["duration"] == 2.0

    def test_validate_storyboard_function_directly(self):
        """Test the validate_storyboard function directly with valid input."""
        valid_data = _make_valid_storyboard(version=1)
        raw = _to_json(valid_data)

        data, errors = validate_storyboard(raw, 1)

        assert errors == []
        assert data is not None
        assert data["schema_version"] == 1
        assert len(data["shots"]) == 2

    def test_validate_storyboard_function_with_invalid_input(self):
        """Test the validate_storyboard function directly with invalid input."""
        invalid_data = _make_valid_storyboard(version=1)
        del invalid_data["shots"][0]["shot_id"]
        raw = _to_json(invalid_data)

        data, errors = validate_storyboard(raw, 1)

        assert data is None
        assert len(errors) == 1
        assert "shot_id" in errors[0]
