"""
Tests for psn_nodes.gen.psn_repro_layer.

Covers:
  * PSN_Fixed_Seed_Generator: deterministic mode, offset mode, edge cases,
    bad inputs.
  * PSN_Batch_Invariant_Sampler: plan correctness, fingerprint stability,
    parameter validation, bad inputs.
"""

import json

import pytest

from psn_nodes.gen.psn_repro_layer import (
    PSN_Fixed_Seed_Generator,
    PSN_Batch_Invariant_Sampler,
    _SEED_MODULUS,
)


# ---------------------------------------------------------------------------
# PSN_Fixed_Seed_Generator
# ---------------------------------------------------------------------------

class TestPSNFixedSeedGenerator:

    def test_deterministic_mode_ignores_batch_index(self):
        node = PSN_Fixed_Seed_Generator()
        seed_a = node.run(base_seed=12345, batch_index=0, mode="deterministic")[0]
        seed_b = node.run(base_seed=12345, batch_index=99, mode="deterministic")[0]
        assert seed_a == seed_b == 12345

    def test_offset_mode_adds_batch_index(self):
        node = PSN_Fixed_Seed_Generator()
        seed = node.run(base_seed=100, batch_index=50, mode="offset")[0]
        assert seed == 150

    def test_offset_mode_wraps_at_32bit(self):
        node = PSN_Fixed_Seed_Generator()
        seed = node.run(base_seed=_SEED_MODULUS - 1, batch_index=1, mode="offset")[0]
        assert seed == 0

    def test_negative_base_seed_wraps(self):
        node = PSN_Fixed_Seed_Generator()
        seed = node.run(base_seed=-1, batch_index=0, mode="deterministic")[0]
        assert seed == _SEED_MODULUS - 1

    def test_invalid_mode_raises(self):
        node = PSN_Fixed_Seed_Generator()
        with pytest.raises(ValueError, match="mode must be one of"):
            node.run(base_seed=0, batch_index=0, mode="bogus")

    def test_non_int_base_seed_raises(self):
        node = PSN_Fixed_Seed_Generator()
        with pytest.raises(TypeError, match="seed value must be an int"):
            node.run(base_seed="123", batch_index=0, mode="deterministic")

    def test_negative_batch_index_raises(self):
        node = PSN_Fixed_Seed_Generator()
        with pytest.raises(ValueError, match="batch_index must be >= 0"):
            node.run(base_seed=0, batch_index=-1, mode="offset")


# ---------------------------------------------------------------------------
# PSN_Batch_Invariant_Sampler
# ---------------------------------------------------------------------------

class TestPSNBatchInvariantSampler:

    def _default_kwargs(self, **overrides):
        kwargs = {
            "model_id": "model_0",
            "positive_id": "pos_0",
            "negative_id": "neg_0",
            "latent_id": "lat_0",
            "seed": 42,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "device": "cuda:0",
        }
        kwargs.update(overrides)
        return kwargs

    def test_plan_contains_all_fields(self):
        node = PSN_Batch_Invariant_Sampler()
        plan_json, fp = node.run(**self._default_kwargs())
        plan = json.loads(plan_json)
        assert plan["seed"] == 42
        assert plan["steps"] == 20
        assert plan["cfg"] == 7.0
        assert plan["sampler_name"] == "euler"
        assert plan["scheduler"] == "normal"
        assert plan["device"] == "cuda:0"
        assert plan["determinism"]["cudnn_deterministic"] is True
        assert plan["determinism"]["use_deterministic_algorithms"] is True
        assert plan["determinism"]["batch_invariant"] is True

    def test_fingerprint_is_stable(self):
        node = PSN_Batch_Invariant_Sampler()
        _, fp1 = node.run(**self._default_kwargs())
        _, fp2 = node.run(**self._default_kwargs())
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_fingerprint_changes_with_seed(self):
        node = PSN_Batch_Invariant_Sampler()
        _, fp1 = node.run(**self._default_kwargs(seed=42))
        _, fp2 = node.run(**self._default_kwargs(seed=43))
        assert fp1 != fp2

    def test_seed_wraps_to_32bit(self):
        node = PSN_Batch_Invariant_Sampler()
        plan_json, _ = node.run(**self._default_kwargs(seed=_SEED_MODULUS + 5))
        plan = json.loads(plan_json)
        assert plan["seed"] == 5

    def test_invalid_sampler_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="sampler_name must be one of"):
            node.run(**self._default_kwargs(sampler_name="not_a_sampler"))

    def test_invalid_scheduler_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="scheduler must be one of"):
            node.run(**self._default_kwargs(scheduler="bad_sched"))

    def test_steps_below_minimum_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="steps must be >= 1"):
            node.run(**self._default_kwargs(steps=0))

    def test_cfg_out_of_range_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="cfg must be in"):
            node.run(**self._default_kwargs(cfg=200.0))

    def test_empty_model_id_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="model_id must be a non-empty string"):
            node.run(**self._default_kwargs(model_id="   "))

    def test_invalid_device_raises(self):
        node = PSN_Batch_Invariant_Sampler()
        with pytest.raises(ValueError, match="device must be one of"):
            node.run(**self._default_kwargs(device="cuda:99"))
