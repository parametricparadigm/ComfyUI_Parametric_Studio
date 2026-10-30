"""Latent operations on REAL ComfyUI latents ({"samples": tensor [B,C,H,W] or video [B,C,T,H,W]}). Original code. Every node returns a new latent (inputs are never modified), keeps dtype and device,
and refuses NaN/Inf results instead of passing them downstream. Tested on CPU tensors in tests/test_latent_nodes.py."""
import json, math
import torch
import torch.nn.functional as F

CAT = "ParametricStudio/Latent"

def _s(lat):
    if not isinstance(lat, dict) or not torch.is_tensor(lat.get("samples")): raise ValueError("expected a LATENT: {'samples': tensor}")
    return lat["samples"]

def _out(lat, x):
    if not torch.isfinite(x).all(): raise ValueError("result contains NaN/Inf: lower the strength or check the inputs")
    o = {k: v for k, v in lat.items() if k != "samples"}; o["samples"] = x; return o

def _match(a, b):
    """b brought to a's shape: spatial resize (bilinear/trilinear) and batch broadcast/trim. Channel count must already agree."""
    if a.shape[1] != b.shape[1]: raise ValueError(f"channel mismatch: {a.shape[1]} vs {b.shape[1]}")
    if b.shape[2:] != a.shape[2:]: b = F.interpolate(b.float(), size=a.shape[2:], mode="trilinear" if a.dim() == 5 else "bilinear", align_corners=False).to(a.dtype)
    if b.shape[0] != a.shape[0]: b = b[:1].expand(a.shape[0], *b.shape[1:]) if b.shape[0] == 1 else b[: a.shape[0]] if b.shape[0] > a.shape[0] else b.repeat(math.ceil(a.shape[0] / b.shape[0]), *[1] * (b.dim() - 1))[: a.shape[0]]
    return b

class PSN_LatentMath:
    """a (op) b with a strength: add, subtract, multiply, lerp, maximum, minimum. b is resized to a when the shapes differ. result = a + strength * (op(a,b) - a)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent_a": ("LATENT",), "latent_b": ("LATENT",), "op": (["add", "subtract", "multiply", "lerp", "maximum", "minimum"],), "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent_a, latent_b, op, strength):
        a = _s(latent_a); b = _match(a, _s(latent_b)).to(a.device)
        r = {"add": a + b, "subtract": a - b, "multiply": a * b, "lerp": b, "maximum": torch.maximum(a, b), "minimum": torch.minimum(a, b)}[op]
        return (_out(latent_a, a + strength * (r - a)),)

def slerp(a, b, t, eps=1e-6):
    """Spherical interpolation per batch item over all other dims; falls back to lerp when the two are (almost) parallel."""
    af, bf = a.flatten(1).float(), b.flatten(1).float(); an, bn = af / (af.norm(dim=1, keepdim=True) + eps), bf / (bf.norm(dim=1, keepdim=True) + eps)
    dot = (an * bn).sum(1, keepdim=True).clamp(-1 + 1e-7, 1 - 1e-7); om = torch.acos(dot); so = torch.sin(om)
    w_a, w_b = torch.sin((1 - t) * om) / so, torch.sin(t * om) / so; lin = so.abs() < 1e-4
    out = torch.where(lin, (1 - t) * af + t * bf, w_a * af + w_b * bf); return out.view_as(a).to(a.dtype)

class PSN_LatentSlerp:
    """Spherical interpolation between two latents (better than a straight blend for transitions between noise-like latents). t=0 gives a, t=1 gives b."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent_a": ("LATENT",), "latent_b": ("LATENT",), "t": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent_a, latent_b, t):
        a = _s(latent_a); return (_out(latent_a, slerp(a, _match(a, _s(latent_b)).to(a.device), float(t))),)

class PSN_LatentNormalize:
    """Re-scale a latent: 'standardize' (zero mean, unit std per sample), 'match_reference' (mean/std of a reference latent), or 'set_std' (keep the mean, force a standard deviation)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "mode": (["standardize", "match_reference", "set_std"],), "target_std": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 20.0, "step": 0.01}), "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01})}, "optional": {"reference": ("LATENT",)}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, mode, target_std, strength, reference=None):
        x = _s(latent); xf = x.float(); dims = tuple(range(1, x.dim())); m, sd = xf.mean(dims, keepdim=True), xf.std(dims, keepdim=True) + 1e-6
        if mode == "standardize": y = (xf - m) / sd
        elif mode == "set_std": y = (xf - m) / sd * target_std + m
        else:
            if reference is None: raise ValueError("match_reference needs a reference latent")
            r = _match(x, _s(reference)).float().to(xf.device); y = (xf - m) / sd * (r.std(dims, keepdim=True) + 1e-6) + r.mean(dims, keepdim=True)
        return (_out(latent, (xf + strength * (y - xf)).to(x.dtype)),)

class PSN_LatentBatchRepeat:
    """Repeat the whole batch n times (frames or variations)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "times": ("INT", {"default": 2, "min": 1, "max": 256})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, times): x = _s(latent); return (_out(latent, x.repeat(times, *[1] * (x.dim() - 1))),)

