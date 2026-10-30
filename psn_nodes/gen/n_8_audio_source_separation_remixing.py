"""
PSN Audio Source Separation & Remixing (pure-logic core).

This module implements the *pure-logic, secure-by-design* portion of the
"Audio Source Separation & Remixing" spec. The actual neural source
separation (Demucs / MDX) and any real audio I/O require torch, demucs,
GPU memory and file access, which are intentionally NOT used here.

What IS implemented (standard library only, no torch / comfy / network /
file / subprocess / eval):

  * PSN_Sep_Split  -- validates the separation request (model allow-list,
                      audio payload shape) and returns the *planned* stem
                      layout (names, order, per-stem gain defaults) plus a
                      status/reason string. It does NOT run a model.
  * PSN_Sep_Mix    -- performs the actual gain-mixing math on plain numeric
                      sample lists: applies per-stem gain, sums the stems,
                      and reports clipping / peak information.

Both nodes take and return plain values (numbers, strings, lists of
numbers, JSON text) so they can be unit-tested without any audio backend.
"""

import json

# ---------------------------------------------------------------------------
# Constants / allow-lists
# ---------------------------------------------------------------------------

# Allowed separation back-ends (mirrors the spec's COMBO choices).
SPLIT_MODELS = ("htdemucs", "mdx")

# Canonical stem order produced by a 4-stem separation.
STEM_NAMES = ("vocals", "drums", "bass", "other")

# Default per-stem gain used when a mix request omits gains.
DEFAULT_GAIN = 1.0

# Hard ceiling on per-stem gain to keep the pure-logic math well behaved.
MAX_GAIN = 1e6

# Hard floor on per-stem gain (0 mutes a stem).
MIN_GAIN = 0.0

# Maximum number of stems we will mix in one call.
MAX_STEMS = 16

# Maximum number of samples per stem we will process in one call.
MAX_SAMPLES = 10_000_000

# A tiny epsilon used for "non-zero" style checks.
_EPS = 1e-12


# ---------------------------------------------------------------------------
# Pure-logic helpers
# ---------------------------------------------------------------------------

