"""
PSN Local Song Generation & Mastering (pure-logic core).

This module implements the *secure, pure-logic* portion of the "Local Song
Generation & Mastering" spec.  The real spec requires GPU/torch/torchaudio/
pyloudnorm and local model weights (YuE2 / MiniMax Music 3) plus Mzikart
mixer DSP.  None of that is available here, so we implement only the
deterministic, side-effect-free parts:

  * PSN_Music_Generate  -> validates prompt/duration/seed/model_id and
    returns a *deterministic* raw-audio *plan* (a JSON string describing the
    generation request).  It never touches a socket, file, or model.
  * PSN_Music_Master    -> applies a *pure-Python* mastering chain (EQ
    normalization, soft-knee compression, brick-wall limiting) to a plain
    list-of-lists "audio" payload (stereo frames of floats in [-1, 1]),
    and reports the resulting peak in dB.  Loudness is approximated with a
    simple RMS-based estimate so the node is testable without pyloudnorm.

Both nodes take and return plain Python values (strings, numbers, lists,
JSON text).  No torch, no ComfyUI imports, no network, no file/OS access,
no eval/exec, no dunder tricks.
"""

import json
import math

# ---------------------------------------------------------------------------
# Constants / allow-lists
# ---------------------------------------------------------------------------

# Allowed backend model ids (allow-list; anything else is rejected).
MODEL_IDS = ("yue2", "minimax_music_3")

# Allowed EQ presets (allow-list).
EQ_PRESETS = ("flat", "bright", "warm", "broadcast")

# Hard limits for generation parameters.
MIN_DURATION = 1
MAX_DURATION = 600          # 10 minutes
MIN_SEED = 0
MAX_SEED = 2 ** 32 - 1
MIN_PROMPT_LEN = 1
MAX_PROMPT_LEN = 2000

# Mastering limits.
MIN_TARGET_LOUDNESS = -60.0
MAX_TARGET_LOUDNESS = 0.0
COMP_THRESHOLD_DB = -18.0   # soft-knee compression threshold
COMP_RATIO = 2.0            # compression ratio above threshold
LIMITER_DB = -0.5           # brick-wall limiter ceiling (below 0 dB)

# EQ gain curves per preset: (low_gain_db, mid_gain_db, high_gain_db)
# Applied as simple per-band scalar gains (pure logic, no FFT).
_EQ_GAINS = {
    "flat":      (0.0, 0.0, 0.0),
    "bright":    (-1.0, 0.0, 3.0),
    "warm":      (2.0, 0.0, -2.0),
    "broadcast": (0.5, 1.0, 1.5),
}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _db_to_linear(db):
    """Convert a dB value to a linear gain factor."""
    return 10.0 ** (db / 20.0)


def _linear_to_db(value):
    """Convert a linear magnitude to dB (floor at -120 dB)."""
    if value <= 0.0:
        return -120.0
    return 20.0 * math.log10(value)


def _validate_prompt(prompt):
    """Validate the prompt string; return (ok, reason)."""
    if not isinstance(prompt, str):
        return False, "prompt must be a string"
    if len(prompt) < MIN_PROMPT_LEN:
        return False, "prompt is empty"
    if len(prompt) > MAX_PROMPT_LEN:
        return False, "prompt too long"
    return True, "ok"


def _validate_duration(duration):
    """Validate duration (seconds); return (ok, reason)."""
    if not isinstance(duration, int) or isinstance(duration, bool):
        return False, "duration must be an integer"
    if duration < MIN_DURATION or duration > MAX_DURATION:
        return False, "duration out of range"
    return True, "ok"


