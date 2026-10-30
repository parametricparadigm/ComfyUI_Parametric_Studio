"""Non-destructive post-processing hook for ComfyUI (ParametricStudio).

Implements the pattern from the original studio's ``mastering.after_render`` /
``mastering.master_song``: a mastering step (here: loudness normalization) is
applied to an audio artifact and the result is appended as a NEW artifact in
the job's artifact list, while the original artifact is left completely
untouched (no in-place mutation, no file rewriting).

Audio is represented as a plain float torch tensor of shape [B, T] (mono) or
[B, T, C] (multi-channel), values in roughly -1..1.  The "artifact" is a
dict: {"name": str, "audio": tensor, "meta": dict}.  The hook returns a new
artifact list (original list object is never mutated) plus the new artifact.
"""

import torch

CAT = "ParametricStudio/PostProcessing"


def _as_audio(audio):
    """Validate/convert audio to a float torch tensor; never mutates input."""
    if isinstance(audio, torch.Tensor):
        x = audio
    elif isinstance(audio, (list, tuple)):
        x = torch.tensor(audio, dtype=torch.float32)
    else:
        raise TypeError("audio must be a torch.Tensor or a nested list of floats")
    if x.dim() < 1 or x.dim() > 3:
        raise ValueError("audio tensor must have 1..3 dims ([T], [B,T] or [B,T,C])")
    if x.dtype != torch.float32:
        x = x.to(torch.float32)
    return x.detach().clone()  # always work on a copy


def _normalize_loudness(x, target_lufs=-14.0, ceiling_db=-1.0):
    """Simple gain-based loudness normalization (RMS -> target LUFS-ish).

    Pure torch, CPU.  Returns a NEW tensor; input is not modified.
    """
    x = x.float()
    rms = x.pow(2).mean().sqrt()
    if rms.item() < 1e-8:
        # silent input: nothing to normalize, return unchanged copy
        return x.clone()
    current_lufs = 20.0 * torch.log10(rms + 1e-8).item()
    gain_db = target_lufs - current_lufs
    # limit gain so peaks do not exceed the ceiling
    peak = x.abs().max()
    if peak.item() > 1e-8:
        ceiling_amp = 10.0 ** (ceiling_db / 20.0) if ceiling_db else 1.0
        max_gain_db = 20.0 * (torch.log10(torch.tensor(ceiling_amp / peak.item() + 1e-8)).item())
        gain_db = min(gain_db, max_gain_db)
    gain = 10.0 ** (gain_db / 20.0)
    out = x * gain
    # hard safety clip (still non-destructive: new tensor)
    return out.clamp(-1.0, 1.0)


def _new_artifact(name, audio, meta):
    return {"name": name, "audio": audio, "meta": dict(meta)}


class PSN_NonDestructiveMasterHook:
    """Append a loudness-mastered copy of an audio artifact as a NEW artifact.

    Non-destructive: the input artifact list and the original artifact are
    never modified; the mastered audio is a fresh tensor with a new name and
    its own metadata (original name kept in meta['source']).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "artifacts": ("ARTIFACTS",),
                "target": ("INT", {"default": -14, "min": -60, "max": 0}),
                "suffix": ("STRING", {"default": "_mastered"}),
            }
        }

    RETURN_TYPES = ("ARTIFACTS", "ARTIFACT")
    RETURN_NAMES = ("artifacts", "mastered")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, artifacts, target, suffix):
        if not isinstance(artifacts, (list, tuple)):
            raise TypeError("artifacts must be a list of artifact dicts")
        if not artifacts:
            raise ValueError("artifacts list is empty; nothing to master")
        # work on a shallow copy of the list; never mutate the caller's list
        new_list = [dict(a) for a in artifacts]
        last = new_list[-1]
        if "audio" not in last:
            raise ValueError("last artifact has no 'audio' field to master")
        audio = _as_audio(last["audio"])
        mastered = _normalize_loudness(audio, target_lufs=float(target))
        src_name = str(last.get("name", "audio"))
        meta = dict(last.get("meta", {}))
        meta["source"] = src_name
        meta["target_lufs"] = int(target)
        meta["mastered"] = True
        new_art = _new_artifact(src_name + suffix, mastered, meta)
        new_list.append(new_art)
        return (new_list, new_art)


class PSN_MasterSongCopy:
    """Create a mastered copy of a single library song (audio tensor).

    Mirrors ``mastering.master_song``: returns a brand-new artifact dict with
    the normalized audio; the input tensor is never modified.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "name": ("STRING", {"default": "song"}),
                "target": ("INT", {"default": -14, "min": -60, "max": 0}),
            }
        }

    RETURN_TYPES = ("ARTIFACT",)
    RETURN_NAMES = ("mastered",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, name, target):
        x = _as_audio(audio)
        mastered = _normalize_loudness(x, target_lufs=float(target))
        meta = {"source": str(name), "target_lufs": int(target), "mastered": True}
        return (_new_artifact(str(name) + "_mastered", mastered, meta),)


NODE_CLASS_MAPPINGS = {
    "PSN_NonDestructiveMasterHook": PSN_NonDestructiveMasterHook,
    "PSN_MasterSongCopy": PSN_MasterSongCopy,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_NonDestructiveMasterHook": "Non-Destructive Master Hook (append mastered audio)",
    "PSN_MasterSongCopy": "Master Song Copy",
}