def _is_number(value):
    """Return True if value is a real number (int/float) but not bool."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _coerce_sample_list(value, name):
    """
    Coerce a plain value into a list of floats representing audio samples.

    Accepts:
      * a list/tuple of numbers
      * a JSON text string that decodes to a list of numbers
    Raises ValueError with a clear message otherwise.
    """
    if value is None:
        raise ValueError(f"{name} must not be null")

    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{name} is not valid JSON: {exc}")
        value = decoded

    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list of numbers or JSON text, got {type(value).__name__}")

    if len(value) > MAX_SAMPLES:
        raise ValueError(f"{name} has too many samples ({len(value)} > {MAX_SAMPLES})")

    out = []
    for i, s in enumerate(value):
        if not _is_number(s):
            raise ValueError(f"{name}[{i}] is not a number: {type(s).__name__}")
        out.append(float(s))
    return out


def _coerce_gain_list(value, expected_len, name="gains"):
    """
    Coerce gains into a list of floats of length expected_len.

    Accepts a single number (applied to every stem) or a list/tuple of
    numbers of the right length. Raises ValueError otherwise.
    """
    if value is None:
        # Default: all ones.
        return [DEFAULT_GAIN] * expected_len

    # If it's a string, try to parse as JSON first.
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            # If JSON parsing fails, maybe it's just a number string?
            # But json.loads("0.5") works. If it fails, it's invalid.
            raise ValueError(f"{name} is not valid JSON or number: {value!r}")

    if _is_number(value):
        g = float(value)
        if g < MIN_GAIN or g > MAX_GAIN:
            raise ValueError(f"{name} gain {g} out of range [{MIN_GAIN}, {MAX_GAIN}]")
        return [g] * expected_len

    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a number or list of numbers, got {type(value).__name__}")

    if len(value) != expected_len:
        raise ValueError(f"{name} length {len(value)} does not match stem count {expected_len}")

    out = []
    for i, g in enumerate(value):
        if not _is_number(g):
            raise ValueError(f"{name}[{i}] is not a number: {type(g).__name__}")
        g = float(g)
        if g < MIN_GAIN or g > MAX_GAIN:
            raise ValueError(f"{name}[{i}] gain {g} out of range [{MIN_GAIN}, {MAX_GAIN}]")
        out.append(g)
    return out


def _mix_stems(stem_lists, gains):
    """
    Core gain-mixing math.

    stem_lists: list of lists of floats (one per stem).
    gains:      list of floats, same length as stem_lists.

    Returns (mixed, peak, clipped) where:
      mixed  -- list of floats, the summed result
      peak   -- max absolute value in mixed
      clipped-- bool, True if any sample exceeded 1.0 in magnitude
    """
    n = len(stem_lists[0]) if stem_lists else 0
    mixed = [0.0] * n
    for stem, gain in zip(stem_lists, gains):
        if gain == 0.0:
            continue
        for i in range(n):
            mixed[i] += stem[i] * gain

    peak = 0.0
    clipped = False
    for v in mixed:
        a = abs(v)
        if a > peak:
            peak = a
        if a > 1.0:
            clipped = True
    return mixed, peak, clipped


# ---------------------------------------------------------------------------
# Node 1: PSN_Sep_Split
# ---------------------------------------------------------------------------

class PSN_Sep_Split:
    """
    Validate a source-separation request and return the planned stem layout.

    This node does NOT run a separation model (that requires torch/demucs/GPU).
    It validates the model choice and the audio payload, then emits the
    canonical 4-stem plan (names, order, default gains) plus a status string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("STRING", {"default": "[]", "multiline": True}),
                "model": (list(SPLIT_MODELS), {"default": "htdemucs"}),
            },
            "optional": {
                "sample_rate": ("INT", {"default": 44100, "min": 1, "max": 192000}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("vocals", "drums", "bass", "other", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, audio, model, sample_rate=44100):
        # Validate model against allow-list.
        if model not in SPLIT_MODELS:
            return ("", "", "", "", f"error: model '{model}' not in allow-list {SPLIT_MODELS}")

        # Validate audio payload (plain list of numbers or JSON text).
        try:
            samples = _coerce_sample_list(audio, "audio")
        except ValueError as exc:
            return ("", "", "", "", f"error: {exc}")

        if len(samples) == 0:
            return ("", "", "", "", "error: audio payload is empty")

        if not _is_number(sample_rate) or sample_rate <= 0:
            return ("", "", "", "", f"error: sample_rate must be a positive number, got {sample_rate!r}")

        # Build the planned stem layout. Each stem is represented as a JSON
        # list of zeros (placeholder for the real separated signal) with the
        # same length as the input, so downstream pure-logic nodes can operate
        # on the shape. The real signal would come from the GPU model.
        placeholder = json.dumps([0.0] * len(samples))
        status = (
            f"ok: model={model} samples={len(samples)} sample_rate={int(sample_rate)} "
            f"stems={','.join(STEM_NAMES)} (placeholder zeros; run GPU model for real signal)"
        )
        return (placeholder, placeholder, placeholder, placeholder, status)


# ---------------------------------------------------------------------------
# Node 2: PSN_Sep_Mix
# ---------------------------------------------------------------------------

class PSN_Sep_Mix:
    """
    Mix a list of stems with per-stem gains (pure gain-mixing math).

    Inputs are plain values: a JSON text (or list) of stems, each stem being a
    list of numbers, and a JSON text (or list) of gains. Returns the mixed
    audio as JSON text plus peak and clipping info.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stems": ("STRING", {"default": "[]", "multiline": True}),
                "gains": ("STRING", {"default": "1.0", "multiline": True}),
            },
            "optional": {
                "stem_names": ("STRING", {"default": "vocals,drums,bass,other"}),
            },
        }

    RETURN_TYPES = ("STRING", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("mixed_audio", "peak", "clipped", "status")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Audio"

    def run(self, stems, gains, stem_names="vocals,drums,bass,other"):
        # Parse stems.
        # stems is expected to be a JSON string representing a list of lists.
        if isinstance(stems, str):
            try:
                raw_stems = json.loads(stems)
            except (ValueError, TypeError) as exc:
                return ("", 0.0, False, f"error: stems is not valid JSON: {exc}")
        else:
            raw_stems = stems

        if not isinstance(raw_stems, (list, tuple)):
            return ("", 0.0, False, f"error: stems must be a list, got {type(raw_stems).__name__}")

        if len(raw_stems) == 0:
            return ("", 0.0, False, "error: stems list is empty")

        if len(raw_stems) > MAX_STEMS:
            return ("", 0.0, False, f"error: too many stems ({len(raw_stems)} > {MAX_STEMS})")

        # Coerce each stem to a list of floats.
        stem_lists = []
        for i, s in enumerate(raw_stems):
            try:
                stem_lists.append(_coerce_sample_list(s, f"stems[{i}]"))
            except ValueError as exc:
                return ("", 0.0, False, f"error: {exc}")

        # All stems must have the same length.
        n = len(stem_lists[0])
        for i, s in enumerate(stem_lists):
            if len(s) != n:
                return ("", 0.0, False, f"error: stems[{i}] length {len(s)} != {n}")

        # Parse gains.
        try:
            gain_list = _coerce_gain_list(gains, len(stem_lists))
        except ValueError as exc:
            return ("", 0.0, False, f"error: {exc}")

        # Parse optional stem names (comma separated).
        names = [x.strip() for x in stem_names.split(",") if x.strip()]
        if len(names) != len(stem_lists):
            names = [f"stem{i}" for i in range(len(stem_lists))]

        # Do the mixing.
        mixed, peak, clipped = _mix_stems(stem_lists, gain_list)

        status = (
            f"ok: stems={len(stem_lists)} samples={n} "
            f"gains={json.dumps(gain_list)} peak={peak:.6f} clipped={clipped}"
        )
        return (json.dumps(mixed), peak, clipped, status)


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Sep_Split": PSN_Sep_Split,
    "PSN_Sep_Mix": PSN_Sep_Mix,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Sep_Split": "PSN Sep Split (Source Separation Plan)",
    "PSN_Sep_Mix": "PSN Sep Mix (Stem Gain Mixing)",
}
