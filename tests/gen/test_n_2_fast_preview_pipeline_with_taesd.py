"""Tests for PSN_TAESD_Preview_Decode (pure-logic planning node)."""

import json
import pytest

from psn_nodes.gen.n_2_fast_preview_pipeline_with_taesd import (
    PSN_TAESD_Preview_Decode,
    _validate_channels,
    _validate_model_descriptor,
    _compute_preview_plan,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_node(**kwargs):
    """Run the node with sensible defaults, overriding via kwargs."""
    defaults = {
        "latent_channels": 4,
        "latent_width": 64,
        "latent_height": 64,
        "model_name": "taesd.safetensors",
        "model_type": "taesd",
        "extra_config": None,
    }
    defaults.update(kwargs)
    node = PSN_TAESD_Preview_Decode()
    return node.run(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_sd_latent_produces_plan():
    """A standard 4-channel SD latent should produce a valid plan."""
    valid, plan_json, reason = _run_node()
    assert valid is True
    assert reason == "ok"
    plan = json.loads(plan_json)
    assert plan["operation"] == "taesd_preview_decode"
    assert plan["quality"] == "low"
    assert plan["latent"]["channels"] == 4
    assert plan["preview"]["preview_w"] > 0
    assert plan["preview"]["preview_h"] > 0
    assert plan["preview"]["est_vram_ratio"] == 0.15


def test_rejects_standard_vae_model():
    """A standard VAE model type must be rejected with a clear message."""
    valid, plan_json, reason = _run_node(model_type="standard_vae")
    assert valid is False
    assert "not a TAESD variant" in reason
    assert plan_json == "{}"


def test_rejects_non_taesd_model_name():
    """A model name that does not contain 'taesd' should be rejected."""
    valid, plan_json, reason = _run_node(model_name="sdxl_vae.safetensors")
    assert valid is False
    assert "does not appear to be a TAESD model" in reason


def test_rejects_unsupported_channel_count():
    """Channel counts outside the TAESD allow-list (4, 16) must fail."""
    valid, plan_json, reason = _run_node(latent_channels=8)
    assert valid is False
    assert "does not support 8-channel" in reason


def test_accepts_flux_16_channel_latent():
    """Flux uses 16-channel latents; TAESD should accept them."""
    valid, plan_json, reason = _run_node(latent_channels=16, latent_width=128, latent_height=128)
    assert valid is True
    plan = json.loads(plan_json)
    assert plan["latent"]["channels"] == 16


def test_rejects_invalid_extra_config_json():
    """Malformed JSON in extra_config should be rejected."""
    valid, plan_json, reason = _run_node(extra_config="{not valid json")
    assert valid is False
    assert "not valid JSON" in reason


def test_extra_config_must_be_object():
    """extra_config that is valid JSON but not an object should be rejected."""
    valid, plan_json, reason = _run_node(extra_config="[1, 2, 3]")
    assert valid is False
    assert "must be a JSON object" in reason


def test_preview_dims_are_aligned_to_8():
    """Preview dimensions should be multiples of 8."""
    valid, plan_json, reason = _run_node(latent_width=64, latent_height=64)
    assert valid is True
    plan = json.loads(plan_json)
    pw = plan["preview"]["preview_w"]
    ph = plan["preview"]["preview_h"]
    assert pw % 8 == 0
    assert ph % 8 == 0
    assert pw >= 64
    assert ph >= 64


def test_preview_dims_respect_max():
    """Very large latents should still produce preview dims <= 1024."""
    valid, plan_json, reason = _run_node(latent_width=512, latent_height=512)
    assert valid is True
    plan = json.loads(plan_json)
    assert plan["preview"]["preview_w"] <= 1024
    assert plan["preview"]["preview_h"] <= 1024


def test_rejects_non_integer_channels():
    """Channels must be an integer; floats and booleans are rejected."""
    valid, plan_json, reason = _run_node(latent_channels=4.0)
    assert valid is False
    assert "must be an integer" in reason


def test_rejects_negative_latent_width():
    """Latent width below 8 should be rejected."""
    valid, plan_json, reason = _run_node(latent_width=4)
    assert valid is False
    assert "latent_width" in reason


def test_empty_model_name_rejected():
    """An empty model name should be rejected."""
    valid, plan_json, reason = _run_node(model_name="")
    assert valid is False
    assert "non-empty string" in reason


def test_valid_extra_config_is_included():
    """Valid extra config should appear in the payload."""
    cfg = json.dumps({"seed": 42, "steps": 4})
    valid, plan_json, reason = _run_node(extra_config=cfg)
    assert valid is True
    plan = json.loads(plan_json)
    assert plan["extra"]["seed"] == 42
    assert plan["extra"]["steps"] == 4


def test_node_registry():
    """The module should expose the expected registry entries."""
    from psn_nodes.gen.n_2_fast_preview_pipeline_with_taesd import (
        NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS,
    )
    assert "PSN_TAESD_Preview_Decode" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_TAESD_Preview_Decode"] is PSN_TAESD_Preview_Decode
    assert "PSN_TAESD_Preview_Decode" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_structure():
    """INPUT_TYPES should declare the expected fields."""
    it = PSN_TAESD_Preview_Decode.INPUT_TYPES()
    assert "required" in it
    assert "latent_channels" in it["required"]
    assert "model_type" in it["required"]
    assert "optional" in it
    assert "extra_config" in it["optional"]
