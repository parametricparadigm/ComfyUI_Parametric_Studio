"""Timeline-based camera direction nodes for ParametricStudio.

Implements a keyframe-based camera path editor and an audio-energy
driven camera parameter mapper.  Pure torch/stdlib: no numpy, no
librosa.  Audio is accepted as a ComfyUI AUDIO dict
{"waveform": [C, T] tensor, "sample_rate": int} and reduced to a
per-frame energy envelope with a small torch DSP (RMS windows).
"""

import json
import math

import torch

CAT = "ParametricStudio/Camera"


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _parse_keyframes(raw):
    """Parse the keyframes JSON string into a sorted list of dicts.

    Each keyframe: {"time": float, "position": [x, y, z], "zoom": float}
    Returns (frames, error).  error is None on success.
    """
    if not isinstance(raw, str):
        return None, "keyframes must be a JSON string"
    try:
        data = json.loads(raw)
    except Exception as e:
        return None, "invalid JSON: %s" % e
    if not isinstance(data, list):
        return None, "keyframes must be a JSON list"
    if len(data) < 1:
        return None, "need at least one keyframe"
    frames = []
    for i, kf in enumerate(data):
        if not isinstance(kf, dict):
            return None, "keyframe %d must be an object" % i
        t = kf.get("time")
        if not isinstance(t, (int, float)) or isinstance(t, bool):
            return None, "keyframe %d: time must be a number" % i
        pos = kf.get("position", [0.0, 0.0, 0.0])
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            return None, "keyframe %d: position must be [x, y, z]" % i
        try:
            pos = [float(p) for p in pos]
        except Exception:
            return None, "keyframe %d: position values must be numbers" % i
        zoom = kf.get("zoom", 1.0)
        if not isinstance(zoom, (int, float)) or isinstance(zoom, bool):
            return None, "keyframe %d: zoom must be a number" % i
        frames.append({"time": float(t), "position": pos, "zoom": float(zoom)})
    frames.sort(key=lambda f: f["time"])
    return frames, None


