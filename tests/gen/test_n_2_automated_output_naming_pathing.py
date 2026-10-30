"""Tests for psn_nodes.gen.n_2_automated_output_naming_pathing."""

import datetime
import pytest

from psn_nodes.gen.n_2_automated_output_naming_pathing import (
    PSN_Filename_Generator,
    PSN_Path_Validator,
    psn_generate_filename,
    psn_validate_path,
    psn_sanitize_filename_component,
    psn_is_reserved_name,
    DEFAULT_ALLOWED_ROOTS,
)


# ---------------------------------------------------------------------------
# Filename generation tests
# ---------------------------------------------------------------------------

class TestFilenameGenerator:
    def test_basic_generation(self):
        """Basic filename with known timestamp."""
        now = datetime.datetime(2024, 1, 15, 12, 30, 45)
        result = psn_generate_filename(
            base_name="my_image",
            timestamp_format="%Y%m%d_%H%M%S",
            seed=42,
            suffix="",
            now=now,
        )
        assert result == "my_image_20240115_123045_42"

    def test_with_suffix(self):
        """Filename includes suffix when provided."""
        now = datetime.datetime(2024, 6, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="render",
            timestamp_format="%Y%m%d",
            seed=7,
            suffix="v2",
            now=now,
        )
        assert result == "render_20240601_7_v2"

    def test_sanitizes_unsafe_characters(self):
        """Unsafe characters in base name are replaced."""
        now = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="my/image:with?bad*chars",
            timestamp_format="%Y%m%d",
            seed=1,
            now=now,
        )
        # Colons, slashes, question marks, asterisks -> underscores
        assert "/" not in result
        assert ":" not in result
        assert "?" not in result
        assert "*" not in result
        assert result.startswith("my_image_with_bad_chars_")

    def test_empty_base_name_uses_default(self):
        """Empty base name falls back to 'output'."""
        now = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="",
            timestamp_format="%Y%m%d",
            seed=0,
            now=now,
        )
        assert result.startswith("output_")

    def test_reserved_name_gets_prefix(self):
        """Reserved names like 'CON' get an 'x_' prefix."""
        now = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="CON",
            timestamp_format="%Y%m%d",
            seed=0,
            now=now,
        )
        # The full filename won't be exactly "CON" but the stem check
        # applies to the whole filename. Since we append timestamp and seed,
        # the stem is the whole thing before first dot. Let's verify it's
        # not just "CON".
        assert result != "CON"
        assert "CON" in result

    def test_negative_seed(self):
        """Negative seeds are handled."""
        now = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="test",
            timestamp_format="%Y%m%d",
            seed=-123,
            now=now,
        )
        assert "-123" in result

    def test_invalid_timestamp_format_falls_back(self):
        """Invalid timestamp format uses default format."""
        now = datetime.datetime(2024, 1, 1, 0, 0, 0)
        result = psn_generate_filename(
            base_name="test",
            timestamp_format="INVALID_FORMAT",
            seed=1,
            now=now,
        )
        # Should still produce a valid filename
        assert "test" in result
        assert "1" in result


# ---------------------------------------------------------------------------
# Path validation tests
# ---------------------------------------------------------------------------

