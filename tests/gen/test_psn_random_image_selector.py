"""
Tests for PSN_Random_Image_Selector

These tests verify the pure-logic selection behavior without any file system
access, network, or GPU operations.
"""

import pytest
from psn_nodes.gen.psn_random_image_selector import (
    PSN_Random_Image_Selector,
    select_random_images,
    _validate_folder_path,
    _validate_num_images,
    _validate_seed,
    _validate_file_names,
)


class TestValidation:
    """Test input validation functions."""

    def test_validate_folder_path_valid(self):
        valid, err = _validate_folder_path("/home/user/images")
        assert valid is True
        assert err == ""

    def test_validate_folder_path_empty(self):
        valid, err = _validate_folder_path("")
        assert valid is False
        assert "empty" in err

    def test_validate_folder_path_whitespace_only(self):
        valid, err = _validate_folder_path("   ")
        assert valid is False
        assert "empty" in err

    def test_validate_folder_path_not_string(self):
        valid, err = _validate_folder_path(123)
        assert valid is False
        assert "string" in err

    def test_validate_folder_path_control_chars(self):
        valid, err = _validate_folder_path("/home/user/img\x00es")
        assert valid is False
        assert "control" in err

    def test_validate_num_images_valid(self):
        valid, err = _validate_num_images(5)
        assert valid is True
        assert err == ""

    def test_validate_num_images_zero(self):
        valid, err = _validate_num_images(0)
        assert valid is False
        assert "at least 1" in err

    def test_validate_num_images_negative(self):
        valid, err = _validate_num_images(-3)
        assert valid is False
        assert "at least 1" in err

    def test_validate_num_images_not_int(self):
        valid, err = _validate_num_images(3.5)
        assert valid is False
        assert "integer" in err

    def test_validate_num_images_bool_rejected(self):
        valid, err = _validate_num_images(True)
        assert valid is False
        assert "integer" in err

    def test_validate_seed_valid(self):
        valid, err = _validate_seed(42)
        assert valid is True
        assert err == ""

    def test_validate_seed_none(self):
        valid, err = _validate_seed(None)
        assert valid is True
        assert err == ""

    def test_validate_seed_not_int(self):
        valid, err = _validate_seed("42")
        assert valid is False
        assert "integer" in err

    def test_validate_file_names_valid(self):
        valid, err = _validate_file_names(["a.png", "b.jpg"])
        assert valid is True
        assert err == ""

    def test_validate_file_names_none(self):
        valid, err = _validate_file_names(None)
        assert valid is True
        assert err == ""

    def test_validate_file_names_not_list(self):
        valid, err = _validate_file_names("a.png")
        assert valid is False
        assert "list" in err

    def test_validate_file_names_non_string_element(self):
        valid, err = _validate_file_names(["a.png", 123])
        assert valid is False
        assert "string" in err

    def test_validate_file_names_empty_string_element(self):
        valid, err = _validate_file_names(["a.png", "  "])
        assert valid is False
        assert "empty" in err


class TestSelectRandomImages:
    """Test the core selection logic."""

    def test_select_all_when_fewer_available(self):
        file_names = ["a.png", "b.png", "c.png"]
        indices, names, paths, reason = select_random_images(
            "/folder", 10, 42, file_names
        )
        assert len(indices) == 3
        assert len(names) == 3
        assert len(paths) == 3
        assert set(names) == {"a.png", "b.png", "c.png"}
        assert "3 of 3" in reason

    def test_select_subset(self):
        file_names = [f"img_{i}.png" for i in range(10)]
        indices, names, paths, reason = select_random_images(
            "/folder", 3, 42, file_names
        )
        assert len(indices) == 3
        assert len(names) == 3
        assert len(paths) == 3
        # All selected names should be from the original list
        for name in names:
            assert name in file_names
        # All indices should be valid
        for idx in indices:
            assert 0 <= idx < 10
        # Selected names should be unique
        assert len(set(names)) == 3

    def test_reproducibility_with_seed(self):
        file_names = [f"img_{i}.png" for i in range(20)]
        indices1, names1, _, _ = select_random_images("/folder", 5, 123, file_names)
        indices2, names2, _, _ = select_random_images("/folder", 5, 123, file_names)
        assert indices1 == indices2
        assert names1 == names2

    def test_different_seeds_give_different_results(self):
        file_names = [f"img_{i}.png" for i in range(50)]
        _, names1, _, _ = select_random_images("/folder", 5, 1, file_names)
        _, names2, _, _ = select_random_images("/folder", 5, 2, file_names)
        # With 50 files and selecting 5, it's extremely unlikely to get the same set
        assert names1 != names2

    def test_empty_file_names(self):
        indices, names, paths, reason = select_random_images("/folder", 3, 42, [])
        assert indices == []
        assert names == []
        assert paths == []
        assert "No files" in reason

    def test_none_file_names(self):
        indices, names, paths, reason = select_random_images("/folder", 3, 42, None)
        assert indices == []
        assert names == []
        assert paths == []
        assert "No files" in reason

    def test_file_paths_construction(self):
        file_names = ["a.png", "b.jpg"]
        indices, names, paths, reason = select_random_images(
            "/home/user/images", 2, 42, file_names
        )
        for path in paths:
            assert path.startswith("/home/user/images/")
            assert path.endswith(".png") or path.endswith(".jpg")

    def test_folder_path_trailing_slash_normalized(self):
        file_names = ["a.png"]
        indices, names, paths, reason = select_random_images(
            "/home/user/images/", 1, 42, file_names
        )
        assert paths[0] == "/home/user/images/a.png"

    def test_single_file_selection(self):
        file_names = ["only.png"]
        indices, names, paths, reason = select_random_images("/folder", 1, 42, file_names)
        assert indices == [0]
        assert names == ["only.png"]
        assert paths == ["/folder/only.png"]

    def test_seed_in_reason(self):
        file_names = ["a.png", "b.png"]
        _, _, _, reason = select_random_images("/folder", 1, 99, file_names)
        assert "seed=99" in reason


