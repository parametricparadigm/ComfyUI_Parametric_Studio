"""Tests for PSN_Prompt_Attribute_Cutoff node."""

import math
import pytest

from psn_nodes.gen.n_7_attribute_cutoff_for_precise_prompting import (
    PSN_Prompt_Attribute_Cutoff,
    _apply_cutoff,
    _validate_strength,
    _validate_cutoff_position,
    _find_cutoff_index,
)


def test_basic_cutoff_scales_down_subsequent_tokens():
    """Encode 'a red car with blue wheels'. Cutoff at 'red'. Verify tokens after 'red' are scaled."""
    tokens = ["a", "red", "car", "with", "blue", "wheels"]
    magnitudes = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    new_mags, cutoff_idx, reason = _apply_cutoff(tokens, magnitudes, "red", 1, 0.5)
    assert cutoff_idx == 1
    assert "found" in reason
    # Tokens after index 1 should be scaled by (1 - 0.5) = 0.5
    assert new_mags[0] == 1.0
    assert new_mags[1] == 1.0
    assert new_mags[2] == pytest.approx(0.5)
    assert new_mags[3] == pytest.approx(0.5)
    assert new_mags[4] == pytest.approx(0.5)
    assert new_mags[5] == pytest.approx(0.5)


def test_cutoff_token_not_found_uses_position():
    """If cutoff token is not found, use the provided cutoff_position."""
    tokens = ["a", "blue", "car", "with", "red", "wheels"]
    magnitudes = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    new_mags, cutoff_idx, reason = _apply_cutoff(tokens, magnitudes, "green", 2, 0.8)
    assert cutoff_idx == 2
    assert "not found" in reason
    # Tokens after index 2 scaled by (1 - 0.8) = 0.2
    assert new_mags[0] == 1.0
    assert new_mags[1] == 1.0
    assert new_mags[2] == 1.0
    assert new_mags[3] == pytest.approx(0.2)
    assert new_mags[4] == pytest.approx(0.2)
    assert new_mags[5] == pytest.approx(0.2)


def test_strength_zero_no_change():
    """Strength 0 means no scaling; all magnitudes unchanged."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, 2.0, 3.0]
    new_mags, cutoff_idx, reason = _apply_cutoff(tokens, magnitudes, "red", 1, 0.0)
    assert new_mags == [1.0, 2.0, 3.0]
    assert cutoff_idx == 1


def test_strength_one_full_suppression():
    """Strength 1 means full suppression; all magnitudes after cutoff become 0."""
    tokens = ["a", "red", "car", "wheels"]
    magnitudes = [1.0, 2.0, 3.0, 4.0]
    new_mags, cutoff_idx, reason = _apply_cutoff(tokens, magnitudes, "red", 1, 1.0)
    assert new_mags[0] == 1.0
    assert new_mags[1] == 2.0
    assert new_mags[2] == pytest.approx(0.0)
    assert new_mags[3] == pytest.approx(0.0)


def test_cutoff_at_last_token_no_scaling():
    """Cutoff at the last token means no tokens after it to scale."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, 2.0, 3.0]
    new_mags, cutoff_idx, reason = _apply_cutoff(tokens, magnitudes, "car", 2, 0.5)
    assert cutoff_idx == 2
    assert new_mags == [1.0, 2.0, 3.0]


def test_bad_input_strength_out_of_range():
    """Strength outside [0, 1] should raise ValueError."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, 1.0, 1.0]
    with pytest.raises(ValueError, match="strength must be in"):
        _apply_cutoff(tokens, magnitudes, "red", 1, 1.5)
    with pytest.raises(ValueError, match="strength must be in"):
        _apply_cutoff(tokens, magnitudes, "red", 1, -0.1)


def test_bad_input_mismatched_lengths():
    """Tokens and magnitudes must have the same length."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, 1.0]
    with pytest.raises(ValueError, match="must match"):
        _apply_cutoff(tokens, magnitudes, "red", 1, 0.5)


def test_bad_input_non_finite_magnitude():
    """Non-finite magnitudes should raise ValueError."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, float("inf"), 1.0]
    with pytest.raises(ValueError, match="must be finite"):
        _apply_cutoff(tokens, magnitudes, "red", 1, 0.5)


def test_bad_input_cutoff_position_out_of_range():
    """Cutoff position out of range should raise ValueError."""
    tokens = ["a", "red", "car"]
    magnitudes = [1.0, 1.0, 1.0]
    with pytest.raises(ValueError, match="cutoff_position must be in"):
        _apply_cutoff(tokens, magnitudes, "red", 5, 0.5)
    with pytest.raises(ValueError, match="cutoff_position must be in"):
        _apply_cutoff(tokens, magnitudes, "red", -1, 0.5)


def test_node_run_parses_comma_separated_strings():
    """The node's run method should parse comma-separated strings correctly."""
    node = PSN_Prompt_Attribute_Cutoff()
    tokens_str = "a, red, car, with, blue, wheels"
    mags_str = "1.0, 1.0, 1.0, 1.0, 1.0, 1.0"
    new_mags_str, cutoff_idx, reason = node.run(tokens_str, mags_str, "red", 1, 0.5)
    assert cutoff_idx == 1
    mags = [float(x) for x in new_mags_str.split(",")]
    assert len(mags) == 6
    assert mags[0] == pytest.approx(1.0)
    assert mags[1] == pytest.approx(1.0)
    assert mags[2] == pytest.approx(0.5)
    assert mags[3] == pytest.approx(0.5)
    assert mags[4] == pytest.approx(0.5)
    assert mags[5] == pytest.approx(0.5)


def test_node_run_with_empty_tokens():
    """Empty tokens should result in empty magnitudes and no cutoff."""
    node = PSN_Prompt_Attribute_Cutoff()
    tokens_str = ""
    mags_str = ""
    new_mags_str, cutoff_idx, reason = node.run(tokens_str, mags_str, "red", 0, 0.5)
    assert cutoff_idx == 0
    assert new_mags_str == ""
    assert "not found" in reason


def test_find_cutoff_index_returns_first_occurrence():
    """Should return the first occurrence of the token."""
    tokens = ["a", "red", "car", "red", "wheels"]
    assert _find_cutoff_index(tokens, "red") == 1
    assert _find_cutoff_index(tokens, "blue") == -1
    assert _find_cutoff_index(tokens, "a") == 0
