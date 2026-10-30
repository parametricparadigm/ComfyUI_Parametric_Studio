"""
Tests for psn_nodes.gen.n_7_visual_regional_prompting
"""

import json
import pytest

from psn_nodes.gen.n_7_visual_regional_prompting import (
    PSN_RegionalMask,
    PSN_RegionalPrompt,
    _validate_bbox,
    _build_mask_rows,
    _validate_regions,
    _compute_attention_weights,
)


class TestValidateBbox:
    def test_valid_bbox(self):
        result = _validate_bbox([10, 20, 100, 50], 512, 512)
        assert result == (10, 20, 100, 50)

    def test_bbox_clamped_to_bounds(self):
        # x=500, w=100 would exceed width=512, so w clamped to 12
        result = _validate_bbox([500, 0, 100, 50], 512, 512)
        assert result == (500, 0, 12, 50)

    def test_bbox_negative_clamped(self):
        result = _validate_bbox([-10, -5, 100, 50], 512, 512)
        assert result == (0, 0, 100, 50)

    def test_bbox_invalid_length(self):
        with pytest.raises(ValueError, match="4 ints"):
            _validate_bbox([10, 20, 100], 512, 512)

    def test_bbox_non_positive_size(self):
        with pytest.raises(ValueError, match="positive"):
            _validate_bbox([10, 20, 0, 50], 512, 512)

    def test_bbox_non_numeric(self):
        with pytest.raises(ValueError, match="numeric"):
            _validate_bbox([10, "a", 100, 50], 512, 512)


class TestBuildMaskRows:
    def test_full_image_mask(self):
        bbox = (0, 0, 4, 3)
        rows = _build_mask_rows(bbox, 4, 3)
        assert rows == ["1111", "1111", "1111"]

    def test_partial_mask(self):
        bbox = (1, 1, 2, 2)
        rows = _build_mask_rows(bbox, 4, 4)
        assert rows[0] == "0000"
        assert rows[1] == "0110"
        assert rows[2] == "0110"
        assert rows[3] == "0000"

    def test_single_pixel_mask(self):
        bbox = (2, 1, 1, 1)
        rows = _build_mask_rows(bbox, 4, 3)
        assert rows[0] == "0000"
        assert rows[1] == "0010"
        assert rows[2] == "0000"


class TestValidateRegions:
    def test_valid_regions(self):
        regions = {
            "left": {"bbox": [0, 0, 256, 512], "prompt": "a cat"},
            "right": {"bbox": [256, 0, 256, 512], "prompt": "a dog"},
        }
        entries = _validate_regions(regions, 512, 512)
        assert len(entries) == 2
        assert entries[0]["name"] == "left"
        assert entries[0]["prompt"] == "a cat"
        assert entries[1]["name"] == "right"
        assert entries[1]["prompt"] == "a dog"

    def test_regions_not_dict(self):
        with pytest.raises(ValueError, match="dict"):
            _validate_regions("not a dict", 512, 512)

    def test_region_missing_bbox(self):
        regions = {"r1": {"prompt": "hello"}}
        with pytest.raises(ValueError, match="missing 'bbox'"):
            _validate_regions(regions, 512, 512)

    def test_region_missing_prompt(self):
        regions = {"r1": {"bbox": [0, 0, 10, 10]}}
        with pytest.raises(ValueError, match="missing 'prompt'"):
            _validate_regions(regions, 512, 512)

    def test_region_empty_name(self):
        regions = {"": {"bbox": [0, 0, 10, 10], "prompt": "x"}}
        with pytest.raises(ValueError, match="non-empty"):
            _validate_regions(regions, 512, 512)


class TestComputeAttentionWeights:
    def test_even_distribution(self):
        entries = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        weights = _compute_attention_weights(entries, 3.0)
        assert weights == [1.0, 1.0, 1.0]

    def test_single_region_full_strength(self):
        entries = [{"name": "only"}]
        weights = _compute_attention_weights(entries, 2.5)
        assert weights == [2.5]

    def test_empty_entries(self):
        weights = _compute_attention_weights([], 1.0)
        assert weights == []


class TestPSNRegionalMask:
    def test_run_valid(self):
        node = PSN_RegionalMask()
        mask_json, info_json = node.run(4, 3, "[0, 0, 4, 3]")
        mask = json.loads(mask_json)
        assert mask == ["1111", "1111", "1111"]
        info = json.loads(info_json)
        assert info["bbox"] == [0, 0, 4, 3]

    def test_run_partial(self):
        node = PSN_RegionalMask()
        mask_json, _ = node.run(4, 4, "[1, 1, 2, 2]")
        mask = json.loads(mask_json)
        assert mask[1] == "0110"

    def test_run_invalid_bbox_json(self):
        node = PSN_RegionalMask()
        with pytest.raises(ValueError, match="valid JSON"):
            node.run(4, 4, "not json")

    def test_run_bbox_out_of_bounds_clamped(self):
        node = PSN_RegionalMask()
        mask_json, info_json = node.run(4, 4, "[2, 2, 100, 100]")
        info = json.loads(info_json)
        # w clamped to 2 (4-2), h clamped to 2
        assert info["bbox"] == [2, 2, 2, 2]


class TestPSNRegionalPrompt:
    def test_run_two_regions(self):
        node = PSN_RegionalPrompt()
        regions = json.dumps({
            "left": {"bbox": [0, 0, 256, 512], "prompt": "a cat"},
            "right": {"bbox": [256, 0, 256, 512], "prompt": "a dog"},
        })
        plan_json, count, status = node.run(512, 512, regions, 2.0)
        assert status == "ok"
        assert count == 2
        plan = json.loads(plan_json)
        assert len(plan["regions"]) == 2
        assert plan["regions"][0]["prompt"] == "a cat"
        assert plan["regions"][1]["prompt"] == "a dog"
        # Each gets 2.0/2 = 1.0
        assert plan["regions"][0]["attention_weight"] == 1.0

    def test_run_empty_regions(self):
        node = PSN_RegionalPrompt()
        plan_json, count, status = node.run(512, 512, "{}", 1.0)
        assert status == "ok"
        assert count == 0
        plan = json.loads(plan_json)
        assert plan["regions"] == []

    def test_run_invalid_json(self):
        node = PSN_RegionalPrompt()
        _, _, status = node.run(512, 512, "not json", 1.0)
        assert status.startswith("error:")

    def test_run_region_missing_prompt(self):
        node = PSN_RegionalPrompt()
        regions = json.dumps({"r1": {"bbox": [0, 0, 10, 10]}})
        _, _, status = node.run(512, 512, regions, 1.0)
        assert "missing 'prompt'" in status

    def test_run_bbox_out_of_bounds(self):
        node = PSN_RegionalPrompt()
        regions = json.dumps({"r1": {"bbox": [500, 500, 100, 100], "prompt": "x"}})
        plan_json, count, status = node.run(512, 512, regions, 1.0)
        assert status == "ok"
        plan = json.loads(plan_json)
        # bbox clamped: x=500, y=500, w=12, h=12
        assert plan["regions"][0]["bbox"] == [500, 500, 12, 12]

    def test_run_zero_attention_strength(self):
        node = PSN_RegionalPrompt()
        regions = json.dumps({"r1": {"bbox": [0, 0, 10, 10], "prompt": "x"}})
        plan_json, _, status = node.run(512, 512, regions, 0.0)
        assert status == "ok"
        plan = json.loads(plan_json)
        assert plan["regions"][0]["attention_weight"] == 0.0
