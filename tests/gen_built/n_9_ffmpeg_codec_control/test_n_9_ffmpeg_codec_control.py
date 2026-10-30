import torch

from n_9_ffmpeg_codec_control import (
    PSN_FFMpegEncoder,
    PSN_FFMpegDecoder,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    build_encode_command,
    build_decode_command,
    tensor_to_raw_frames,
    raw_frames_to_tensor,
)


# 1. module-level mappings exist and are consistent
assert set(NODE_CLASS_MAPPINGS) == {"PSN_FFMpegEncoder", "PSN_FFMpegDecoder"}
assert set(NODE_DISPLAY_NAME_MAPPINGS) == set(NODE_CLASS_MAPPINGS)
assert NODE_CLASS_MAPPINGS["PSN_FFMpegEncoder"] is PSN_FFMpegEncoder

# 2. INPUT_TYPES / RETURN metadata
enc_in = PSN_FFMpegEncoder.INPUT_TYPES()
assert "image" in enc_in["required"] and enc_in["required"]["image"] == ("IMAGE",)
assert "codec" in enc_in["required"]
assert set(enc_in["required"]["codec"][0]) == {"h264", "hevc", "vp9"}
assert PSN_FFMpegEncoder.RETURN_TYPES == ("STRING", "INT")
assert PSN_FFMpegEncoder.FUNCTION == "run"
assert PSN_FFMpegEncoder.CATEGORY.startswith("ParametricStudio/")

# 3. encode command construction (h264)
img = torch.rand(2, 8, 8, 3)
cmd = build_encode_command(img, "h264", 23, "out.mp4", fps=24)
assert cmd[0] == "ffmpeg"
assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "libx264"
assert "-crf" in cmd and cmd[cmd.index("-crf") + 1] == "23"
assert cmd[-1] == "out.mp4"
assert "-s" in cmd and cmd[cmd.index("-s") + 1] == "8x8"
assert "-pix_fmt" in cmd and "rgb24" in cmd

# 4. encode command construction (vp9 -> webm encoder)
cmd_vp9 = build_encode_command(img, "vp9", 30, "out.webm", fps=30)
assert cmd_vp9[cmd_vp9.index("-c:v") + 1] == "libvpx-vp9"
assert cmd_vp9[-1] == "out.webm"

# 5. node run returns command string + raw byte count; input not modified
before = img.clone()
node = PSN_FFMpegEncoder()
out_cmd, out_bytes = node.run(img, "h264", 23, "out.mp4", fps=24)
assert isinstance(out_cmd, str) and out_cmd.startswith("ffmpeg")
assert out_bytes == 2 * 8 * 8 * 3  # B*H*W*3 bytes of rgb24
assert torch.equal(img, before)  # no in-place modification

# 6. tensor -> raw frames -> tensor round trip preserves values (approx)
raw, b, h, w, c = tensor_to_raw_frames(img)
assert len(raw) == b * h * w * c
back = raw_frames_to_tensor(raw, b, h, w, c)
assert back.shape == img.shape
assert torch.allclose(back, img, atol=1.0 / 255.0 + 1e-6)

# 7. bad input: wrong shape raises
try:
    build_encode_command(torch.rand(2, 8, 8, 4), "h264", 23, "x.mp4")
    raise AssertionError("expected ValueError for wrong channel count")
except ValueError:
    pass

# 8. bad input: out-of-range values raise
try:
    build_encode_command(torch.rand(2, 8, 8, 3) * 2.0, "h264", 23, "x.mp4")
    raise AssertionError("expected ValueError for out-of-range values")
except ValueError:
    pass

# 9. bad input: unsupported codec raises
try:
    build_encode_command(img, "av1", 23, "x.mp4")
    raise AssertionError("expected ValueError for unsupported codec")
except ValueError:
    pass

# 10. bad input: odd width raises (yuv420p needs even dims)
try:
    build_encode_command(torch.rand(1, 7, 8, 3), "h264", 23, "x.mp4")
    raise AssertionError("expected ValueError for odd width")
except ValueError:
    pass

# 11. bad input: crf out of range raises
try:
    build_encode_command(img, "h264", 99, "x.mp4")
    raise AssertionError("expected ValueError for crf out of range")
except ValueError:
    pass

# 12. decode command construction
dcmd = build_decode_command("in.mp4", "hevc", fps=24)
assert dcmd[0] == "ffmpeg"
assert dcmd[1] == "-i" and dcmd[2] == "in.mp4"
assert dcmd[dcmd.index("-c:v") + 1] == "libx265"
assert dcmd[-1] == "-"

# 13. decoder node run returns a command string
dnode = PSN_FFMpegDecoder()
dout = dnode.run("in.mp4", "hevc", fps=24)
assert isinstance(dout, tuple) and len(dout) == 1
assert dout[0].startswith("ffmpeg")

# 14. bad input: empty file_path raises
try:
    build_decode_command("", "h264")
    raise AssertionError("expected ValueError for empty file_path")
except ValueError:
    pass

print("ok")
