"""The flagship nodes, written for ComfyUI's V3 API (comfy_api.latest). Original code, AGPL-3.0-or-later.

Registration: nodes.py load_custom_node takes NODE_CLASS_MAPPINGS first and only looks at comfy_entrypoint when that is absent, so a pack holding V1 and V3 nodes
lists its V3 classes in NODE_CLASS_MAPPINGS. Every server and execution path branches on the class, so they run as true V3 nodes. A lazy switch is not here because core ships ComfySwitchNode.
The prompt tables are read from studio/goals.py with ast, not imported: goals.py needs fastapi, which a bare ComfyUI need not have, and this way the studio and the nodes cannot drift."""
import ast, functools, hashlib, json, os, re, time
import torch
from comfy_api.latest import ComfyAPI, io, ui

CATEGORY = "Parametric/Flagship"
GOALS_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio", "goals.py")
_WANT = ("CAMERA_MOVES", "SHOTS", "LENSES", "LIGHTING", "MOODS", "CONTINUOUS", "SWAP_PROMPT")
_MINIMAL = {"CAMERA_MOVES": {"locked": "The camera stays locked off on one framing for the whole shot."}, "SHOTS": {"auto": ""}, "LENSES": {"auto": ""}, "LIGHTING": {"auto": ""}, "MOODS": {"auto": ""}, "CONTINUOUS": "One continuous shot, no cuts.", "SWAP_PROMPT": "Replace only {target} in <Video 1> with the character in <Picture 1>."}   # only if studio/ is not shipped

@functools.lru_cache(maxsize=1)
def goal_tables():
    found = {}
    try:
        with open(GOALS_PY, encoding="utf-8") as f: tree = ast.parse(f.read())
        for st in tree.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and getattr(st.targets[0], "id", "") in _WANT:
                try: found[st.targets[0].id] = ast.literal_eval(st.value)
                except ValueError: pass
    except (OSError, SyntaxError): pass
    return {**_MINIMAL, **found}

# ---- Director Prompt: each camera move reveals its own controls. At their defaults the sentence is exactly the one studio/goals.py director_prompt writes.
_SMOOTH = {"slow": "slowly and smoothly", "steady": "smoothly at a steady pace", "fast": "quickly and smoothly"}
_FIXED = {"slow": "slowly", "very_slow": "very slowly", "fast": "quickly"}
_CRANE = {"smooth": "smoothly", "very_slow": "very slowly and smoothly", "fast": "quickly and smoothly"}
_ORBIT = {"pace": {"steady": "at a steady pace", "slow": "at a slow pace", "fast": "at a fast pace"}, "arc": {"quarter": "quarter circle", "half": "half circle", "full": "full circle"}}
MOVE_CONTROLS = {
 "locked": {},
 "dolly_in": {"pace": _SMOOTH}, "dolly_out": {"pace": _SMOOTH}, "crane_up": {"pace": _CRANE}, "crane_down": {"pace": _CRANE},
 "orbit_left": _ORBIT, "orbit_right": _ORBIT,
 "pan_left": {"pace": _FIXED}, "pan_right": {"pace": _FIXED}, "tilt_up": {"pace": _FIXED},
 "tracking": {"speed": {"walking": "walking speed", "drifting": "a slow drifting speed", "running": "running speed"}},
 "handheld": {"sway": {"light": "a light natural sway", "steady": "a barely visible sway", "heavy": "a heavy energetic sway"}},
 "dolly_zoom": {"pace": {"slow": "A slow dolly zoom", "fast": "A fast dolly zoom"}},
}
def camera_sentence(camera):
    """camera is the DynamicCombo dict: {"camera": move, <control>: choice}. A control swaps the phrase its default wrote, so the shared sentence stays the source."""
    move = camera["camera"]; sentence = goal_tables()["CAMERA_MOVES"][move]
    for name, choices in MOVE_CONTROLS.get(move, {}).items():
        choice = camera.get(name)
        if choice in choices: sentence = sentence.replace(next(iter(choices.values())), choices[choice])
        if name == "arc" and choice not in (None, next(iter(choices))): sentence = sentence.replace(", and ends on a side view of the subject in profile", "")   # true of a quarter circle only
    return sentence
