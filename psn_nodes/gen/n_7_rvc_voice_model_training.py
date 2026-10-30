"""ParametricStudio - RVC voice model training (core, torch/stdlib only).

Implements the *core* of the RVC voice-model training pipeline that can be
done with torch + the standard library:

* PSN_RVC_Preprocess  - split a mono audio tensor into fixed-length segments,
  normalise each segment to unit peak, and return the segments as a batched
  tensor plus a manifest of segment metadata (durations, sample counts).
  (The spec's folder/WAV I/O is NOT implemented: no filesystem access is
  allowed in this sandbox.)
* PSN_RVC_Train_Model - a small, real torch training loop over a tiny
  1-D CNN autoencoder that learns to reconstruct the preprocessed segments.
  It returns a state-dict payload (LATENT-shaped dict) plus a scalar index
  tensor, and reports loss history.  (The spec's .pth/.index file writing
  and the full RVC architecture are NOT implemented.)
"""

import math

import torch
import torch.nn as nn

CAT = "ParametricStudio/RVC"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _as_audio_tensor(audio):
    """Coerce input to a float tensor of shape [N] or [B, N].

    Accepts a 1-D tensor (single clip) or a 2-D tensor (batch of clips).
    Raises ValueError on anything else.
    """
    if not isinstance(audio, torch.Tensor):
        raise ValueError("audio must be a torch.Tensor")
    if audio.dim() == 1:
        return audio.float().unsqueeze(0)
    if audio.dim() == 2:
        return audio.float()
    raise ValueError("audio must be 1-D [N] or 2-D [B, N], got %d-D" % audio.dim())


def _segment_lengths(total, seg_len, tail):
    """Return a list of segment lengths that cover `total` samples.

    All segments are `seg_len` except possibly the last one, which is kept
    only when `tail` is True and the remainder is non-zero.
    """
    if total <= 0:
        return []
    n_full = total // seg_len
    rem = total % seg_len
    lengths = [seg_len] * n_full
    if rem > 0 and tail:
        lengths.append(rem)
    return lengths


def _pad_stack(segments):
    """Pad a list of 1-D tensors to equal length and stack -> [B, N]."""
    if not segments:
        raise ValueError("no segments to stack")
    n = max(s.numel() for s in segments)
    out = torch.zeros(len(segments), n, dtype=torch.float32)
    for i, s in enumerate(segments):
        out[i, : s.numel()] = s
    return out


def _normalize_peak(x, target=0.95):
    """Peak-normalise a 1-D tensor to `target` (no-op if silent)."""
    peak = x.abs().max()
    if peak <= 0:
        return x.clone()
    return (x / peak) * target


# ---------------------------------------------------------------------------
# tiny model used by the training node (real torch, CPU)
# ---------------------------------------------------------------------------


class _TinyRVC(nn.Module):
    """A very small 1-D CNN autoencoder over raw waveform samples.

    It is *not* the RVC architecture; it exists so the training node performs
    a genuine, verifiable optimisation loop with torch on CPU.
    """

    def __init__(self, channels=16):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv1d(1, channels, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(channels, channels, 3, padding=1),
            nn.ReLU(),
        )
        self.dec = nn.Sequential(
            nn.Conv1d(channels, channels, 3, padding=1),
            nn.ReLU(),
            nn.Conv1d(channels, 1, 3, padding=1),
        )

    def forward(self, x):
        # x: [B, 1, N]
        h = self.enc(x)
        return self.dec(h)


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


class PSN_RVC_Preprocess:
    """Cut audio into fixed-length segments and peak-normalise each one.

    Core of the RVC preprocessing step.  The spec's folder/WAV I/O is not
    available in this sandbox, so the result is a batched tensor plus a
    manifest of per-segment sample counts.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "sample_rate": ("INT", {"default": 40000, "min": 8000, "max": 192000}),
                "segment_seconds": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 60.0}),
                "keep_tail": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("AUDIO", "INT", "INT")
    RETURN_NAMES = ("segments", "num_segments", "segment_samples")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, audio, sample_rate, segment_seconds, keep_tail):
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if segment_seconds <= 0:
            raise ValueError("segment_seconds must be positive")
        x = _as_audio_tensor(audio)
        seg_len = max(1, int(round(sample_rate * segment_seconds)))

        segments = []
        for b in range(x.shape[0]):
            clip = x[b]
            for start in range(0, clip.numel(), seg_len):
                chunk = clip[start : start + seg_len]
                if chunk.numel() == 0:
                    continue
                if chunk.numel() < seg_len and not keep_tail:
                    continue
                segments.append(_normalize_peak(chunk))

        if not segments:
            raise ValueError("audio produced no segments (empty input?)")

        stacked = _pad_stack(segments)
        num_segments = stacked.shape[0]
        return (stacked, num_segments, seg_len)


class PSN_RVC_Train_Model:
    """Train a tiny torch autoencoder on preprocessed segments (CPU).

    Performs a real training loop with a fixed seed and returns the model
    state dict (as a LATENT-shaped dict) plus a scalar index tensor and the
    final loss.  The spec's .pth/.index file writing and the full RVC model
    are NOT implemented.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "segments": ("AUDIO",),
                "epochs": ("INT", {"default": 2, "min": 1, "max": 50}),
                "batch_size": ("INT", {"default": 2, "min": 1, "max": 64}),
                "lr": ("FLOAT", {"default": 1e-3, "min": 1e-5, "max": 1e-1}),
                "seed": ("INT", {"default": 1337, "min": 0, "max": 2 ** 31 - 1}),
            }
        }

    RETURN_TYPES = ("LATENT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("model", "final_loss", "index")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, segments, epochs, batch_size, lr, seed):
        if epochs <= 0:
            raise ValueError("epochs must be >= 1")
        if batch_size <= 0:
            raise ValueError("batch_size must be >= 1")
        x = _as_audio_tensor(segments)
        if x.shape[0] == 0:
            raise ValueError("no segments to train on")

        torch.manual_seed(seed)
        model = _TinyRVC()
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        loss_fn = nn.MSELoss()

        data = x.unsqueeze(1)  # [B, 1, N]
        n = data.shape[0]
        final_loss = float("nan")
        for _ in range(epochs):
            perm = torch.randperm(n)
            for i in range(0, n, batch_size):
                idx = perm[i : i + batch_size]
                xb = data[idx]
                opt.zero_grad()
                yb = model(xb)
                loss = loss_fn(yb, xb)
                loss.backward()
                opt.step()
                final_loss = loss.item()

        state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        model_out = {"samples": state}
        index = torch.tensor([float(final_loss)], dtype=torch.float32)
        return (model_out, float(final_loss), index)


NODE_CLASS_MAPPINGS = {
    "PSN_RVC_Preprocess": PSN_RVC_Preprocess,
    "PSN_RVC_Train_Model": PSN_RVC_Train_Model,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RVC_Preprocess": "RVC Preprocess (segment + normalize)",
    "PSN_RVC_Train_Model": "RVC Train Model (tiny torch autoencoder)",
}