class TestNodeRun:
    """Test the node's run method."""

    def setup_method(self):
        self.node = PSN_Random_Image_Selector()

    def test_run_valid_inputs(self):
        file_names = [f"img_{i}.png" for i in range(10)]
        indices, names, paths, reason = self.node.run(
            folder_path="/test/folder",
            num_images=3,
            seed=42,
            file_names=file_names,
        )
        assert len(indices) == 3
        assert len(names) == 3
        assert len(paths) == 3
        assert "Selected 3 of 10" in reason

    def test_run_invalid_folder_path(self):
        indices, names, paths, reason = self.node.run(
            folder_path="",
            num_images=3,
            seed=42,
            file_names=["a.png"],
        )
        assert indices == []
        assert names == []
        assert paths == []
        assert "Validation error" in reason

    def test_run_invalid_num_images(self):
        indices, names, paths, reason = self.node.run(
            folder_path="/test",
            num_images=0,
            seed=42,
            file_names=["a.png"],
        )
        assert indices == []
        assert names == []
        assert paths == []
        assert "Validation error" in reason

    def test_run_no_file_names(self):
        indices, names, paths, reason = self.node.run(
            folder_path="/test",
            num_images=3,
            seed=42,
            file_names=None,
        )
        assert indices == []
        assert names == []
        assert paths == []
        assert "No files" in reason

    def test_run_reproducible(self):
        file_names = [f"img_{i}.png" for i in range(10)]
        result1 = self.node.run("/test", 3, 7, file_names)
        result2 = self.node.run("/test", 3, 7, file_names)
        assert result1[0] == result2[0]
        assert result1[1] == result2[1]
        assert result1[2] == result2[2]

    def test_run_num_images_exceeds_available(self):
        file_names = ["a.png", "b.png"]
        indices, names, paths, reason = self.node.run(
            folder_path="/test",
            num_images=10,
            seed=42,
            file_names=file_names,
        )
        assert len(indices) == 2
        assert len(names) == 2
        assert "2 of 2" in reason

    def test_run_invalid_file_names_type(self):
        indices, names, paths, reason = self.node.run(
            folder_path="/test",
            num_images=3,
            seed=42,
            file_names="not_a_list",
        )
        assert indices == []
        assert names == []
        assert paths == []
        assert "Validation error" in reason

    def test_run_invalid_file_names_element(self):
        indices, names, paths, reason = self.node.run(
            folder_path="/test",
            num_images=3,
            seed=42,
            file_names=["a.png", 123],
        )
        assert indices == []
        assert names == []
        assert paths == []
        assert "Validation error" in reason

    def test_return_types_and_names(self):
        assert PSN_Random_Image_Selector.RETURN_TYPES == (
            "LIST[INT]",
            "LIST[STRING]",
            "LIST[STRING]",
            "STRING",
        )
        assert PSN_Random_Image_Selector.RETURN_NAMES == (
            "selected_indices",
            "selected_file_names",
            "file_paths",
            "reason",
        )
        assert PSN_Random_Image_Selector.FUNCTION == "run"
        assert PSN_Random_Image_Selector.CATEGORY == "ParametricStudio/Selection"

    def test_input_types_structure(self):
        input_types = PSN_Random_Image_Selector.INPUT_TYPES()
        assert "required" in input_types
        assert "optional" in input_types
        assert "folder_path" in input_types["required"]
        assert "num_images" in input_types["required"]
        assert "seed" in input_types["optional"]
        assert "file_names" in input_types["optional"]
