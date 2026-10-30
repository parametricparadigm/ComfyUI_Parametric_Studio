"""ParametricStudio: Automated Video Contact Sheet Generation.

Nodes:
  * PSN_Video_Frame_Sampler     - pick N frames from a video tensor (uniform / keyframe / first_last).
  * PSN_Contact_Sheet_Assembler - stitch sampled frames into a grid, optionally with a
                                  small numeric label drawn on each cell.

Video representation: float torch tensor [F, H, W, C] in 0..1 (C in {1,3,4}).
All work is done on CPU with torch only; no external libraries are required.
"""

import torch

CAT = "ParametricStudio/Video"


def _as_video(video):
    """Validate and normalise a video tensor to [F, H, W, C] float in 0..1."""
    if not isinstance(video, torch.Tensor):
        raise TypeError("video must be a torch.Tensor")
    if video.dim() == 3:
        video = video.unsqueeze(0)
    if video.dim() != 4:
        raise ValueError("video must be a tensor of shape [F, H, W, C] (or [H, W, C])")
    f, h, w, c = video.shape
    if c not in (1, 3, 4):
        raise ValueError("video channel count must be 1, 3 or 4, got %d" % c)
    if f < 1 or h < 1 or w < 1:
        raise ValueError("video dimensions must be positive")
    x = video.detach().to(dtype=torch.float32)
    if x.min() < 0.0 or x.max() > 1.0:
        x = x.clamp_(0.0, 1.0)
    return x


def _uniform_indices(total, n):
    if n <= 0:
        return []
    if n >= total:
        return list(range(total))
    step = total / float(n)
    return [int(round(i * step)) for i in range(n)]


def _first_last_indices(total, n):
    if n <= 0:
        return []
    if n >= total:
        return list(range(total))
    if n == 1:
        return [0]
    if n == 2:
        return [0, total - 1]
    # n >= 3: first, last, plus n-2 evenly spaced intermediates in (0, total-1)
    inner = n - 2
    step = (total - 1) / float(inner + 1)
    idx = [0]
    for i in range(1, inner + 1):
        idx.append(int(round(i * step)))
    idx.append(total - 1)
    seen = set()
    out = []
    for i in idx:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _keyframe_indices(total, n, frames):
    """Motion-based keyframe placeholder (falls back to uniform)."""
    if n <= 0:
        return []
    if n >= total:
        return list(range(total))
    if total < 2:
        return [0]
    diff = (frames[1:] - frames[:-1]).abs().mean(dim=(1, 2, 3))
    order = torch.argsort(diff, descending=True).tolist()
    picked = []
    for i in order:
        if i + 1 not in picked:
            picked.append(i + 1)
        if len(picked) >= n:
            break
    if len(picked) < n:
        for i in _uniform_indices(total, n):
            if i not in picked:
                picked.append(i)
            if len(picked) >= n:
                break
    picked.sort()
    return picked[:n]


