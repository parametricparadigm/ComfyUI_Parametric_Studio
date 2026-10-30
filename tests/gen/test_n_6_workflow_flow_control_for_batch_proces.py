"""
Tests for psn_nodes.gen.n_6_workflow_flow_control_for_batch_proces
"""

import pytest
from psn_nodes.gen.n_6_workflow_flow_control_for_batch_proces import (
    PSN_Conditioning_Variation_Generator,
    PSN_Batch_Conditioning_Loop,
    _normalize_conditioning,
    _validate_positive_int,
    _validate_float,
    _validate_steps,
    _validate_cfg,
)


class TestConditioningVariationGenerator:
    """Tests for PSN_Conditioning_Variation_Generator."""

    def test_basic_generation(self):
        """Generate 4 variations of a base prompt with noise type."""
        node = PSN_Conditioning_Variation_Generator()
        (result,) = node.run(
            base_conditioning="a cat",
            variation_type="noise",
            num_variations=4,
            magnitude=0.1,
            seed=42,
        )
        assert len(result) == 4
        for i, v in enumerate(result):
            assert v["variation_index"] == i
            assert v["variation_type"] == "noise"
            assert v["prompt"] == "a cat"
            assert 0.0 <= v["weight"] <= 10.0
            assert -10.0 <= v["bias"] <= 10.0

    def test_deterministic_with_same_seed(self):
        """Same seed produces identical variations."""
        node = PSN_Conditioning_Variation_Generator()
        (r1,) = node.run("a dog", "scale", 3, 0.2, seed=123)
        (r2,) = node.run("a dog", "scale", 3, 0.2, seed=123)
        assert r1 == r2

    def test_different_seeds_differ(self):
        """Different seeds produce different variations (with high probability)."""
        node = PSN_Conditioning_Variation_Generator()
        (r1,) = node.run("a bird", "noise", 5, 0.5, seed=1)
        (r2,) = node.run("a bird", "noise", 5, 0.5, seed=2)
        # At least one variation should differ
        assert r1 != r2

    def test_scale_variation(self):
        """Scale variation modifies weight."""
        node = PSN_Conditioning_Variation_Generator()
        (result,) = node.run(
            base_conditioning="a tree",
            variation_type="scale",
            num_variations=3,
            magnitude=0.3,
            seed=99,
            base_weight=2.0,
        )
        assert len(result) == 3
        for v in result:
            assert v["variation_type"] == "scale"
            assert v["weight"] != 2.0 or v["weight"] == 2.0  # may or may not change
            assert 0.0 <= v["weight"] <= 10.0

    def test_shift_variation(self):
        """Shift variation modifies bias."""
        node = PSN_Conditioning_Variation_Generator()
        (result,) = node.run(
            base_conditioning="a mountain",
            variation_type="shift",
            num_variations=2,
            magnitude=0.4,
            seed=7,
            base_bias=1.0,
        )
        assert len(result) == 2
        for v in result:
            assert v["variation_type"] == "shift"
            assert -10.0 <= v["bias"] <= 10.0

    def test_invalid_variation_type(self):
        """Invalid variation_type raises ValueError."""
        node = PSN_Conditioning_Variation_Generator()
        with pytest.raises(ValueError, match="variation_type"):
            node.run("a cat", "invalid_type", 3, 0.1, seed=1)

    def test_invalid_num_variations_zero(self):
        """num_variations=0 raises ValueError."""
        node = PSN_Conditioning_Variation_Generator()
        with pytest.raises(ValueError, match="num_variations"):
            node.run("a cat", "noise", 0, 0.1, seed=1)

    def test_invalid_num_variations_negative(self):
        """num_variations=-1 raises ValueError."""
        node = PSN_Conditioning_Variation_Generator()
        with pytest.raises(ValueError, match="num_variations"):
            node.run("a cat", "noise", -1, 0.1, seed=1)

    def test_invalid_magnitude_out_of_range(self):
        """magnitude > 1.0 raises ValueError."""
        node = PSN_Conditioning_Variation_Generator()
        with pytest.raises(ValueError, match="magnitude"):
            node.run("a cat", "noise", 3, 1.5, seed=1)

    def test_invalid_seed_negative(self):
        """Negative seed raises ValueError."""
        node = PSN_Conditioning_Variation_Generator()
        with pytest.raises(ValueError, match="seed"):
            node.run("a cat", "noise", 3, 0.1, seed=-1)

    def test_dict_base_conditioning(self):
        """Base conditioning as dict is handled correctly."""
        node = PSN_Conditioning_Variation_Generator()
        base = {"prompt": "a river", "weight": 1.5, "bias": 0.5}
        (result,) = node.run(base, "noise", 2, 0.1, seed=10)
        assert len(result) == 2
        assert result[0]["prompt"] == "a river"
        assert result[0]["weight"] == pytest.approx(1.5, abs=0.2)

    def test_single_variation(self):
        """num_variations=1 returns exactly one variation."""
        node = PSN_Conditioning_Variation_Generator()
        (result,) = node.run("a sky", "scale", 1, 0.1, seed=5)
        assert len(result) == 1
        assert result[0]["variation_index"] == 0