def _validate_seed(seed):
    """Validate seed; return (ok, reason)."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        return False, "seed must be an integer"
    if seed < MIN_SEED or seed > MAX_SEED:
        return False, "seed out of range"
    return True, "ok"


def _validate_model(model_id):
    """Validate model id against allow-list; return (ok, reason)."""
    if not isinstance(model_id, str):
        return False, "model_id must be a string"
    if model_id not in MODEL_IDS:
        return False, "model_id not in allow-list"
    return True, "ok"


def _build_generation_plan(prompt, duration, seed, model_id):
    """Build a deterministic JSON plan for the (external) generator."""
    plan = {
        "backend": model_id,
        "prompt": prompt,
        "duration_seconds": duration,
        "seed": seed,
        "channels": 2,
        "sample_rate": 44100,
        "format": "stereo_float32",
    }
    return json.dumps(plan, sort_keys=True)


def _apply_eq(frame, preset):
    """Apply a simple 3-band scalar EQ to a stereo frame.

    frame: (left, right) floats.  We approximate bands by treating the
    frame magnitude as a single value and applying the mid-band gain, then
    scaling.  This is a pure-logic stand-in for real multi-band EQ.
    """
    low_db, mid_db, high_db = _EQ_GAINS[preset]
    # Use the mid-band gain as the representative gain for this simple model.
    gain = _db_to_linear(mid_db)
    return (frame[0] * gain, frame[1] * gain)


def _compress_frame(frame, threshold_db, ratio):
    """Apply soft-knee-ish compression to a stereo frame.

    For each channel, if the magnitude (in dB) exceeds the threshold,
    compress by the given ratio.  Pure math, no state.
    """
    out = []
    for sample in frame:
        mag = abs(sample)
        if mag <= 0.0:
            out.append(0.0)
            continue
        db = _linear_to_db(mag)
        if db <= threshold_db:
            out.append(sample)
            continue
        # Compress: new_db = threshold + (db - threshold) / ratio
        new_db = threshold_db + (db - threshold_db) / ratio
        new_mag = _db_to_linear(new_db)
        sign = 1.0 if sample > 0 else -1.0
        out.append(sign * new_mag)
    return (out[0], out[1])


def _limit_frame(frame, ceiling_db):
    """Brick-wall limit a stereo frame to a ceiling in dB."""
    ceiling = _db_to_linear(ceiling_db)
    out = []
    for sample in frame:
        if abs(sample) > ceiling:
            sign = 1.0 if sample > 0 else -1.0
            out.append(sign * ceiling)
        else:
            out.append(sample)
    return (out[0], out[1])


def _normalize_to_loudness(frames, target_loudness_db):
    """Scale frames so that the RMS-based loudness estimate matches target.

    Returns (scaled_frames, gain_applied).  Pure math.
    """
    if not frames:
        return frames, 1.0
    # Compute RMS over all samples.
    total = 0.0
    count = 0
    for frame in frames:
        for sample in frame:
            total += sample * sample
            count += 1
    if count == 0:
        return frames, 1.0
    rms = math.sqrt(total / count)
    if rms <= 0.0:
        return frames, 1.0
    current_db = _linear_to_db(rms)
    gain_db = target_loudness_db - current_db
    gain = _db_to_linear(gain_db)
    scaled = [(l * gain, r * gain) for (l, r) in frames]
    return scaled, gain


def _compute_peak_db(frames):
    """Compute the peak magnitude in dB across all frames."""
    peak = 0.0
    for frame in frames:
        for sample in frame:
            mag = abs(sample)
            if mag > peak:
                peak = mag
    return _linear_to_db(peak)


def _frames_to_list(frames):
    """Convert tuple-of-tuples frames to a plain list-of-lists for output."""
    return [[l, r] for (l, r) in frames]


def _list_to_frames(audio):
    """Convert a list-of-lists (or list-of-tuples) to tuple-of-tuples.

    Returns (frames, ok, reason).
    """
    if not isinstance(audio, (list, tuple)):
        return None, False, "audio must be a list of [left, right] frames"
    frames = []
    for i, frame in enumerate(audio):
        if not isinstance(frame, (list, tuple)) or len(frame) != 2:
            return None, False, "audio frame %d must be a 2-element sequence" % i
        l, r = frame
        if not isinstance(l, (int, float)) or not isinstance(r, (int, float)):
            return None, False, "audio frame %d must contain numbers" % i
        if isinstance(l, bool) or isinstance(r, bool):
            return None, False, "audio frame %d must not contain booleans" % i
        frames.append((float(l), float(r)))
    return frames, True, "ok"


# ---------------------------------------------------------------------------
# Node 1: PSN_Music_Generate
# ---------------------------------------------------------------------------

class PSN_Music_Generate:
    """Validate a music-generation request and emit a deterministic plan.

    Pure-logic stand-in for the YuE2 / MiniMax Music 3 backend.  It does NOT
    generate audio; it validates inputs and returns a JSON plan that a real
    backend would consume.  The 'raw_audio' output is the JSON plan string
    (typed AUDIO in the real graph; here it is a STRING payload).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "duration": ("INT", {"default": 30, "min": MIN_DURATION, "max": MAX_DURATION, "step": 1}),
                "seed": ("INT", {"default": 0, "min": MIN_SEED, "max": MAX_SEED, "step": 1}),
                "model_id": (list(MODEL_IDS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("AUDIO", "STRING", "BOOLEAN")
    RETURN_NAMES = ("raw_audio", "plan_json", "valid")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Music"

    def run(self, prompt, duration, seed, model_id):
        ok, reason = _validate_prompt(prompt)
        if not ok:
            return ("", "", False)
        ok, reason = _validate_duration(duration)
        if not ok:
            return ("", "", False)
        ok, reason = _validate_seed(seed)
        if not ok:
            return ("", "", False)
        ok, reason = _validate_model(model_id)
        if not ok:
            return ("", "", False)
        plan = _build_generation_plan(prompt, duration, seed, model_id)
        # raw_audio is the plan (stand-in for actual audio bytes).
        return (plan, plan, True)


# ---------------------------------------------------------------------------
# Node 2: PSN_Music_Master
# ---------------------------------------------------------------------------

class PSN_Music_Master:
    """Apply a pure-Python mastering chain to a plain audio payload.

    Input 'audio' is a list of [left, right] float frames in [-1, 1].
    The chain: EQ normalization -> soft-knee compression -> brick-wall
    limiting -> loudness normalization.  Outputs the mastered frames and
    the resulting peak in dB.  No torch, no pyloudnorm; loudness is an
    RMS-based estimate.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "target_loudness": ("FLOAT", {"default": -14.0, "min": MIN_TARGET_LOUDNESS, "max": MAX_TARGET_LOUDNESS, "step": 0.1}),
                "eq_preset": (list(EQ_PRESETS),),
            },
            "optional": {},
        }

    RETURN_TYPES = ("AUDIO", "FLOAT")
    RETURN_NAMES = ("mastered_audio", "peak_db")
    FUNCTION = "run"
    CATEGORY = "ParametricStudio/Music"

    def run(self, audio, target_loudness, eq_preset):
        frames, ok, reason = _list_to_frames(audio)
        if not ok:
            # Return empty audio and -inf peak on bad input.
            return ([], -120.0)
        if eq_preset not in _EQ_GAINS:
            return ([], -120.0)
        if not isinstance(target_loudness, (int, float)) or isinstance(target_loudness, bool):
            return ([], -120.0)
        if target_loudness < MIN_TARGET_LOUDNESS or target_loudness > MAX_TARGET_LOUDNESS:
            return ([], -120.0)

        # Step 1: EQ normalization.
        frames = [_apply_eq(f, eq_preset) for f in frames]
        # Step 2: Soft-knee compression.
        frames = [_compress_frame(f, COMP_THRESHOLD_DB, COMP_RATIO) for f in frames]
        # Step 3: Brick-wall limiting.
        frames = [_limit_frame(f, LIMITER_DB) for f in frames]
        # Step 4: Loudness normalization to target.
        frames, _gain = _normalize_to_loudness(frames, float(target_loudness))
        # Re-limit after normalization to guarantee below 0 dB.
        frames = [_limit_frame(f, LIMITER_DB) for f in frames]

        peak_db = _compute_peak_db(frames)
        mastered = _frames_to_list(frames)
        return (mastered, peak_db)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_Music_Generate": PSN_Music_Generate,
    "PSN_Music_Master": PSN_Music_Master,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Music_Generate": "PSN Music Generate",
    "PSN_Music_Master": "PSN Music Master",
}