_FONT = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["01110", "10001", "00001", "00110", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ":": ["00000", "00100", "00000", "00100", "00000", "00100", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def _bitmap(text):
    glyphs = [_FONT.get(ch, _FONT[" "]) for ch in text]
    gw, gh, pad = 5, 7, 1
    bw = len(glyphs) * (gw + pad) + pad
    bh = gh + 2 * pad
    bmp = torch.zeros(bh, bw, dtype=torch.float32)
    for gi, g in enumerate(glyphs):
        x0 = pad + gi * (gw + pad)
        for y in range(gh):
            for x in range(gw):
                if g[y][x] == "1":
                    bmp[pad + y, x0 + x] = 1.0
    return bmp


def _draw_label(img, text):
    """Draw `text` into the top-left corner of `img` ([H, W, C] float 0..1)."""
    out = img.clone()
    if not text:
        return out
    bmp = _bitmap(text)
    bh, bw = bmp.shape
    cell_h, cell_w = img.shape[0], img.shape[1]
    max_w = max(8, int(cell_w * 0.25))
    max_h = max(8, int(cell_h * 0.15))
    scale = min(max_w / float(bw), max_h / float(bh), 1.0)
    if scale < 1.0:
        new_w = max(4, int(bw * scale))
        new_h = max(4, int(bh * scale))
        small = torch.zeros(new_h, new_w, dtype=torch.float32)
        for y in range(new_h):
            sy = min(bh - 1, int(y / scale))
            for x in range(new_w):
                sx = min(bw - 1, int(x / scale))
                small[y, x] = bmp[sy, sx]
        bmp = small
        bh, bw = bmp.shape
    if bh >= cell_h or bw >= cell_w:
        return out
    margin = 2
    patch_h = bh + 2 * margin
    patch_w = bw + 2 * margin
    if patch_h > cell_h or patch_w > cell_w:
        return out
    c = img.shape[2]
    bg = torch.zeros(patch_h, patch_w, c, dtype=torch.float32)
    fg = torch.ones(patch_h, patch_w, c, dtype=torch.float32)
    g = bmp.unsqueeze(-1).expand(bh, bw, c)
    region = fg[margin:margin + bh, margin:margin + bw, :]
    region = region * g + bg[margin:margin + bh, margin:margin + bw, :] * (1.0 - g)
    fg[margin:margin + bh, margin:margin + bw, :] = region
    alpha = 0.6
    cell = out[:patch_h, :patch_w, :]
    out[:patch_h, :patch_w, :] = cell * (1.0 - alpha) + fg * alpha
    return out


class PSN_Video_Frame_Sampler:
    """Sample N frames from a video tensor using a chosen strategy."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
                "num_frames": ("INT", {"default": 10, "min": 1, "max": 4096}),
                "sampling_strategy": (["uniform", "keyframe", "first_last"],),
            }
        }

    RETURN_TYPES = ("IMAGE", "LIST[INT]")
    RETURN_NAMES = ("sampled_frames", "frame_indices")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, video, num_frames, sampling_strategy):
        x = _as_video(video)
        total = x.shape[0]
        n = max(1, min(int(num_frames), total))
        if sampling_strategy == "first_last":
            idx = _first_last_indices(total, n)
        elif sampling_strategy == "keyframe":
            idx = _keyframe_indices(total, n, x)
        else:
            idx = _uniform_indices(total, n)
        if not idx:
            idx = [0]
        idx = [int(i) for i in idx]
        sel = x[idx]
        return (sel, idx)


class PSN_Contact_Sheet_Assembler:
    """Stitch sampled frames into a grid, optionally with a numeric label per cell."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sampled_frames": ("IMAGE",),
                "frame_indices": ("LIST[INT]",),
                "cols": ("INT", {"default": 4, "min": 1, "max": 64}),
                "rows": ("INT", {"default": 4, "min": 1, "max": 64}),
                "show_timestamps": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("contact_sheet",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, sampled_frames, frame_indices, cols, rows, show_timestamps):
        if not isinstance(sampled_frames, torch.Tensor):
            raise TypeError("sampled_frames must be a torch.Tensor")
        x = sampled_frames.detach().to(dtype=torch.float32)
        if x.dim() == 3:
            x = x.unsqueeze(0)
        if x.dim() != 4:
            raise ValueError("sampled_frames must be [B, H, W, C]")
        b, h, w, c = x.shape
        if c not in (1, 3, 4):
            raise ValueError("channel count must be 1, 3 or 4")
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        if not isinstance(frame_indices, (list, tuple)):
            frame_indices = [frame_indices]
        idx = [int(i) for i in frame_indices]
        n = min(b, cols * rows)
        if n == 0:
            raise ValueError("no frames to assemble")
        used = x[:n]
        if show_timestamps:
            cells = []
            for i in range(n):
                label = str(idx[i]) if i < len(idx) else str(i)
                cells.append(_draw_label(used[i], label))
            used = torch.stack(cells, dim=0)
        total_cells = cols * rows
        if n < total_cells:
            pad = torch.zeros(total_cells - n, h, w, c, dtype=torch.float32)
            used = torch.cat([used, pad], dim=0)
        grid = used.view(rows, cols, h, w, c)
        grid = grid.permute(0, 2, 1, 3, 4).reshape(rows * h, cols * w, c)
        return (grid,)


NODE_CLASS_MAPPINGS = {
    "PSN_Video_Frame_Sampler": PSN_Video_Frame_Sampler,
    "PSN_Contact_Sheet_Assembler": PSN_Contact_Sheet_Assembler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_Video_Frame_Sampler": "Video Frame Sampler",
    "PSN_Contact_Sheet_Assembler": "Contact Sheet Assembler",
}