def _smoothstep(u):
    """Smooth Hermite interpolation on [0, 1] (C1 continuous)."""
    u = _clamp(u, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def _interp_keyframes(frames, duration, steps):
    """Interpolate keyframes into `steps` evenly spaced samples over [0, duration].

    Returns a list of {"time", "position", "zoom"} dicts.
    """
    if duration <= 0:
        raise ValueError("duration must be > 0")
    if steps < 1:
        raise ValueError("steps must be >= 1")
    t0 = frames[0]["time"]
    t1 = frames[-1]["time"]
    out = []
    for i in range(steps):
        t = duration * i / (steps - 1) if steps > 1 else 0.0
        # clamp to keyframe span
        tc = _clamp(t, t0, t1)
        # find segment
        if tc <= t0:
            a, b = frames[0], frames[0]
        elif tc >= t1:
            a, b = frames[-1], frames[-1]
        else:
            a, b = frames[0], frames[-1]
            for j in range(len(frames) - 1):
                if frames[j]["time"] <= tc <= frames[j + 1]["time"]:
                    a, b = frames[j], frames[j + 1]
                    break
        span = b["time"] - a["time"]
        u = 0.0 if span <= 1e-9 else (tc - a["time"]) / span
        u = _smoothstep(u)
        pos = [a["position"][k] + (b["position"][k] - a["position"][k]) * u for k in range(3)]
        zoom = a["zoom"] + (b["zoom"] - a["zoom"]) * u
        out.append({"time": t, "position": pos, "zoom": zoom})
    return out


def _audio_energy(waveform, sample_rate, steps, window):
    """Compute a per-step RMS energy envelope from a waveform tensor.

    waveform: [C, T] or [T] float tensor (any range).
    Returns a list of `steps` floats in ~[0, 1] (normalised by max).
    """
    if isinstance(waveform, dict):
        wf = waveform.get("waveform")
        sr = int(waveform.get("sample_rate", sample_rate or 44100))
    else:
        wf = waveform
        sr = int(sample_rate or 44100)
    if wf is None:
        raise ValueError("audio waveform missing")
    if not isinstance(wf, torch.Tensor):
        raise ValueError("audio waveform must be a torch tensor")
    wf = wf.detach().float().cpu()
    if wf.dim() == 1:
        wf = wf.unsqueeze(0)
    if wf.dim() != 2:
        raise ValueError("waveform must be [C, T] or [T]")
    T = wf.shape[1]
    if T == 0:
        raise ValueError("waveform has no samples")
    # mono mix
    mono = wf.mean(dim=0)
    # windowed RMS
    if window < 1:
        window = 1
    n_win = max(1, T // window)
    # pad to multiple of window
    pad = n_win * window - T
    if pad > 0:
        mono = torch.cat([mono, torch.zeros(pad)])
    mono = mono.reshape(n_win, window)
    rms = mono.pow(2).mean(dim=1).sqrt()
    peak = rms.max().item() if n_win else 0.0
    if peak <= 1e-9:
        env = [0.0] * steps
    else:
        env = (rms / peak).tolist()
    # resample env to `steps` by linear interpolation
    out = []
    if steps == 1:
        out = [env[0]]
    else:
        for i in range(steps):
            x = (len(env) - 1) * i / (steps - 1)
            j = int(math.floor(x))
            f = x - j
            if j + 1 < len(env):
                out.append(env[j] * (1 - f) + env[j + 1] * f)
            else:
                out.append(env[-1])
    return out


class PSN_CameraTimelineEditor:
    """Interpolate camera keyframes into a smooth timeline curve.

    Input: JSON list of {time, position, zoom} keyframes + duration.
    Output: JSON list of interpolated {time, position, zoom} samples.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "keyframes": ("STRING", {"default": "[{\"time\": 0, \"position\": [0, 0, 0], \"zoom\": 1}, {\"time\": 1, \"position\": [1, 0, 0], \"zoom\": 2}]"}),
                "duration": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 600.0}),
                "steps": ("INT", {"default": 32, "min": 2, "max": 1024}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("camera_curve",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, keyframes, duration, steps):
        frames, err = _parse_keyframes(keyframes)
        if err is not None:
            raise ValueError(err)
        curve = _interp_keyframes(frames, float(duration), int(steps))
        return (json.dumps(curve),)


class PSN_EnergyCurveMapper:
    """Modulate camera speed/zoom by audio energy peaks.

    Input: camera_curve JSON + AUDIO dict {waveform, sample_rate}.
    Output: JSON of synced camera params with per-step speed and zoom
    scaled by the audio energy envelope.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "camera_curve": ("STRING", {}),
                "audio": ("AUDIO",),
                "energy_gain": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
                "speed_gain": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("synced_camera_params",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, camera_curve, audio, energy_gain, speed_gain):
        if not isinstance(camera_curve, str):
            raise ValueError("camera_curve must be a JSON string")
        try:
            curve = json.loads(camera_curve)
        except Exception as e:
            raise ValueError("invalid camera_curve JSON: %s" % e)
        if not isinstance(curve, list) or len(curve) < 2:
            raise ValueError("camera_curve must be a list of >= 2 samples")
        for i, s in enumerate(curve):
            if not isinstance(s, dict) or "position" not in s or "zoom" not in s:
                raise ValueError("curve sample %d malformed" % i)
        # audio energy
        sr = audio.get("sample_rate", 44100) if isinstance(audio, dict) else 44100
        steps = len(curve)
        window = max(1, int(sr / 100))  # ~10 ms windows
        env = _audio_energy(audio, sr, steps, window)
        # per-step speed from position deltas
        out = []
        for i, s in enumerate(curve):
            pos = [float(p) for p in s["position"]]
            zoom = float(s["zoom"])
            if i + 1 < steps:
                npos = [float(p) for p in curve[i + 1]["position"]]
                dt = float(curve[i + 1].get("time", i + 1)) - float(s.get("time", i))
                if dt <= 1e-9:
                    dt = 1.0 / steps
                dist = math.sqrt(sum((npos[k] - pos[k]) ** 2 for k in range(3)))
                speed = dist / dt
            else:
                speed = 0.0
            e = _clamp(env[i] * float(energy_gain), 0.0, 10.0)
            out.append({
                "time": float(s.get("time", i)),
                "position": pos,
                "zoom": zoom * (1.0 + 0.5 * e),
                "speed": speed * (1.0 + float(speed_gain) * e),
                "energy": e,
            })
        return (json.dumps(out),)


NODE_CLASS_MAPPINGS = {
    "PSN_CameraTimelineEditor": PSN_CameraTimelineEditor,
    "PSN_EnergyCurveMapper": PSN_EnergyCurveMapper,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CameraTimelineEditor": "Camera Timeline Editor",
    "PSN_EnergyCurveMapper": "Energy Curve Mapper",
}
