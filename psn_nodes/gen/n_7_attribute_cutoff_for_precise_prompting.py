"""PSN_Prompt_Attribute_Cutoff: pure-logic prompt attribute cutoff.

This module implements the pure-logic, secure-by-design part of the
"Attribute Cutoff for Precise Prompting" node. It does NOT touch torch,
ComfyUI, or any GPU internals. Instead it operates on plain Python values:
a list of token strings (the tokenized prompt) and a list of numeric
embedding magnitudes (one per token). It locates the cutoff token, then
scales down the magnitudes of all tokens after that position by a strength
factor. This mirrors the intended behavior of reducing the influence of
subsequent attributes without requiring a tokenizer or tensor library.

The node takes plain values (strings, numbers, lists) and returns plain
values (lists, numbers, strings). No file, network, subprocess, or OS access.
"""

import math

CAT = "ParametricStudio/Prompting"


def _validate_strength(strength):
    """Validate the strength factor. Must be a finite number in [0, 1]."""
    if not isinstance(strength, (int, float)):
        raise ValueError("strength must be a number")
    if isinstance(strength, bool):
        raise ValueError("strength must be a number, not bool")
    if math.isnan(strength) or math.isinf(strength):
        raise ValueError("strength must be finite")
    if strength < 0.0 or strength > 1.0:
        raise ValueError("strength must be in [0, 1]")
    return float(strength)


def _validate_cutoff_position(pos, num_tokens):
    """Validate cutoff position is an integer in [0, num_tokens]."""
    if not isinstance(pos, int):
        raise ValueError("cutoff_position must be an integer")
    if isinstance(pos, bool):
        raise ValueError("cutoff_position must be an integer, not bool")
    if pos < 0 or pos > num_tokens:
        raise ValueError(
            "cutoff_position must be in [0, %d] for %d tokens" % (num_tokens, num_tokens)
        )
    return pos


def _find_cutoff_index(tokens, cutoff_token):
    """Find the index of the first occurrence of cutoff_token in tokens.

    Returns the index (0-based) or -1 if not found.
    """
    if not isinstance(tokens, (list, tuple)):
        raise ValueError("tokens must be a list or tuple of strings")
    if not isinstance(cutoff_token, str):
        raise ValueError("cutoff_token must be a string")
    for i, tok in enumerate(tokens):
        if not isinstance(tok, str):
            raise ValueError("all tokens must be strings, got %r at index %d" % (type(tok), i))
        if tok == cutoff_token:
            return i
    return -1


def _apply_cutoff(tokens, magnitudes, cutoff_token, cutoff_position, strength):
    """Apply the attribute cutoff logic.

    Args:
        tokens: list of token strings.
        magnitudes: list of numeric embedding magnitudes (same length as tokens).
        cutoff_token: the token string to find.
        cutoff_position: the position to cut off at (0-based index).
        strength: factor in [0, 1] to scale down magnitudes after cutoff.

    Returns:
        (new_magnitudes, cutoff_index, reason)
    """
    num_tokens = len(tokens)
    if len(magnitudes) != num_tokens:
        raise ValueError(
            "magnitudes length (%d) must match tokens length (%d)" % (len(magnitudes), num_tokens)
        )

    # Validate all magnitudes are finite numbers
    for i, m in enumerate(magnitudes):
        if not isinstance(m, (int, float)):
            raise ValueError("magnitudes[%d] must be a number, got %r" % (i, type(m)))
        if isinstance(m, bool):
            raise ValueError("magnitudes[%d] must be a number, not bool" % i)
        if math.isnan(m) or math.isinf(m):
            raise ValueError("magnitudes[%d] must be finite" % i)

    strength = _validate_strength(strength)
    cutoff_position = _validate_cutoff_position(cutoff_position, num_tokens)

    # Find the cutoff token index
    found_index = _find_cutoff_index(tokens, cutoff_token)

    # Determine the effective cutoff index
    if found_index >= 0:
        # Use the found token position, but clamp to cutoff_position if specified
        # The spec says: "Identifies the token corresponding to cutoff_token in the
        # conditioning sequence. Reduces the magnitude of the embeddings for all
        # tokens after this position by the strength factor."
        # cutoff_position is the position to cut off at. We use the found index
        # as the cutoff point. If cutoff_position is provided and differs, we
        # use the found index (since the spec says to identify the token).
        # However, the input also has cutoff_position as an INT. Let's interpret:
        # cutoff_position is the index at which to start cutting. The token is
        # used to find that position. If the token is found, use its index.
        # If not found, use cutoff_position directly.
        effective_cutoff = found_index
        reason = "cutoff token '%s' found at index %d" % (cutoff_token, found_index)
    else:
        # Token not found; use the provided cutoff_position
        effective_cutoff = cutoff_position
        reason = "cutoff token '%s' not found; using cutoff_position %d" % (cutoff_token, cutoff_position)

    # Scale down magnitudes after the effective cutoff index
    new_magnitudes = list(magnitudes)
    for i in range(effective_cutoff + 1, num_tokens):
        new_magnitudes[i] = magnitudes[i] * (1.0 - strength)

    return new_magnitudes, effective_cutoff, reason


class PSN_Prompt_Attribute_Cutoff:
    """Limit the effect of specific prompt attributes by scaling down embedding
    magnitudes after a cutoff token position.

    Pure-logic implementation: operates on token strings and numeric magnitudes.
    No torch, no ComfyUI, no GPU.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tokens": ("STRING", {"default": "a red car with blue wheels", "multiline": False}),
                "magnitudes": ("STRING", {"default": "1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0", "multiline": False}),
                "cutoff_token": ("STRING", {"default": "red", "multiline": False}),
                "cutoff_position": ("INT", {"default": 1, "min": 0, "max": 1024, "step": 1}),
                "strength": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("new_magnitudes", "cutoff_index", "reason")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, tokens, magnitudes, cutoff_token, cutoff_position, strength):
        """Run the attribute cutoff logic.

        Args:
            tokens: comma-separated string of token strings.
            magnitudes: comma-separated string of numeric magnitudes.
            cutoff_token: the token to find for cutoff.
            cutoff_position: fallback position if token not found.
            strength: factor in [0, 1] to scale down post-cutoff magnitudes.

        Returns:
            (new_magnitudes_str, cutoff_index, reason)
        """
        # Parse tokens
        token_list = [t.strip() for t in tokens.split(",") if t.strip() != ""]
        # Parse magnitudes
        mag_list = []
        for m in magnitudes.split(","):
            m = m.strip()
            if m == "":
                continue
            mag_list.append(float(m))

        new_mags, cutoff_idx, reason = _apply_cutoff(
            token_list, mag_list, cutoff_token, cutoff_position, strength
        )

        new_mags_str = ", ".join(str(m) for m in new_mags)
        return (new_mags_str, cutoff_idx, reason)


NODE_CLASS_MAPPINGS = {
    "PSN_Prompt_Attribute_Cutoff": PSN_Prompt_Attribute_Cutoff,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Prompt_Attribute_Cutoff": "Prompt Attribute Cutoff",
}