def compose_director(idea, camera, shot="auto", lens="auto", lighting="auto", mood="auto"):
    t = goal_tables(); parts = [str(idea or "").strip().rstrip(".") + ".", t["SHOTS"][shot], camera_sentence(camera), t["LENSES"][lens], t["LIGHTING"][lighting], t["MOODS"][mood], t["CONTINUOUS"]]
    return " ".join(p for p in parts if p)

class PSN_DirectorPrompt(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        t = goal_tables(); moves = list(t["CAMERA_MOVES"])
        def option(move):
            return io.DynamicCombo.Option(move, [io.Combo.Input(name, options=list(choices), default=next(iter(choices)), tooltip=f"{name.title()} of this move. The first choice is the wording the studio uses.") for name, choices in MOVE_CONTROLS.get(move, {}).items()])
        return io.Schema(node_id="PSN_DirectorPrompt", display_name="Director Prompt", category=CATEGORY, search_aliases=["camera prompt", "shot prompt", "cinematography"],
            description="Writes a one-camera-move video prompt the way the Studio's Director does: idea, shot size, camera move, lens, light and mood. Pick a move and only that move's controls appear.",
            inputs=[io.String.Input("idea", multiline=True, default="a lighthouse keeper climbs the stairs at dusk", tooltip="What happens in the shot, in plain words."),
                    io.DynamicCombo.Input("camera", options=[option(m) for m in moves], tooltip="One camera move per shot: models follow one clear move far better than several."),
                    io.Combo.Input("shot", options=list(t["SHOTS"]), default="auto", tooltip="Shot size. auto writes nothing."),
                    io.Combo.Input("lens", options=list(t["LENSES"]), default="auto", tooltip="Lens look. auto writes nothing."),
                    io.Combo.Input("lighting", options=list(t["LIGHTING"]), default="auto", tooltip="Light. auto writes nothing."),
                    io.Combo.Input("mood", options=list(t["MOODS"]), default="auto", tooltip="Mood. auto writes nothing.")],
            outputs=[io.String.Output("prompt", display_name="prompt", tooltip="The composed prompt, ready for a text encoder or Shot List.")])
    @classmethod
    def execute(cls, idea, camera, shot, lens, lighting, mood):
        return io.NodeOutput(compose_director(idea, camera, shot, lens, lighting, mood))

# ---- Recast Prompt: the reference tags of the Studio's Recast goal.
def compose_recast(target, direction="", video_ref=1, picture_ref=1):
    text = goal_tables()["SWAP_PROMPT"].format(target=str(target or "").strip() or "the main person")
    text = text.replace("<Video 1>", f"<Video {int(video_ref)}>").replace("<Picture 1>", f"<Picture {int(picture_ref)}>")
    direction = str(direction or "").strip()
    return text + (" " + direction if direction else "")

class PSN_RecastPrompt(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="PSN_RecastPrompt", display_name="Recast Prompt", category=CATEGORY, search_aliases=["character swap prompt", "replace character", "reference tags"],
            description="Writes a character replacement prompt with the reference tags the Studio's Recast goal uses (<Video N>, <Picture N>). Describe the target to replace, not the scene.",
            inputs=[io.String.Input("target", default="the main person", tooltip="Who to replace in the video. Describe the target, not the scene."),
                    io.String.Input("direction", multiline=True, default="", tooltip="Optional extra direction, added at the end."),
                    io.Int.Input("video_ref", default=1, min=1, max=16, tooltip="Which reference video the tag points at."),
                    io.Int.Input("picture_ref", default=1, min=1, max=16, tooltip="Which reference picture the tag points at.")],
            outputs=[io.String.Output("prompt", display_name="prompt", tooltip="The recast prompt."), io.String.Output("reference_tags", display_name="reference_tags", tooltip="The tags used, comma separated.")])
    @classmethod
    def execute(cls, target, direction, video_ref, picture_ref):
        return io.NodeOutput(compose_recast(target, direction, video_ref, picture_ref), f"<Video {int(video_ref)}>,<Picture {int(picture_ref)}>")

# ---- VRAM Gate: the studio's VRAM rule inside any graph.
def memory_state():
    """(free GB, device label). Uses ComfyUI's own accounting: device-wide free memory plus what torch holds unused. On --cpu that is free RAM, and the label says so."""
    import comfy.model_management as mm
    dev = mm.get_torch_device()
    return mm.get_free_memory(dev) / 1024 ** 3, ("RAM (no GPU)" if mm.cpu_mode() else str(dev))
def gate_reason(free_gb, peak_gb, margin_gb, device):
    return f"Not enough free memory on {device}: {free_gb:.1f} GB free, this step needs {peak_gb:.1f} GB plus the {margin_gb:.1f} GB margin ({peak_gb + margin_gb:.1f} GB). Nothing downstream ran. Free some memory or lower peak_gb."

class PSN_VRAMGate(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        t = io.MatchType.Template("value")
        return io.Schema(node_id="PSN_VRAMGate", display_name="VRAM Gate", category=CATEGORY, search_aliases=["memory gate", "oom guard", "free vram check"],
            description="Passes its input through only when free VRAM covers this step's peak plus a safety margin; otherwise everything downstream stops with a plain reason instead of an out-of-memory crash. Works with any type.",
            inputs=[io.MatchType.Input("value", template=t, tooltip="Anything: passed through unchanged when the gate is open."),
                    io.Float.Input("peak_gb", default=8.0, min=0.0, max=1000000.0, step=0.5, tooltip="The most memory the next step will use, in GB."),
                    io.Float.Input("margin_gb", default=4.0, min=0.0, max=1000.0, step=0.5, tooltip="Memory to keep free on top of the peak, in GB."),
                    io.Boolean.Input("free_idle_models", default=True, tooltip="When short, first unload models this ComfyUI holds idle, then measure again. Never touches other programs.")],
            outputs=[io.MatchType.Output(template=t, display_name="value", tooltip="The input, unchanged."), io.Float.Output("free_gb", display_name="free_gb", tooltip="Free memory measured, in GB."), io.String.Output("status", display_name="status", tooltip="What the gate saw, in one line.")])
    @classmethod
    def fingerprint_inputs(cls, peak_gb=None, margin_gb=None, **kwargs):
        # Memory changes between runs, so the check always runs; an open gate reports a constant, so a passing gate does not make the render below it run again. A closed gate never reuses its result: it must say why every time.
        try:
            free, _ = memory_state()
            return "open" if free >= float(peak_gb) + float(margin_gb) else time.time()
        except Exception: return float("nan")
    @classmethod
    def execute(cls, value, peak_gb, margin_gb, free_idle_models):
        import comfy.model_management as mm
        free, device = memory_state(); need = peak_gb + margin_gb; freed = ""
        if free < need and free_idle_models:
            mm.free_memory(int(need * 1024 ** 3), mm.get_torch_device()); after, device = memory_state()
            if after > free: freed = f" after unloading idle models (was {free:.1f} GB)"
            free = after
        if free < need: return io.NodeOutput(None, None, None, block_execution=gate_reason(free, peak_gb, margin_gb, device))   # args must be non-empty: execution.py only applies the blocker when NodeOutput has a result
        return io.NodeOutput(value, free, f"Open: {free:.1f} GB free on {device}{freed}, need {need:.1f} GB.")

# ---- Shot List: one render subgraph per shot, concatenated. Measured: with --cache-classic, changing one shot renders only that shot and the join. ComfyUI's default RAM-pressure cache rendered all of them again on the author's box; the cause is not confirmed.
def wrap_text(text, width):
    words, lines, line = str(text).split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width and line: lines.append(line); line = w
        else: line = (line + " " + w).strip()
    return lines + [line] if line else lines

class PSN_ShotCard(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="PSN_ShotCard", display_name="Shot Card", category=CATEGORY, search_aliases=["storyboard card", "title card"],
            description="Draws a shot's text on a plain card, on the CPU with no model. Shot List uses it for a free storyboard pass before spending GPU time.",
            inputs=[io.String.Input("text", multiline=True, default="", tooltip="The shot text."), io.Int.Input("number", default=1, min=0, max=9999, tooltip="The shot number on the card."),
                    io.Int.Input("width", default=512, min=64, max=4096, step=8, tooltip="Card width in pixels."), io.Int.Input("height", default=288, min=64, max=4096, step=8, tooltip="Card height in pixels.")],
            outputs=[io.Image.Output("image", display_name="image", tooltip="The card.")])
    @classmethod
    def execute(cls, text, number, width, height):
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGB", (width, height), (22, 22, 24)); d = ImageDraw.Draw(im); s = max(10, height // 18); pad = s
        d.rectangle([0, 0, width - 1, height - 1], outline=(201, 162, 39), width=max(1, s // 6))
        d.text((pad, pad), f"SHOT {number}", fill=(201, 162, 39), font=ImageFont.load_default(int(s * 1.4)))
        font = ImageFont.load_default(s); y = pad + int(s * 2.2)
        for line in wrap_text(text, max(8, int((width - 2 * pad) / (s * 0.52)))):
            if y + s > height - pad: break
            d.text((pad, y), line, fill=(232, 232, 228), font=font); y += int(s * 1.3)
        return io.NodeOutput(torch.from_numpy(np.asarray(im, dtype=np.float32).copy() / 255.0)[None])

BATCH_LIMIT = 50   # BatchImagesNode's Autogrow maximum
def build_shot_graph(graph, shots, render):
    """Adds one subgraph per shot to a GraphBuilder and returns the link of the concatenated images. render is the DynamicCombo dict."""
    outs, mode = [], render["render"]
    for i, text in enumerate(shots):
        if mode == "storyboard": outs.append(graph.node("PSN_ShotCard", text=text, number=i + 1, width=render["width"], height=render["height"]).out(0)); continue
        clip, width, height = render["clip"], render["width"], render["height"]
        pos, neg = graph.node("CLIPTextEncode", text=text, clip=clip), graph.node("CLIPTextEncode", text=render["negative"], clip=clip)
        latent = graph.node("EmptyLatentImage", width=width, height=height, batch_size=1)
        sampled = graph.node("KSampler", model=render["model"], seed=render["seed"] + i, steps=render["steps"], cfg=render["cfg"], sampler_name=render["sampler_name"], scheduler=render["scheduler"], positive=pos.out(0), negative=neg.out(0), latent_image=latent.out(0), denoise=1.0)
        outs.append(graph.node("VAEDecode", samples=sampled.out(0), vae=render["vae"]).out(0))
    return outs[0] if len(outs) == 1 else graph.node("BatchImagesNode", **{f"images.image{i}": o for i, o in enumerate(outs)}).out(0)

class PSN_ShotList(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        import comfy.samplers
        return io.Schema(node_id="PSN_ShotList", display_name="Shot List", category=CATEGORY, enable_expand=True, search_aliases=["storyboard", "multi shot", "scene list", "batch prompts"],
            description="Connect any number of shot prompts. When it runs, this node turns itself into one render graph per shot and joins the results, so ComfyUI runs and tracks each shot as its own node. Storyboard draws cards on the CPU and needs no model.",
            inputs=[io.Autogrow.Input("shots", template=io.Autogrow.TemplatePrefix(io.String.Input("shot", force_input=True, tooltip="One shot prompt."), prefix="shot_", min=1, max=BATCH_LIMIT), tooltip="Shot prompts, in order."),
                    io.DynamicCombo.Input("render", tooltip="storyboard draws a card for each shot on the CPU. sampler renders each shot with your model.", options=[
                        io.DynamicCombo.Option("storyboard", [io.Int.Input("width", default=512, min=64, max=4096, step=8, tooltip="Image width."), io.Int.Input("height", default=288, min=64, max=4096, step=8, tooltip="Image height.")]),
                        io.DynamicCombo.Option("sampler", [io.Model.Input("model", raw_link=True, tooltip="The model for every shot."), io.Clip.Input("clip", raw_link=True, tooltip="The text encoder for every shot."), io.Vae.Input("vae", raw_link=True, tooltip="The VAE for every shot."),
                            io.String.Input("negative", multiline=True, default="", tooltip="Negative prompt for every shot."), io.Int.Input("width", default=1024, min=64, max=8192, step=8, tooltip="Image width."), io.Int.Input("height", default=576, min=64, max=8192, step=8, tooltip="Image height."),
                            io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True, tooltip="Seed of the first shot; each next shot adds one."), io.Int.Input("steps", default=20, min=1, max=1000, tooltip="Sampling steps."), io.Float.Input("cfg", default=7.0, min=0.0, max=100.0, step=0.1, tooltip="Guidance scale."),
                            io.Combo.Input("sampler_name", options=list(comfy.samplers.KSampler.SAMPLERS), default="euler", tooltip="Sampler."), io.Combo.Input("scheduler", options=list(comfy.samplers.KSampler.SCHEDULERS), default="normal", tooltip="Noise schedule.")])])],
            outputs=[io.Image.Output("images", display_name="images", tooltip="Every shot, in order, as one image batch."), io.Int.Output("shot_count", display_name="shot_count", tooltip="How many shots ran."), io.String.Output("shot_prompts", display_name="shot_prompts", tooltip="The shot prompts, one per line.")])
    @classmethod
    def execute(cls, shots, render):
        from comfy_execution.graph_utils import GraphBuilder
        keys = sorted((k for k, v in shots.items() if v is not None), key=lambda k: int(re.sub(r"\D", "", k) or 0)); texts = [str(shots[k]) for k in keys]
        if not texts: raise ValueError("Shot List needs at least one connected shot.")
        graph = GraphBuilder(); images = build_shot_graph(graph, texts, render)
        return io.NodeOutput(images, len(texts), "\n".join(texts), expand=graph.finalize())

# ---- Latent Inspector: see what a sampler is really working on.
def latent_frame(samples, batch_index=0, frame=0):
    """One [C, H, W] float tensor on the CPU out of a 4D image latent or 5D video latent."""
    if getattr(samples, "is_nested", False): samples = samples.unbind()[0]
    x = samples.detach().float().cpu()
    if x.ndim == 3: x = x[None]
    x = x[min(batch_index, x.shape[0] - 1)]
    if x.ndim == 4: x = x[:, min(frame, x.shape[1] - 1)]
    return x
def channel_stats(x):
    """Per-channel numbers, plus lag-1 spatial correlation: near 0 is noise, high means a picture is forming."""
    rows = []
    for c in range(x.shape[0]):
        ch = x[c]; mean, std = ch.mean().item(), ch.std(unbiased=False).item(); corr = 0.0
        if std > 1e-8 and ch.shape[1] > 1:
            z = (ch - mean) / std; corr = (z[:, :-1] * z[:, 1:]).mean().item()
        rows.append({"channel": c, "mean": mean, "std": std, "min": ch.min().item(), "max": ch.max().item(), "corr": corr})
    return rows
def read_stats(rows):
    corr = sum(r["corr"] for r in rows) / len(rows); std = sum(r["std"] for r in rows) / len(rows)
    if std < 1e-6: return "Reading: flat. Every value is the same, as in an empty latent before noise is added."
    if abs(corr) < 0.1: return f"Reading: this looks like pure noise (neighbour correlation {corr:.2f}). Nothing has been denoised yet."
    if corr < 0.5: return f"Reading: part way (neighbour correlation {corr:.2f}). Structure is coming out of the noise."
    return f"Reading: structured (neighbour correlation {corr:.2f}). Neighbouring values agree, so a picture has formed."
def stats_text(rows, shape):
    head = [f"Latent {list(shape)}: {len(rows)} channels", "ch      mean       std       min       max      corr"]
    return "\n".join(head + [f"{r['channel']:>2} {r['mean']:>9.3f} {r['std']:>9.3f} {r['min']:>9.3f} {r['max']:>9.3f} {r['corr']:>9.3f}" for r in rows] + [read_stats(rows)])
def _norm(t, lo=None, hi=None):
    lo = t.min() if lo is None else lo; hi = t.max() if hi is None else hi
    return ((t - lo) / (hi - lo)).clamp(0, 1) if float(hi - lo) > 1e-8 else torch.zeros_like(t)
def channel_grid(x, columns=0, per_channel=True):
    """All channels side by side, grey, as [H, W, 3]. Dark gaps separate the cells."""
    n, h, w = x.shape; cols = columns if columns > 0 else max(1, round(n ** 0.5)); rows = -(-n // cols)
    grid = torch.zeros(rows * (h + 1) - 1, cols * (w + 1) - 1); lo, hi = (None, None) if per_channel else (x.min(), x.max())
    for i in range(n):
        r, c = divmod(i, cols); grid[r * (h + 1):r * (h + 1) + h, c * (w + 1):c * (w + 1) + w] = _norm(x[i], lo, hi)
    return grid[..., None].repeat(1, 1, 3)
def pca_rgb(x, clip_percent=1.0):
    """The three strongest directions of all channels as red, green and blue, each stretched between its percentiles. A 1 or 2 channel latent fills what it can."""
    c, h, w = x.shape; flat = x.reshape(c, -1).T; flat = flat - flat.mean(0, keepdim=True)
    if not flat.abs().sum() > 0: return torch.zeros(h, w, 3)
    _, _, v = torch.linalg.svd(flat if flat.shape[0] < 20000 else flat[torch.linspace(0, flat.shape[0] - 1, 20000).long()], full_matrices=False)
    comps = flat @ v[:3].T; out = []
    for i in range(comps.shape[1]):
        p = comps[:, i]; sign = 1.0 if p.abs().max() == p.max() else -1.0; p = p * sign   # fixed sign: the same latent always gets the same colours
        lo, hi = torch.quantile(p, clip_percent / 100.0), torch.quantile(p, 1.0 - clip_percent / 100.0); out.append(_norm(p, lo, hi))
    while len(out) < 3: out.append(torch.zeros_like(out[0]))
    return torch.stack(out, -1).reshape(h, w, 3)
def histogram_panel(x, bins=64, cell=(96, 200)):
    """One bar chart per channel over a shared range, with a marker at zero, as [H, W, 3]."""
    n = x.shape[0]; ch, cw = cell; cols = max(1, round(n ** 0.5)); rows = -(-n // cols); lo, hi = x.min().item(), x.max().item(); hi = hi if hi > lo else lo + 1.0
    img = torch.full((rows * (ch + 2), cols * (cw + 2), 3), 0.09)
    for i in range(n):
        counts = torch.histc(x[i], bins=bins, min=lo, max=hi); bars = (counts / counts.max().clamp(min=1) * (ch - 1)).long(); top, left = divmod(i, cols)[0] * (ch + 2), divmod(i, cols)[1] * (cw + 2); bw = cw / bins
        for b in range(bins):
            x0, x1 = left + int(b * bw), left + max(int((b + 1) * bw), int(b * bw) + 1)
            if bars[b] > 0: img[top + ch - int(bars[b]):top + ch, x0:x1] = torch.tensor([0.79, 0.64, 0.15])
        if lo < 0 < hi: zx = left + int((0 - lo) / (hi - lo) * (cw - 1)); img[top:top + ch, zx] = torch.tensor([0.25, 0.75, 0.45])
    return img
def upscale(img, scale):
    return img if scale <= 1 else img.repeat_interleave(scale, 0).repeat_interleave(scale, 1)

class PSN_LatentInspector(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="PSN_LatentInspector", display_name="Latent Inspector", category=CATEGORY, search_aliases=["latent preview", "latent debug", "pca", "latent histogram", "teach diffusion"],
            description="Shows what a sampler is working on, with no VAE: every channel, the three strongest directions as colour, or a histogram per channel. The stats output gives each channel's numbers and a plain reading: noise, part way or structured. Compare it before and after a sampler.",
            inputs=[io.Latent.Input("latent", tooltip="Any image or video latent."),
                    io.DynamicCombo.Input("view", tooltip="What to draw.", options=[
                        io.DynamicCombo.Option("channel_grid", [io.Int.Input("columns", default=0, min=0, max=64, tooltip="Cells per row. 0 picks a square grid."), io.Boolean.Input("per_channel", default=True, tooltip="Stretch each channel on its own. Off shares one range, so strong and weak channels can be compared."), io.Int.Input("scale", default=4, min=1, max=16, tooltip="Image pixels per latent pixel.")]),
                        io.DynamicCombo.Option("pca_rgb", [io.Float.Input("clip_percent", default=1.0, min=0.0, max=20.0, step=0.5, tooltip="Percent trimmed from each end before stretching the colours."), io.Int.Input("scale", default=8, min=1, max=16, tooltip="Image pixels per latent pixel. 8 is the usual VAE size.")]),
                        io.DynamicCombo.Option("histogram", [io.Int.Input("bins", default=64, min=8, max=256, tooltip="Bars per channel. All channels share one range; the green line marks zero.")])]),
                    io.Int.Input("batch_index", default=0, min=0, max=4096, tooltip="Which item of the batch to inspect."), io.Int.Input("frame", default=0, min=0, max=100000, tooltip="Which frame of a video latent to inspect. Ignored for images.")],
            outputs=[io.Image.Output("view", display_name="view", tooltip="The picture."), io.String.Output("stats", display_name="stats", tooltip="Per-channel mean, std, min, max and neighbour correlation, with a plain reading.")])
    @classmethod
    async def execute(cls, latent, view, batch_index, frame):
        x = latent_frame(latent["samples"], batch_index, frame); mode = view["view"]; rows = channel_stats(x)
        if mode == "channel_grid": image = upscale(channel_grid(x, view["columns"], view["per_channel"]), view["scale"])
        elif mode == "pca_rgb": image = upscale(pca_rgb(x, view["clip_percent"]), view["scale"])
        else: image = histogram_panel(x, view["bins"])
        image = image[None].clamp(0, 1)
        await _progress(1, 1, image)
        return io.NodeOutput(image, stats_text(rows, latent["samples"].shape), ui=ui.PreviewImage(image, cls=cls))
async def _progress(value, total, image=None):
    try: await ComfyAPI().execution.set_progress(value, total, preview_image=image)
    except (ValueError, RuntimeError, AttributeError): pass   # outside a running prompt there is no node to report to

# ---- Graph Proof: what made this picture, in a file beside it.
_SECRET = re.compile(r"(api[_-]?key|token|secret|password|credential|authorization)", re.I)
def redact(value, key=""):
    if isinstance(value, dict): return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list): return [redact(v, key) for v in value]
    return "[redacted]" if key and isinstance(value, str) and value and _SECRET.search(str(key)) else value
def clean_graph(prompt):
    """What ran: each node's class and inputs, secrets redacted. Drops the title and the is_changed value execution.py writes into the prompt, or a clock-based IS_CHANGED anywhere in the graph would change the hash on every run."""
    return redact({nid: {"class_type": n.get("class_type"), "inputs": n.get("inputs") or {}} for nid, n in (prompt or {}).items() if isinstance(n, dict)})
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
def graph_hash(graph): return hashlib.sha256(canonical(graph).encode("utf-8")).hexdigest()
def settings_of(graph):
    """Each node's class and its own values, without the links: the settings a person would read."""
    return {nid: {"class_type": n.get("class_type"), "values": {k: v for k, v in (n.get("inputs") or {}).items() if not (isinstance(v, list) and len(v) == 2 and isinstance(v[0], str))}} for nid, n in graph.items() if isinstance(n, dict)}
def verify_proof(path):
    """True when the graph in a proof file still hashes to the hash it records."""
    with open(path, encoding="utf-8") as f: doc = json.load(f)
    return graph_hash(doc["graph"]) == doc["graph_sha256"]

class PSN_GraphProof(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="PSN_GraphProof", display_name="Graph Proof", category=CATEGORY, is_output_node=True, hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo, io.Hidden.unique_id], search_aliases=["provenance", "reproducibility", "graph hash", "settings sidecar"],
            description="Writes a JSON file beside your output: a SHA-256 of the exact graph that ran, every node's settings and a hash of the pixels. The same graph always gives the same hash, so anyone can check a result. Values under names like api_key are redacted first. Nothing leaves this machine.",
            inputs=[io.String.Input("filename_prefix", default="proof/ParametricStudio", tooltip="Where to write it, inside the output folder."),
                    io.Image.Input("images", optional=True, tooltip="Optional: the images this graph made, so their pixels are hashed too."),
                    io.String.Input("note", optional=True, multiline=True, default="", tooltip="Optional note stored in the file.")],
            outputs=[io.String.Output("graph_sha256", display_name="graph_sha256", tooltip="SHA-256 of the graph."), io.String.Output("proof_path", display_name="proof_path", tooltip="The file written.")])
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float("nan")   # fingerprint_inputs is not given the graph, so a change elsewhere in the graph could not be seen: always write
    @classmethod
    def execute(cls, filename_prefix, images=None, note=""):
        import folder_paths
        graph = clean_graph(cls.hidden.prompt if cls.hidden else None); digest = graph_hash(graph); out_dir = folder_paths.get_output_directory()
        folder, base, _, sub, _ = folder_paths.get_save_image_path(filename_prefix, out_dir); os.makedirs(folder, exist_ok=True)
        extra = (cls.hidden.extra_pnginfo if cls.hidden else None) or {}
        doc = {"format": "parametric-studio.graph-proof/1", "graph_sha256": digest, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "node_count": len(graph), "note": note or "", "workflow_included": "workflow" in extra, "settings": settings_of(graph), "graph": graph}
        if images is not None: doc["pixels"] = {"sha256": hashlib.sha256(images.detach().cpu().numpy().tobytes()).hexdigest(), "shape": list(images.shape)}
        path = os.path.join(folder, f"{base}_{digest[:12]}.proof.json")
        with open(path, "w", encoding="utf-8") as f: json.dump(doc, f, indent=1, ensure_ascii=False, default=str)
        rel = os.path.join(sub, os.path.basename(path)) if sub else os.path.basename(path)
        return io.NodeOutput(digest, rel, ui=ui.PreviewText(f"{digest}\n{rel}"))

NODES = [PSN_VRAMGate, PSN_DirectorPrompt, PSN_RecastPrompt, PSN_ShotList, PSN_ShotCard, PSN_LatentInspector, PSN_GraphProof]
NODE_CLASS_MAPPINGS = {c.__name__: c for c in NODES}
NODE_DISPLAY_NAME_MAPPINGS = {"PSN_VRAMGate": "VRAM Gate", "PSN_DirectorPrompt": "Director Prompt", "PSN_RecastPrompt": "Recast Prompt", "PSN_ShotList": "Shot List", "PSN_ShotCard": "Shot Card", "PSN_LatentInspector": "Latent Inspector", "PSN_GraphProof": "Graph Proof"}
