"""ParametricStudio - FFmpeg Codec Control (command construction + tensor<->frame helpers).

The real FFmpeg encode/decode step requires a subprocess + a static ffmpeg
binary, which is not allowed in this sandbox.  This module therefore
implements the *core* that torch/stdlib can do:

* codec -> ffmpeg argument mapping (encoder name, pix_fmt, container ext)
* full ffmpeg command-line construction for encode and decode
* tensor -> raw RGB frame bytes (what would be piped into ffmpeg stdin)
* raw RGB frame bytes -> tensor (what would be built from ffmpeg stdout)

The ComfyUI nodes expose these as pure functions so the command can be
inspected/verified without ever touching the network, disk or a process.
"""

import struct

import torch

CAT = "ParametricStudio/Video"

# ---------------------------------------------------------------------------
# codec metadata
# ---------------------------------------------------------------------------

CODECS = ("h264", "hevc", "vp9")

_CODEC_INFO = {
    "h264": {"encoder": "libx264", "pix_fmt": "yuv420p", "ext": "mp4", "container": "mp4"},
    "hevc": {"encoder": "libx265", "pix_fmt": "yuv420p", "ext": "mp4", "container": "mp4"},
    "vp9": {"encoder": "libvpx-vp9", "pix_fmt": "yuv420p", "ext": "webm", "container": "webm"},
}


def _codec_info(codec):
    if codec not in _CODEC_INFO:
        raise ValueError(f"unsupported codec: {codec!r}; expected one of {list(CODECS)}")
    return _CODEC_INFO[codec]


def _s(x):
    """Unwrap a ComfyUI LATENT dict to its samples tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Re-wrap samples into a ComfyUI LATENT dict (preserving other keys)."""
    if isinstance(latent, dict):
        d = dict(latent)
        d["samples"] = samples
        return d
    return {"samples": samples}


# ---------------------------------------------------------------------------
# command construction
# ---------------------------------------------------------------------------

def build_encode_command(image, codec, crf, output_path, fps=24):
    """Return the ffmpeg argv list that would encode `image` (a [B,H,W,C]
    float tensor in 0..1) to `output_path` using `codec` at quality `crf`.

    The raw RGB frames are piped on stdin (``-f rawvideo -pix_fmt rgb24``).
    """
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4 or image.shape[-1] != 3:
        raise ValueError(f"image must be [B,H,W,3], got shape {tuple(image.shape)}")
    if not (0.0 <= float(image.min()) and float(image.max()) <= 1.0):
        raise ValueError("image values must be in 0..1")
    if not isinstance(output_path, str) or not output_path:
        raise ValueError("output_path must be a non-empty string")
    if not isinstance(crf, int) or isinstance(crf, bool):
        raise TypeError("crf must be an int")
    if not (0 <= crf <= 63):
        raise ValueError("crf must be in 0..63")
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps must be a positive int")

    info = _codec_info(codec)
    _, h, w, _ = image.shape
    if w % 2 or h % 2:
        raise ValueError("width and height must be even for yuv420p")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", info["encoder"],
        "-pix_fmt", info["pix_fmt"],
        "-crf", str(crf),
        output_path,
    ]
    return cmd


def build_decode_command(file_path, codec, fps=24):
    """Return the ffmpeg argv list that would decode `file_path` (a video
    encoded with `codec`) to raw RGB frames on stdout.
    """
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("file_path must be a non-empty string")
    if not isinstance(fps, int) or fps <= 0:
        raise ValueError("fps must be a positive int")
    info = _codec_info(codec)
    cmd = [
        "ffmpeg",
        "-i", file_path,
        "-c:v", info["encoder"],
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-",
    ]
    return cmd


# ---------------------------------------------------------------------------
# tensor <-> raw frame bytes (the data that would be piped to/from ffmpeg)
# ---------------------------------------------------------------------------

def tensor_to_raw_frames(image):
    """Convert a [B,H,W,3] float tensor in 0..1 to raw RGB24 bytes.

    Returns (bytes, B, H, W).  The input tensor is NOT modified.
    """
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4 or image.shape[-1] != 3:
        raise ValueError(f"image must be [B,H,W,3], got shape {tuple(image.shape)}")
    if float(image.min()) < 0.0 or float(image.max()) > 1.0:
        raise ValueError("image values must be in 0..1")
    b, h, w, c = image.shape
    u8 = (image.clamp(0.0, 1.0) * 255.0 + 0.5).to(torch.uint8)
    return u8.contiguous().view(-1).numpy().tobytes(), b, h, w, c


def raw_frames_to_tensor(data, b, h, w, c=3):
    """Convert raw RGB24 bytes back to a [B,H,W,C] float tensor in 0..1."""
    expected = b * h * w * c
    if len(data) != expected:
        raise ValueError(f"expected {expected} bytes, got {len(data)}")
    u8 = torch.frombuffer(bytearray(data), dtype=torch.uint8).view(b, h, w, c)
    return u8.to(torch.float32) / 255.0


# ---------------------------------------------------------------------------
# ComfyUI nodes
# ---------------------------------------------------------------------------

class PSN_FFMpegEncoder:
    """Build the FFmpeg encode command for a video batch (no subprocess here).

    Real encoding (piping frames to an ffmpeg binary and writing the file)
    is NOT implemented in this sandbox because subprocess is forbidden.
    The node returns the exact argv that would be executed, plus the raw
    frame payload size, so the command can be verified/used elsewhere.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "codec": (list(CODECS),),
                "crf": ("INT", {"default": 23, "min": 0, "max": 63}),
                "output_path": ("STRING", {"default": "out.mp4"}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 240}),
            }
        }

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("ffmpeg_command", "raw_frame_bytes")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image, codec, crf, output_path, fps=24):
        cmd = build_encode_command(image, codec, crf, output_path, fps=fps)
        raw, *_ = tensor_to_raw_frames(image)
        return (" ".join(cmd), len(raw))


class PSN_FFMpegDecoder:
    """Build the FFmpeg decode command for a video file (no subprocess here).

    Real decoding (running ffmpeg and reading raw frames from stdout) is NOT
    implemented in this sandbox because subprocess is forbidden.  The node
    returns the exact argv that would be executed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "in.mp4"}),
                "codec": (list(CODECS),),
                "fps": ("INT", {"default": 24, "min": 1, "max": 240}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("ffmpeg_command",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, file_path, codec, fps=24):
        cmd = build_decode_command(file_path, codec, fps=fps)
        return (" ".join(cmd),)


NODE_CLASS_MAPPINGS = {
    "PSN_FFMpegEncoder": PSN_FFMpegEncoder,
    "PSN_FFMpegDecoder": PSN_FFMpegDecoder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_FFMpegEncoder": "FFmpeg Encoder (command)",
    "PSN_FFMpegDecoder": "FFmpeg Decoder (command)",
}
