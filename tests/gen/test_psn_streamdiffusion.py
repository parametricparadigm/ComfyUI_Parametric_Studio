"""Tests for psn_nodes.gen.psn_streamdiffusion (pure-logic StreamDiffusion state machine)."""

import json
import math

import pytest

from psn_nodes.gen.psn_streamdiffusion import (
    PSN_Stream_Init,
    PSN_Stream_Step,
    _make_state,
    _step_state,
    _validate_steps,
    _validate_guidance,
    _validate_prompt,
    _compute_noise_level,
)


# ---------------------------------------------------------------------------
# PSN_Stream_Init tests
# ---------------------------------------------------------------------------


def test_psn_stream_init_creates_valid_state():
    node = PSN_Stream_Init()
    (state,) = node.run(steps=4, guidance_scale=1.0, schedule_mode="linear")
    assert isinstance(state, dict)
    assert state["steps"] == 4
    assert state["guidance_scale"] == 1.0
    assert state["schedule_mode"] == "linear"
    assert state["current_step"] == 0
    assert state["completed"] is False
    assert state["activation_cache"] == {}
    assert state["history"] == []


def test_psn_stream_init_rejects_bad_steps():
    node = PSN_Stream_Init()
    with pytest.raises(ValueError, match="steps must be"):
        node.run(steps=0, guidance_scale=1.0, schedule_mode="linear")
    with pytest.raises(ValueError, match="steps must be"):
        node.run(steps=2000, guidance_scale=1.0, schedule_mode="linear")


def test_psn_stream_init_rejects_bad_guidance():
    node = PSN_Stream_Init()
    with pytest.raises(ValueError, match="guidance_scale must be"):
        node.run(steps=4, guidance_scale=-1.0, schedule_mode="linear")
    with pytest.raises(ValueError, match="guidance_scale must be"):
        node.run(steps=4, guidance_scale=200.0, schedule_mode="linear")


def test_psn_stream_init_rejects_bad_schedule_mode():
    node = PSN_Stream_Init()
    with pytest.raises(ValueError, match="schedule_mode must be"):
        node.run(steps=4, guidance_scale=1.0, schedule_mode="quadratic")


# ---------------------------------------------------------------------------
# PSN_Stream_Step tests
# ---------------------------------------------------------------------------


def test_psn_stream_step_advances_state_and_preserves_keys():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=4, guidance_scale=2.0, schedule_mode="cosine")
    original_keys = set(state.keys())

    image_json, new_state = step_node.run(stream_state=state, prompt="a cat")

    # State keys preserved
    assert set(new_state.keys()) == original_keys
    assert new_state["current_step"] == 1
    assert new_state["completed"] is False
    assert new_state["steps"] == 4
    assert new_state["guidance_scale"] == 2.0
    assert new_state["schedule_mode"] == "cosine"

    # Activation cache updated
    assert "step_0" in new_state["activation_cache"]
    entry = new_state["activation_cache"]["step_0"]
    assert entry["step"] == 0
    assert entry["prompt_hash"] == hash("a cat") % (10 ** 9)
    assert entry["has_image_input"] is False

    # History updated
    assert len(new_state["history"]) == 1
    assert new_state["history"][0]["step"] == 0
    assert new_state["history"][0]["prompt"] == "a cat"

    # Image output is valid JSON
    payload = json.loads(image_json)
    assert payload["step"] == 0
    assert payload["total_steps"] == 4
    assert payload["prompt"] == "a cat"
    assert payload["completed"] is False


def test_psn_stream_step_completes_after_all_steps():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=2, guidance_scale=1.0, schedule_mode="linear")

    _, state = step_node.run(stream_state=state, prompt="frame 1")
    assert state["current_step"] == 1
    assert state["completed"] is False

    image_json, state = step_node.run(stream_state=state, prompt="frame 2")
    assert state["current_step"] == 2
    assert state["completed"] is True

    payload = json.loads(image_json)
    assert payload["completed"] is True


def test_psn_stream_step_rejects_completed_state():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=1, guidance_scale=1.0, schedule_mode="linear")
    _, state = step_node.run(stream_state=state, prompt="only step")
    assert state["completed"] is True

    with pytest.raises(ValueError, match="already completed"):
        step_node.run(stream_state=state, prompt="extra step")


def test_psn_stream_step_rejects_missing_keys():
    step_node = PSN_Stream_Step()
    bad_state = {"steps": 4, "guidance_scale": 1.0}  # missing many keys
    with pytest.raises(ValueError, match="missing keys"):
        step_node.run(stream_state=bad_state, prompt="test")


def test_psn_stream_step_rejects_empty_prompt():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=4, guidance_scale=1.0, schedule_mode="linear")
    with pytest.raises(ValueError, match="prompt must not be empty"):
        step_node.run(stream_state=state, prompt="")