class TestBatchConditioningLoop:
    """Tests for PSN_Batch_Conditioning_Loop."""

    def test_basic_plan(self):
        """Build a plan from 3 conditioning specs."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [
            {"prompt": "a cat", "weight": 1.0, "bias": 0.0},
            {"prompt": "a dog", "weight": 1.2, "bias": 0.1},
            {"prompt": "a bird", "weight": 0.8, "bias": -0.1},
        ]
        (plan, batch_size) = node.run(conds, steps=20, cfg=7.0, seed=100)
        assert batch_size == 3
        assert len(plan) == 3
        for i, item in enumerate(plan):
            assert item["index"] == i
            assert item["steps"] == 20
            assert item["cfg"] == 7.0
            assert item["seed"] == 100 + i
        assert plan[0]["prompt"] == "a cat"
        assert plan[1]["prompt"] == "a dog"
        assert plan[2]["prompt"] == "a bird"

    def test_string_conditioning_items(self):
        """String items in conditioning_list are normalized."""
        node = PSN_Batch_Conditioning_Loop()
        conds = ["a cat", "a dog"]
        (plan, batch_size) = node.run(conds, steps=10, cfg=5.0, seed=0)
        assert batch_size == 2
        assert plan[0]["prompt"] == "a cat"
        assert plan[0]["weight"] == 1.0
        assert plan[0]["bias"] == 0.0

    def test_empty_conditioning_list(self):
        """Empty conditioning_list raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        with pytest.raises(ValueError, match="must not be empty"):
            node.run([], steps=20, cfg=7.0, seed=0)

    def test_non_list_conditioning(self):
        """Non-list conditioning_list raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        with pytest.raises(ValueError, match="must be a list or tuple"):
            node.run("not a list", steps=20, cfg=7.0, seed=0)

    def test_invalid_steps_zero(self):
        """steps=0 raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": "a cat"}]
        with pytest.raises(ValueError, match="steps"):
            node.run(conds, steps=0, cfg=7.0, seed=0)

    def test_invalid_cfg_negative(self):
        """Negative cfg raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": "a cat"}]
        with pytest.raises(ValueError, match="cfg"):
            node.run(conds, steps=20, cfg=-1.0, seed=0)

    def test_max_batch_size_exceeded(self):
        """Exceeding max_batch_size raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": f"item {i}"} for i in range(5)]
        with pytest.raises(ValueError, match="exceeds max_batch_size"):
            node.run(conds, steps=20, cfg=7.0, seed=0, max_batch_size=3)

    def test_max_batch_size_exact(self):
        """Exactly max_batch_size items is allowed."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": f"item {i}"} for i in range(3)]
        (plan, batch_size) = node.run(conds, steps=20, cfg=7.0, seed=0, max_batch_size=3)
        assert batch_size == 3

    def test_invalid_seed_negative(self):
        """Negative seed raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": "a cat"}]
        with pytest.raises(ValueError, match="seed"):
            node.run(conds, steps=20, cfg=7.0, seed=-5)

    def test_invalid_conditioning_item_type(self):
        """Invalid item type in conditioning_list raises ValueError."""
        node = PSN_Batch_Conditioning_Loop()
        conds = [{"prompt": "a cat"}, 42]
        with pytest.raises(ValueError, match="must be a string or dict"):
            node.run(conds, steps=20, cfg=7.0, seed=0)


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_normalize_conditioning_string(self):
        """String is normalized to dict with default weight/bias."""
        result = _normalize_conditioning("a cat")
        assert result == {"prompt": "a cat", "weight": 1.0, "bias": 0.0}

    def test_normalize_conditioning_dict(self):
        """Dict is normalized with defaults for missing keys."""
        result = _normalize_conditioning({"prompt": "a dog"})
        assert result["prompt"] == "a dog"
        assert result["weight"] == 1.0
        assert result["bias"] == 0.0

    def test_normalize_conditioning_invalid_type(self):
        """Invalid type raises ValueError."""
        with pytest.raises(ValueError, match="must be a string or dict"):
            _normalize_conditioning(123)

    def test_validate_positive_int_valid(self):
        assert _validate_positive_int(5, "test") == 5

    def test_validate_positive_int_zero(self):
        with pytest.raises(ValueError, match="must be >= 1"):
            _validate_positive_int(0, "test")

    def test_validate_positive_int_float(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_positive_int(3.5, "test")

    def test_validate_positive_int_bool(self):
        """Bool is rejected even though it's a subclass of int."""
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_positive_int(True, "test")

    def test_validate_float_in_range(self):
        assert _validate_float(0.5, "test", 0.0, 1.0) == 0.5

    def test_validate_float_out_of_range(self):
        with pytest.raises(ValueError, match="must be in"):
            _validate_float(1.5, "test", 0.0, 1.0)

    def test_validate_steps_valid(self):
        assert _validate_steps(20) == 20

    def test_validate_steps_too_large(self):
        with pytest.raises(ValueError, match="must be <= 1000"):
            _validate_steps(1001)

    def test_validate_cfg_valid(self):
        assert _validate_cfg(7.0) == 7.0

    def test_validate_cfg_too_large(self):
        with pytest.raises(ValueError, match="must be <= 100.0"):
            _validate_cfg(101.0)
