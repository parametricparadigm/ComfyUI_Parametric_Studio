"""ParametricStudio - Lyric-Driven Prompt Travel.

Core logic (pure Python + torch on CPU):
  * Split lyrics into phrases and map each phrase to a time interval.
  * Build a prompt schedule (list of (start, end, prompt) tuples) from
    phrase boundaries and a frame rate.
  * Render the schedule as a compact string.

NOT implemented (requires heavy models / unavailable libraries):
  * Actual audio transcription with Whisper (the `whisper` package and
    model weights are not available in this environment).  The node
    therefore accepts a pre-transcribed `lyrics` string instead of an
    AUDIO tensor.  A thin `PSN_Lyric_Prompt_Scheduler` node is provided
    that takes `lyrics` directly; the `audio` / `whisper_model` inputs
    from the original spec are documented but not wired to a real
    transcriber.
"""

import re
import torch

CAT = "ParametricStudio/LyricTravel"


def _split_phrases(text):
    """Split *text* into non-empty phrase strings.

    A phrase ends at sentence punctuation (``.!?``) or a newline.  If
    the text contains no such boundaries the whole (stripped) text is
    returned as a single phrase.  Empty / whitespace-only input yields
    an empty list.
    """
    if text is None:
        return []
    text = str(text).strip()
    if not text:
        return []
    # Split on sentence-ending punctuation or newlines, keeping the
    # delimiter attached to the preceding phrase.
    parts = re.split(r"(?<=[.!?\n])\s*", text)
    phrases = [p.strip() for p in parts if p.strip()]
    return phrases


def _build_schedule(phrases, total_duration, frame_rate, prompt_template):
    """Map *phrases* to equal-length time intervals over *total_duration*.

    Returns a list of dicts::

        {"start": float, "end": float, "phrase": str, "prompt": str}

    ``start`` / ``end`` are in seconds.  The last interval is clamped so
    that ``end == total_duration``.  If *phrases* is empty a single
    interval covering the whole duration with an empty prompt is
    returned (so downstream nodes always get at least one entry).
    """
    if frame_rate is None or frame_rate <= 0:
        raise ValueError("frame_rate must be a positive integer")
    if total_duration is None or total_duration <= 0:
        raise ValueError("total_duration must be positive")

    if not phrases:
        return [{
            "start": 0.0,
            "end": float(total_duration),
            "phrase": "",
            "prompt": _render_prompt(prompt_template, ""),
        }]

    n = len(phrases)
    seg = total_duration / n
    schedule = []
    for i, phrase in enumerate(phrases):
        start = i * seg
        end = total_duration if i == n - 1 else (i + 1) * seg
        schedule.append({
            "start": round(start, 6),
            "end": round(end, 6),
            "phrase": phrase,
            "prompt": _render_prompt(prompt_template, phrase),
        })
    return schedule


def _render_prompt(template, phrase):
    """Fill *template* with *phrase*.

    Supports ``{lyric}`` / ``{phrase}`` placeholders.  If the template
    has no placeholder the phrase is appended after a space (or used as
   -is when the template is empty).
    """
    if template is None:
        template = ""
    template = str(template)
    if "{lyric}" in template or "{phrase}" in template:
        return template.replace("{lyric}", phrase).replace("{phrase}", phrase)
    if not template:
        return phrase
    if not phrase:
        return template
    return template + " " + phrase


def _schedule_to_string(schedule):
    """Render *schedule* as a compact, human-readable string.

    Format (one line per interval)::

        [0.000-2.500] a video of hello
        [2.500-5.000] a video of world
    """
    lines = []
    for entry in schedule:
        lines.append(
            "[{:.3f}-{:.3f}] {}".format(entry["start"], entry["end"], entry["prompt"])
        )
    return "\n".join(lines)


def _validate_audio(audio):
    """Accept a torch tensor (any shape, float) or None.

    Returns a normalised 1-D float tensor (CPU) or ``None``.  The
    tensor is **not** modified in place.
    """
    if audio is None:
        return None
    if not torch.is_tensor(audio):
        raise TypeError("audio must be a torch tensor or None")
    t = audio.detach().float().cpu().reshape(-1)
    if t.numel() == 0:
        raise ValueError("audio tensor must not be empty")
    return t


class PSN_Lyric_Prompt_Scheduler:
    """Convert lyrics into a prompt-travel schedule.

    Splits *lyrics* into phrases, maps each phrase to an equal time
    interval over *total_duration* seconds, and renders a prompt for
    every interval using *prompt_template*.

    NOTE: real Whisper transcription is NOT implemented (the ``whisper``
    package is unavailable).  Pass a pre-transcribed *lyrics* string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lyrics": ("STRING", {"default": "", "multiline": True}),
                "total_duration": ("FLOAT", {"default": 10.0, "min": 0.1, "max": 3600.0}),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 240}),
                "prompt_template": ("STRING", {"default": "a video of {lyric}"}),
            },
            "optional": {
                # Accepted for interface compatibility with the original
                # spec; the tensor is validated but not used for
                # transcription (Whisper is not available).
                "audio": ("AUDIO",),
                "whisper_model": ("STRING", {"default": "tiny"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt_schedule", "lyrics")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, lyrics, total_duration, frame_rate, prompt_template,
            audio=None, whisper_model="tiny"):
        # Validate optional audio (no transcription performed).
        _validate_audio(audio)

        phrases = _split_phrases(lyrics)
        schedule = _build_schedule(phrases, total_duration, frame_rate, prompt_template)
        schedule_str = _schedule_to_string(schedule)
        return (schedule_str, str(lyrics).strip() if lyrics is not None else "")


NODE_CLASS_MAPPINGS = {
    "PSN_Lyric_Prompt_Scheduler": PSN_Lyric_Prompt_Scheduler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Lyric_Prompt_Scheduler": "Lyric Prompt Scheduler (ParametricStudio)",
}