def test_psn_stream_step_rejects_non_string_prompt():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=4, guidance_scale=1.0, schedule_mode="linear")
    with pytest.raises(ValueError, match="prompt must be a string"):
        step_node.run(stream_state=state, prompt=12345)


def test_psn_stream_step_with_optional_image_input():
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=4, guidance_scale=1.0, schedule_mode="linear")
    image_json, new_state = step_node.run(
        stream_state=state, prompt="img2img test", image='{"width":512,"height":512}'
    )
    entry = new_state["activation_cache"]["step_0"]
    assert entry["has_image_input"] is True


# ---------------------------------------------------------------------------
# Schedule / noise level tests
# ---------------------------------------------------------------------------


def test_compute_noise_level_linear():
    assert _compute_noise_level(0, 4, "linear") == pytest.approx(1.0)
    assert _compute_noise_level(1, 4, "linear") == pytest.approx(0.75)
    assert _compute_noise_level(2, 4, "linear") == pytest.approx(0.5)
    assert _compute_noise_level(3, 4, "linear") == pytest.approx(0.25)


def test_compute_noise_level_cosine():
    # t=0 -> 0.5*(1+cos(0)) = 1.0
    assert _compute_noise_level(0, 4, "cosine") == pytest.approx(1.0)
    # t=1 (step 3 of 4) -> 0.5*(1+cos(3pi/4)) = 0.5*(1 - sqrt(2)/2)
    expected = 0.5 * (1.0 + math.cos(math.pi * 3.0 / 4.0))
    assert _compute_noise_level(3, 4, "cosine") == pytest.approx(expected)


def test_compute_noise_level_exponential():
    assert _compute_noise_level(0, 4, "exponential") == pytest.approx(1.0)
    expected = math.exp(-3.0 * 3.0 / 4.0)
    assert _compute_noise_level(3, 4, "exponential") == pytest.approx(expected)


def test_compute_noise_level_rejects_bad_inputs():
    with pytest.raises(ValueError, match="total_steps must be positive"):
        _compute_noise_level(0, 0, "linear")
    with pytest.raises(ValueError, match="step_index out of range"):
        _compute_noise_level(5, 4, "linear")
    with pytest.raises(ValueError, match="unknown schedule mode"):
        _compute_noise_level(0, 4, "quadratic")


# ---------------------------------------------------------------------------
# Validation helper tests
# ---------------------------------------------------------------------------


def test_validate_steps_edge_cases():
    assert _validate_steps(1) == 1
    assert _validate_steps(1024) == 1024
    with pytest.raises(ValueError):
        _validate_steps(0)
    with pytest.raises(ValueError):
        _validate_steps(1025)
    with pytest.raises(ValueError, match="steps must be an integer"):
        _validate_steps(4.5)


def test_validate_guidance_edge_cases():
    assert _validate_guidance(0.0) == 0.0
    assert _validate_guidance(100.0) == 100.0
    with pytest.raises(ValueError):
        _validate_guidance(-0.1)
    with pytest.raises(ValueError):
        _validate_guidance(100.1)
    with pytest.raises(ValueError, match="finite"):
        _validate_guidance(float("nan"))
    with pytest.raises(ValueError, match="finite"):
        _validate_guidance(float("inf"))


def test_validate_prompt_edge_cases():
    assert _validate_prompt("hello") == "hello"
    assert _validate_prompt("x" * 4096) == "x" * 4096
    with pytest.raises(ValueError, match="must not be empty"):
        _validate_prompt("")
    with pytest.raises(ValueError, match="at most 4096"):
        _validate_prompt("x" * 4097)
    with pytest.raises(ValueError, match="must be a string"):
        _validate_prompt(None)


# ---------------------------------------------------------------------------
# Multi-step loop test (simulates the data flow)
# ---------------------------------------------------------------------------


def test_psn_stream_full_loop_10_steps():
    """Simulate 10 incremental steps and verify state integrity throughout."""
    init_node = PSN_Stream_Init()
    step_node = PSN_Stream_Step()

    (state,) = init_node.run(steps=10, guidance_scale=3.5, schedule_mode="exponential")
    expected_keys = set(state.keys())

    for i in range(10):
        image_json, state = step_node.run(stream_state=state, prompt="frame {}".format(i))
        assert set(state.keys()) == expected_keys, "keys changed at step {}".format(i)
        assert state["current_step"] == i + 1
        assert len(state["activation_cache"]) == i + 1
        assert len(state["history"]) == i + 1

        payload = json.loads(image_json)
        assert payload["step"] == i
        assert payload["total_steps"] == 10

    assert state["completed"] is True
    assert state["current_step"] == 10
    assert len(state["activation_cache"]) == 10
    assert len(state["history"]) == 10
