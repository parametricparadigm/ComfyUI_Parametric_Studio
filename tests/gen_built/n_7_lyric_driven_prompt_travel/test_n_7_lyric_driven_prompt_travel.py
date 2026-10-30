"""Tests for n_7_lyric_driven_prompt_travel."""

import torch

from n_7_lyric_driven_prompt_travel import (
    PSN_Lyric_Prompt_Scheduler,
    _split_phrases,
    _build_schedule,
    _render_prompt,
    _schedule_to_string,
    _validate_audio,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

node = PSN_Lyric_Prompt_Scheduler()

# 1. Module-level mappings exist and are consistent.
assert "PSN_Lyric_Prompt_Scheduler" in NODE_CLASS_MAPPINGS
assert NODE_CLASS_MAPPINGS["PSN_Lyric_Prompt_Scheduler"] is PSN_Lyric_Prompt_Scheduler
assert "PSN_Lyric_Prompt_Scheduler" in NODE_DISPLAY_NAME_MAPPINGS

# 2. INPUT_TYPES / RETURN_TYPES / FUNCTION / CATEGORY contract.
it = PSN_Lyric_Prompt_Scheduler.INPUT_TYPES()
assert "required" in it and "lyrics" in it["required"]
assert PSN_Lyric_Prompt_Scheduler.RETURN_TYPES == ("STRING", "STRING")
assert PSN_Lyric_Prompt_Scheduler.RETURN_NAMES == ("prompt_schedule", "lyrics")
assert PSN_Lyric_Prompt_Scheduler.FUNCTION == "run"
assert PSN_Lyric_Prompt_Scheduler.CATEGORY.startswith("ParametricStudio/")

# 3. Phrase splitting: multiple sentences.
phrases = _split_phrases("Hello world. How are you? Fine!\nBye.")
assert phrases == ["Hello world.", "How are you?", "Fine!", "Bye."], phrases

# 4. Phrase splitting: no boundaries -> single phrase; empty -> [].
assert _split_phrases("just one phrase") == ["just one phrase"]
assert _split_phrases("") == []
assert _split_phrases(None) == []
assert _split_phrases("   ") == []

# 5. Schedule: 3 phrases over 12 s -> equal 4 s intervals, last clamped.
sched = _build_schedule(["a", "b", "c"], 12.0, 24, "video of {lyric}")
assert len(sched) == 3
assert sched[0]["start"] == 0.0 and sched[0]["end"] == 4.0
assert sched[1]["start"] == 4.0 and sched[1]["end"] == 8.0
assert sched[2]["start"] == 8.0 and sched[2]["end"] == 12.0
assert sched[0]["prompt"] == "video of a"
assert sched[2]["prompt"] == "video of c"

# 6. Schedule: empty phrases -> single full-duration entry.
sched_empty = _build_schedule([], 5.0, 30, "x {lyric}")
assert len(sched_empty) == 1
assert sched_empty[0]["start"] == 0.0 and sched_empty[0]["end"] == 5.0
assert sched_empty[0]["prompt"] == "x "

# 7. Bad inputs raise.
try:
    _build_schedule(["a"], 10.0, 0, "t")
    raise AssertionError("expected ValueError for frame_rate=0")
except ValueError:
    pass
try:
    _build_schedule(["a"], -1.0, 24, "t")
    raise AssertionError("expected ValueError for negative duration")
except ValueError:
    pass

# 8. _render_prompt: no placeholder appends; empty template returns phrase.
assert _render_prompt("", "hi") == "hi"
assert _render_prompt("prefix", "hi") == "prefix hi"
assert _render_prompt("{lyric}!", "hi") == "hi!"
assert _render_prompt("{phrase}!", "hi") == "hi!"

# 9. End-to-end node run with a valid audio tensor (not modified in place).
audio = torch.randn(1, 16000)  # 1 s @ 16 kHz
before = audio.clone()
schedule_str, lyrics_out = node.run(
    lyrics="Sun is up. Birds sing.",
    total_duration=4.0,
    frame_rate=24,
    prompt_template="a video of {lyric}",
    audio=audio,
    whisper_model="tiny",
)
assert torch.equal(audio, before), "audio was modified in place"
assert lyrics_out == "Sun is up. Birds sing."
assert "[0.000-2.000] a video of Sun is up." in schedule_str
assert "[2.000-4.000] a video of Birds sing." in schedule_str

# 10. Edge: empty lyrics -> single empty-prompt interval, no crash.
schedule_str2, lyrics_out2 = node.run(
    lyrics="",
    total_duration=2.0,
    frame_rate=12,
    prompt_template="a video of {lyric}",
)
assert lyrics_out2 == ""
assert "[0.000-2.000] a video of " in schedule_str2

# 11. Bad audio type raises TypeError.
try:
    node.run(lyrics="x", total_duration=1.0, frame_rate=24,
             prompt_template="t", audio="not a tensor")
    raise AssertionError("expected TypeError for non-tensor audio")
except TypeError:
    pass

# 12. Empty audio tensor raises ValueError.
try:
    node.run(lyrics="x", total_duration=1.0, frame_rate=24,
             prompt_template="t", audio=torch.empty(0))
    raise AssertionError("expected ValueError for empty audio")
except ValueError:
    pass

print("ok")