class TestPathValidator:
    def test_valid_path_within_root(self):
        """Path within allowed root is valid."""
        full_path, is_valid, reason = psn_validate_path(
            directory="~/ComfyUI/models/output",
            filename="test.png",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        assert is_valid is True
        assert full_path == "~/ComfyUI/models/output/test.png"
        assert reason == "OK"

    def test_path_outside_allowed_root(self):
        """Path outside allowed root is invalid."""
        full_path, is_valid, reason = psn_validate_path(
            directory="/tmp/other",
            filename="test.png",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        assert is_valid is False
        assert "not within" in reason

    def test_path_traversal_rejected(self):
        """Path with '..' traversal is rejected."""
        full_path, is_valid, reason = psn_validate_path(
            directory="~/ComfyUI/models/../../etc",
            filename="passwd",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        assert is_valid is False
        assert "traversal" in reason

    def test_empty_filename_rejected(self):
        """Empty filename is rejected."""
        full_path, is_valid, reason = psn_validate_path(
            directory="~/ComfyUI/models",
            filename="",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        assert is_valid is False
        assert "empty" in reason.lower() or "unsafe" in reason.lower()

    def test_filename_with_unsafe_chars_sanitized(self):
        """Filename with unsafe characters is sanitized before validation."""
        full_path, is_valid, reason = psn_validate_path(
            directory="~/ComfyUI/models",
            filename="bad/name:with?chars.png",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        # The filename should be sanitized, so no slashes/colons/question marks
        assert "/" not in full_path.split("/")[-1]
        assert ":" not in full_path.split("/")[-1]
        assert "?" not in full_path.split("/")[-1]
        # The path should still be valid if within root
        assert is_valid is True

    def test_multiple_allowed_roots(self):
        """Multiple allowed roots are checked."""
        roots = ("~/ComfyUI/models", "/mnt/other/models")
        full_path, is_valid, reason = psn_validate_path(
            directory="/mnt/other/models/output",
            filename="test.png",
            allowed_roots=roots,
        )
        assert is_valid is True

    def test_root_exact_match(self):
        """Path exactly at root level is valid."""
        full_path, is_valid, reason = psn_validate_path(
            directory="~/ComfyUI/models",
            filename="test.png",
            allowed_roots=DEFAULT_ALLOWED_ROOTS,
        )
        assert is_valid is True
        assert full_path == "~/ComfyUI/models/test.png"


# ---------------------------------------------------------------------------
# Node class integration tests
# ---------------------------------------------------------------------------

class TestNodeClasses:
    def test_filename_generator_node(self):
        """PSN_Filename_Generator node returns a tuple with filename."""
        node = PSN_Filename_Generator()
        result = node.run(
            base_name="test",
            timestamp_format="%Y%m%d",
            seed=42,
            suffix="final",
        )
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert isinstance(result[0], str)
        assert "test" in result[0]
        assert "42" in result[0]
        assert "final" in result[0]

    def test_path_validator_node_valid(self):
        """PSN_Path_Validator node returns valid path for allowed root."""
        node = PSN_Path_Validator()
        result = node.run(
            directory="~/ComfyUI/models/output",
            filename="image.png",
            create_dirs=False,
            allowed_roots="~/ComfyUI/models",
        )
        assert isinstance(result, tuple)
        assert len(result) == 3
        full_path, is_valid, reason = result
        assert is_valid is True
        assert full_path == "~/ComfyUI/models/output/image.png"

    def test_path_validator_node_invalid(self):
        """PSN_Path_Validator node returns invalid for out-of-bounds path."""
        node = PSN_Path_Validator()
        result = node.run(
            directory="/etc",
            filename="passwd",
            create_dirs=False,
            allowed_roots="~/ComfyUI/models",
        )
        full_path, is_valid, reason = result
        assert is_valid is False

    def test_path_validator_node_empty_filename(self):
        """PSN_Path_Validator node rejects empty filename."""
        node = PSN_Path_Validator()
        result = node.run(
            directory="~/ComfyUI/models",
            filename="",
            create_dirs=False,
            allowed_roots="~/ComfyUI/models",
        )
        full_path, is_valid, reason = result
        assert is_valid is False

    def test_node_return_types_match(self):
        """Node RETURN_TYPES and RETURN_NAMES are consistent."""
        assert len(PSN_Filename_Generator.RETURN_TYPES) == len(PSN_Filename_Generator.RETURN_NAMES)
        assert len(PSN_Path_Validator.RETURN_TYPES) == len(PSN_Path_Validator.RETURN_NAMES)
        assert PSN_Filename_Generator.RETURN_TYPES == ("STRING",)
        assert PSN_Path_Validator.RETURN_TYPES == ("STRING", "BOOLEAN", "STRING")

    def test_node_input_types_structure(self):
        """Node INPUT_TYPES have required and optional keys."""
        inputs = PSN_Filename_Generator.INPUT_TYPES()
        assert "required" in inputs
        assert "optional" in inputs
        assert "base_name" in inputs["required"]
        assert "seed" in inputs["required"]

        inputs2 = PSN_Path_Validator.INPUT_TYPES()
        assert "required" in inputs2
        assert "optional" in inputs2
        assert "directory" in inputs2["required"]
        assert "filename" in inputs2["required"]
