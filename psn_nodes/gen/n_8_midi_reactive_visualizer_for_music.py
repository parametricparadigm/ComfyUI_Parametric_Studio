"""PSN_MIDI_Visualizer: pure-logic MIDI note-event parsing and reactive visual-frame
generation.

This module implements ONLY the secure, pure-logic portion of the spec. It does NOT
open sockets, read files, touch the OS, or import torch/numpy/mido. Instead it accepts
`midi_data` as a STRING containing either:
  * a JSON array of note events, e.g.
      [{"time": 0.0, "note": 60, "velocity": 100, "type": "on"}, ...]
    where `time` is seconds, `note` is a MIDI note number (0-127), `velocity` is 0-127,
    and `type` is "on" or "off"; or
  * a compact pipe-delimited text form, e.g.
      0.0|60|100|on;0.125|60|0|off;0.25|64|127|on
    (fields: time|note|velocity|type, events separated by ';').

It parses/validates those events, computes per-frame reactivity (note activity,
velocity energy, pitch range) and emits a JSON "video" payload describing the frames
for the requested visual_style ("bars", "particles", "waveform"). The payload is plain
data (a JSON string) that a downstream GPU/video node could consume; no video bytes are
produced here. All inputs are plain values (strings, floats) and all outputs are plain
values (a JSON string plus a status string), so the node is safe-by-design.
"""

import json
import math

CAT = "ParametricStudio/Music"

_STYLES = ("bars", "particles", "waveform")
_TYPES = ("on", "off")
_MIN_NOTE = 0
_MAX_NOTE = 127
_MIN_VEL = 0
_MAX_VEL = 127
_MAX_EVENTS = 100000
_MAX_TIME = 1e6
_MAX_FRAMES = 100000
_MIN_FPS = 1.0
_MAX_FPS = 240.0
_MIN_SENS = 0.0
_MAX_SENS = 100.0