class PSN_LatentBatchSlice:
    """Take `count` items starting at `start` (negative start counts from the end). Errors if the slice is empty."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "start": ("INT", {"default": 0, "min": -4096, "max": 4096}), "count": ("INT", {"default": 1, "min": 1, "max": 4096})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, start, count):
        x = _s(latent); s = start if start >= 0 else x.shape[0] + start; y = x[max(s, 0): max(s, 0) + count]
        if y.shape[0] == 0: raise ValueError(f"empty slice of a batch of {x.shape[0]}")
        o = _out(latent, y.clone())
        if "batch_index" in o: o.pop("batch_index")
        return (o,)

class PSN_LatentBatchConcat:
    """Join two batches (b is resized to a's spatial size when needed)."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent_a": ("LATENT",), "latent_b": ("LATENT",)}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent_a, latent_b):
        a = _s(latent_a); b = _s(latent_b)
        if b.shape[1] != a.shape[1]: raise ValueError(f"channel mismatch: {a.shape[1]} vs {b.shape[1]}")
        if b.shape[2:] != a.shape[2:]: b = F.interpolate(b.float(), size=a.shape[2:], mode="trilinear" if a.dim() == 5 else "bilinear", align_corners=False).to(a.dtype)      # resize space only: keep every item of b
        o = _out(latent_a, torch.cat([a, b.to(a.device, a.dtype)], 0)); o.pop("batch_index", None); return (o,)

def structured_noise(like, seed, scale, octaves):
    """Noise with structure: random fields at 1/scale resolution upsampled to full size, `octaves` of them at halving amplitude (smooth blobs instead of white noise)."""
    g = torch.Generator(device="cpu").manual_seed(int(seed)); shape = like.shape; acc = torch.zeros(shape, dtype=torch.float32); amp, total = 1.0, 0.0
    for o in range(octaves):
        sc = max(1, int(scale) // (2 ** o)); small = tuple(max(1, d // sc) for d in shape[2:])
        n = torch.randn((shape[0], shape[1], *small), generator=g)
        acc += amp * (F.interpolate(n, size=shape[2:], mode="trilinear" if len(shape) == 5 else "bilinear", align_corners=False) if small != tuple(shape[2:]) else n); total += amp * amp; amp *= 0.5
    acc = acc / math.sqrt(total); return (acc / (acc.std() + 1e-6)).to(like.device)

class PSN_LatentNoiseInject:
    """Add noise to a latent: white (scale 1) or structured blobs (scale > 1, several octaves). Seeded and repeatable. strength 0 returns the input unchanged."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "seed": ("INT", {"default": 0, "min": 0, "max": 2**63 - 1}), "strength": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 5.0, "step": 0.01}), "scale": ("INT", {"default": 1, "min": 1, "max": 64}), "octaves": ("INT", {"default": 1, "min": 1, "max": 6})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, seed, strength, scale, octaves):
        x = _s(latent); return (_out(latent, x + strength * structured_noise(x, seed, scale, octaves).to(x.dtype)),)

class PSN_LatentTileable:
    """Make a latent tile seamlessly: the left/right (and top/bottom) borders are blended with the content half a tile away, so repeating the image shows no seam. axis: both, x or y."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "axis": (["both", "x", "y"],), "blend": ("FLOAT", {"default": 0.5, "min": 0.05, "max": 1.0, "step": 0.05})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, axis, blend):
        x = _s(latent); y = x.clone()
        for ax_name, dim in (("x", -1), ("y", -2)):
            if axis not in ("both", ax_name): continue
            n = y.shape[dim]; pos = torch.arange(n, device=y.device, dtype=torch.float32); edge = torch.minimum(pos, n - 1 - pos) / max(1.0, blend * n / 2)       # 0 at the border, 1 inside
            w = (1 - edge.clamp(0, 1)); w = (w * w * (3 - 2 * w)).view(*[1] * (y.dim() + dim), n, *[1] * (-dim - 1)).to(y.dtype)       # smoothstep: 1 at the borders
            y = y * (1 - w) + torch.roll(y, n // 2, dims=dim) * w
        return (_out(latent, y),)

class PSN_LatentTemporalSmooth:
    """Calm flicker along time: exponential smoothing over the batch axis (frames) or the T axis of a video latent, then optionally re-anchor mean/std to the first frame so the clip cannot drift."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "smoothing": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 0.99, "step": 0.01}), "anchor_first_frame": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, smoothing, anchor_first_frame):
        x = _s(latent); fdim = 2 if x.dim() == 5 else 0
        if x.shape[fdim] < 2: return (_out(latent, x.clone()),)
        fr = list(x.unbind(fdim)); out = [fr[0]]
        for f in fr[1:]: out.append((1 - smoothing) * f + smoothing * out[-1])
        y = torch.stack(out, fdim)
        if anchor_first_frame:
            dims = tuple(d for d in range(x.dim()) if d != fdim and d != (1 if fdim == 0 else 1)); r = y.index_select(fdim, torch.tensor([0], device=y.device)); a = x.index_select(fdim, torch.tensor([0], device=y.device))
            m0, s0, m1, s1 = a.mean(dims, keepdim=True), a.std(dims, keepdim=True) + 1e-6, y.mean(dims, keepdim=True), y.std(dims, keepdim=True) + 1e-6; y = (y - m1) / s1 * s0 + m0
        return (_out(latent, y.to(x.dtype)),)

class PSN_LatentPatchInject:
    """Paste latent_b into latent_a at (x, y) in latent cells with a feathered edge. For stitching tiles or continuing a long video. The patch is clipped at the borders."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent_a": ("LATENT",), "latent_b": ("LATENT",), "x": ("INT", {"default": 0, "min": -4096, "max": 4096}), "y": ("INT", {"default": 0, "min": -4096, "max": 4096}), "feather": ("INT", {"default": 2, "min": 0, "max": 64}), "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent_a, latent_b, x, y, feather, strength):
        a = _s(latent_a).clone(); b = _s(latent_b).to(a.device, a.dtype)
        if a.shape[1] != b.shape[1]: raise ValueError("channel mismatch")
        bh, bw = b.shape[-2:]; H, W = a.shape[-2:]; x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + bw, W), min(y + bh, H)
        if x1 <= x0 or y1 <= y0: return (_out(latent_a, a),)
        sub = b[..., y0 - y: y1 - y, x0 - x: x1 - x]; h, w = sub.shape[-2:]
        def ramp(n, lo, hi):
            r = torch.ones(n, device=a.device)
            if feather:
                k = torch.arange(n, device=a.device, dtype=torch.float32)
                if lo: r = torch.minimum(r, ((k + 1) / (feather + 1)).clamp(max=1))
                if hi: r = torch.minimum(r, ((n - k) / (feather + 1)).clamp(max=1))
            return r
        m = (ramp(h, y0 > y or y > 0, y1 < y + bh or y1 < H).view(h, 1) * ramp(w, x0 > x or x > 0, x1 < x + bw or x1 < W).view(1, w)).to(a.dtype) * strength
        a[..., y0:y1, x0:x1] = a[..., y0:y1, x0:x1] * (1 - m) + sub * m
        return (_out(latent_a, a),)

class PSN_LatentDirection:
    """Move a latent along a direction learned from examples: direction = mean(positive batch) - mean(negative batch); result = target + strength * direction. Works for 'more of X' edits and for StyleGAN-style directions."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"target": ("LATENT",), "positive": ("LATENT",), "negative": ("LATENT",), "strength": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.05})}}
    RETURN_TYPES = ("LATENT",); FUNCTION = "run"; CATEGORY = CAT
    def run(self, target, positive, negative, strength):
        t = _s(target); p = _match(t[:1], _s(positive).mean(0, keepdim=True)).to(t.device); n = _match(t[:1], _s(negative).mean(0, keepdim=True)).to(t.device)
        return (_out(target, t + strength * (p - n)),)

class PSN_LatentStats:
    """Describe a latent (shape, dtype, mean, std, min, max, NaN/Inf count) as text and JSON; with fail_on_bad=true it stops the workflow when the latent contains NaN/Inf."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"latent": ("LATENT",), "fail_on_bad": ("BOOLEAN", {"default": True})}}
    RETURN_TYPES = ("LATENT", "STRING", "STRING"); RETURN_NAMES = ("latent", "summary", "stats_json"); FUNCTION = "run"; CATEGORY = CAT
    def run(self, latent, fail_on_bad):
        x = _s(latent); xf = x.float(); bad = int((~torch.isfinite(xf)).sum())
        if bad and fail_on_bad: raise ValueError(f"latent contains {bad} NaN/Inf values")
        fin = xf[torch.isfinite(xf)]; st = {"shape": list(x.shape), "dtype": str(x.dtype).replace("torch.", ""), "mean": float(fin.mean()) if fin.numel() else None, "std": float(fin.std()) if fin.numel() > 1 else None, "min": float(fin.min()) if fin.numel() else None, "max": float(fin.max()) if fin.numel() else None, "nan_or_inf": bad}
        return (latent, f"{st['shape']} {st['dtype']} mean {st['mean']:.4f} std {st['std']:.4f} range [{st['min']:.3f}, {st['max']:.3f}] bad {bad}" if fin.numel() > 1 else str(st), json.dumps(st))

NODE_CLASS_MAPPINGS = {c.__name__: c for c in (PSN_LatentMath, PSN_LatentSlerp, PSN_LatentNormalize, PSN_LatentBatchRepeat, PSN_LatentBatchSlice, PSN_LatentBatchConcat, PSN_LatentNoiseInject, PSN_LatentTileable, PSN_LatentTemporalSmooth, PSN_LatentPatchInject, PSN_LatentDirection, PSN_LatentStats)}
for _c in NODE_CLASS_MAPPINGS.values():
    if not hasattr(_c, "RETURN_NAMES"): _c.RETURN_NAMES = ("latent",)       # every single-output node here returns one LATENT
NODE_DISPLAY_NAME_MAPPINGS = {k: "PSN " + k[4:].replace("Latent", "Latent ", 1).replace("  ", " ") for k in NODE_CLASS_MAPPINGS}