def _clamp(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _parse_events(text):
    """Parse `text` into a list of (time, note, velocity, type) tuples.

    Returns (events, error). On success error is None and events is a list.
    On failure events is None and error is a human-readable string.
    """
    if not isinstance(text, str):
        return None, "midi_data must be a string"
    stripped = text.strip()
    if not stripped:
        return None, "midi_data is empty"

    events = []
    if stripped[0] == "[":
        try:
            data = json.loads(stripped)
        except Exception as exc:
            return None, "invalid JSON: %s" % exc
        if not isinstance(data, list):
            return None, "JSON must be an array of note events"
        if len(data) > _MAX_EVENTS:
            return None, "too many events (max %d)" % _MAX_EVENTS
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                return None, "event %d is not an object" % idx
            try:
                time_val = float(item.get("time", 0.0))
                note_val = int(item.get("note", 0))
                vel_val = int(item.get("velocity", 0))
                type_val = str(item.get("type", "on")).lower()
            except (TypeError, ValueError):
                return None, "event %d has non-numeric fields" % idx
            if not math.isfinite(time_val) or time_val < 0.0 or time_val > _MAX_TIME:
                return None, "event %d has invalid time" % idx
            if note_val < _MIN_NOTE or note_val > _MAX_NOTE:
                return None, "event %d has note out of range 0-127" % idx
            if vel_val < _MIN_VEL or vel_val > _MAX_VEL:
                return None, "event %d has velocity out of range 0-127" % idx
            if type_val not in _TYPES:
                return None, "event %d has invalid type (use on/off)" % idx
            events.append((time_val, note_val, vel_val, type_val))
    else:
        for idx, chunk in enumerate(stripped.split(";")):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = chunk.split("|")
            if len(parts) != 4:
                return None, "event %d must have 4 fields (time|note|velocity|type)" % idx
            try:
                time_val = float(parts[0])
                note_val = int(parts[1])
                vel_val = int(parts[2])
                type_val = parts[3].strip().lower()
            except (TypeError, ValueError):
                return None, "event %d has non-numeric fields" % idx
            if not math.isfinite(time_val) or time_val < 0.0 or time_val > _MAX_TIME:
                return None, "event %d has invalid time" % idx
            if note_val < _MIN_NOTE or note_val > _MAX_NOTE:
                return None, "event %d has note out of range 0-127" % idx
            if vel_val < _MIN_VEL or vel_val > _MAX_VEL:
                return None, "event %d has velocity out of range 0-127" % idx
            if type_val not in _TYPES:
                return None, "event %d has invalid type (use on/off)" % idx
            events.append((time_val, note_val, vel_val, type_val))
            if len(events) > _MAX_EVENTS:
                return None, "too many events (max %d)" % _MAX_EVENTS
    if not events:
        return None, "no valid note events found"
    events.sort(key=lambda e: e[0])
    return events, None


def _frame_metrics(events, frame_time, frame_index, frame_count):
    """Compute reactivity metrics for a single frame.

    Returns a dict with:
      activity   : number of "on" events in this frame window (0..N)
      energy     : sum of velocities of "on" events in this frame window (0..127*N)
      pitch_low  : lowest active note in the window (or None)
      pitch_high : highest active note in the window (or None)
      pitch_span : pitch_high - pitch_low (0 if none)
    """
    if frame_count <= 1:
        window_start = 0.0
        window_end = _MAX_TIME
    else:
        total_time = events[-1][0]
        if total_time <= 0.0:
            window_start = 0.0
            window_end = 0.0
        else:
            window_start = (total_time / frame_count) * frame_index
            window_end = (total_time / frame_count) * (frame_index + 1)
    activity = 0
    energy = 0
    pitch_low = None
    pitch_high = None
    for (time_val, note_val, vel_val, type_val) in events:
        if time_val < window_start:
            continue
        if time_val > window_end:
            break
        if type_val == "on":
            activity += 1
            energy += vel_val
            if pitch_low is None or note_val < pitch_low:
                pitch_low = note_val
            if pitch_high is None or note_val > pitch_high:
                pitch_high = note_val
    pitch_span = 0
    if pitch_low is not None and pitch_high is not None:
        pitch_span = pitch_high - pitch_low
    return {
        "activity": activity,
        "energy": energy,
        "pitch_low": pitch_low,
        "pitch_high": pitch_high,
        "pitch_span": pitch_span,
    }


def _build_frames(events, style, sensitivity, fps, duration):
    """Build the list of frame descriptors for the requested style."""
    if duration <= 0.0:
        duration = events[-1][0] if events else 0.0
    if duration <= 0.0:
        duration = 1.0
    frame_count = int(math.ceil(duration * fps))
    if frame_count < 1:
        frame_count = 1
    if frame_count > _MAX_FRAMES:
        frame_count = _MAX_FRAMES
    frames = []
    for frame_index in range(frame_count):
        frame_time = (frame_count <= 1) and 0.0 or (duration / frame_count) * frame_index
        metrics = _frame_metrics(events, frame_time, frame_index, frame_count)
        activity = metrics["activity"]
        energy = metrics["energy"]
        pitch_span = metrics["pitch_span"]
        # Normalize to 0..1-ish then scale by sensitivity.
        activity_norm = min(1.0, activity / 8.0)
        energy_norm = min(1.0, energy / (127.0 * 8.0))
        span_norm = min(1.0, pitch_span / 127.0)
        reactivity = (0.5 * activity_norm + 0.35 * energy_norm + 0.15 * span_norm) * sensitivity
        reactivity = _clamp(reactivity, 0.0, 10.0)
        frame = {
            "index": frame_index,
            "time": round(frame_time, 6),
            "activity": activity,
            "energy": energy,
            "pitch_low": metrics["pitch_low"],
            "pitch_high": metrics["pitch_high"],
            "pitch_span": pitch_span,
            "reactivity": round(reactivity, 6),
        }
        if style == "bars":
            bar_count = max(1, min(64, 1 + int(reactivity * 16)))
            frame["bars"] = [round(reactivity * (0.5 + 0.5 * math.sin(math.pi * i / max(1, bar_count - 1))), 6) for i in range(bar_count)]
        elif style == "particles":
            particle_count = max(0, min(256, int(reactivity * 64)))
            frame["particles"] = [
                {
                    "x": round((i * 0.6180339887) % 1.0, 6),
                    "y": round((i * 0.3819660113) % 1.0, 6),
                    "size": round(0.5 + reactivity * 0.5, 6),
                }
                for i in range(particle_count)
            ]
        else:
            sample_count = max(2, min(512, 32 + int(reactivity * 64)))
            frame["waveform"] = [
                round(0.5 + 0.5 * math.sin(2.0 * math.pi * (i / max(1, sample_count - 1)) + reactivity), 6)
                for i in range(sample_count)
            ]
        frames.append(frame)
    return frames, frame_count, duration


class PSN_MIDI_Visualizer:
    """Parse MIDI note events (as JSON or pipe-delimited text) and emit a JSON video
    payload whose frames react to note activity, velocity energy, and pitch span.

    Pure-logic only: no file, network, GPU, or OS access. `midi_data` is a string of
    note events; the output `video` is a JSON string describing frames for the chosen
    visual style. `status` reports success or a validation error.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "midi_data": ("STRING", {"default": "0.0|60|100|on;0.125|60|0|off", "multiline": True}),
                "visual_style": (list(_STYLES),),
                "sensitivity": ("FLOAT", {"default": 1.0, "min": _MIN_SENS, "max": _MAX_SENS, "step": 0.01}),
            },
            "optional": {
                "fps": ("FLOAT", {"default": 30.0, "min": _MIN_FPS, "max": _MAX_FPS, "step": 1.0}),
                "duration": ("FLOAT", {"default": 0.0, "min": 0.0, "max": _MAX_TIME, "step": 0.1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, midi_data, visual_style, sensitivity, fps=30.0, duration=0.0):
        if visual_style not in _STYLES:
            return (json.dumps({"error": "invalid visual_style"}), "error: invalid visual_style")
        if not isinstance(sensitivity, (int, float)) or not math.isfinite(float(sensitivity)):
            return (json.dumps({"error": "invalid sensitivity"}), "error: invalid sensitivity")
        sensitivity = _clamp(float(sensitivity), _MIN_SENS, _MAX_SENS)
        if not isinstance(fps, (int, float)) or not math.isfinite(float(fps)):
            return (json.dumps({"error": "invalid fps"}), "error: invalid fps")
        fps = _clamp(float(fps), _MIN_FPS, _MAX_FPS)
        if not isinstance(duration, (int, float)) or not math.isfinite(float(duration)):
            return (json.dumps({"error": "invalid duration"}), "error: invalid duration")
        duration = _clamp(float(duration), 0.0, _MAX_TIME)

        events, error = _parse_events(midi_data)
        if error is not None:
            return (json.dumps({"error": error}), "error: %s" % error)

        frames, frame_count, used_duration = _build_frames(events, visual_style, sensitivity, fps, duration)
        payload = {
            "style": visual_style,
            "fps": fps,
            "duration": round(used_duration, 6),
            "frame_count": frame_count,
            "event_count": len(events),
            "sensitivity": sensitivity,
            "frames": frames,
        }
        return (json.dumps(payload), "ok: %d frames from %d events" % (frame_count, len(events)))


NODE_CLASS_MAPPINGS = {
    "PSN_MIDI_Visualizer": PSN_MIDI_Visualizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_MIDI_Visualizer": "MIDI Reactive Visualizer (Music)",
}
