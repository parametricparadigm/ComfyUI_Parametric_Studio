"""One ComfyUI instance per model family. Each instance is a generated directory (own port, own model view, own custom-node set, own output/input/user folders) started on demand through
a systemd user template unit, gated by a VRAM check, and stopped when idle. Nothing here starts a server by itself on import; generate() only writes files. Original code.
Layout:  $INSTANCES_ROOT/<slug>/{instance.json, extra_model_paths.yaml, custom_nodes/, output/, input/, user/}   registry.json keeps the ports stable.
CLI:  python3 -m psn.instances generate [family...] | list | status | start FAMILY | stop FAMILY | reap [minutes]"""
import json, os, re, subprocess, sys, time, urllib.request
from psn import paths

MODELS = paths.setting("PSN_MODELS_ROOT", "STUDIO_MODELS_ROOT", default=paths.home("ComfyUI", "models"))
INSTANCES = paths.setting("PSN_INSTANCES_ROOT", default=paths.home(".local", "share", "parametric-studio", "family_instances"))
COMFY_DIR = paths.setting("PSN_COMFY_DIR", default=paths.home("ComfyUI"))
PS_NODES = paths.setting("PSN_CUSTOM_NODES", default=os.path.join(COMFY_DIR, "custom_nodes"))
LAUNCH = paths.setting("PSN_LAUNCH", default=os.path.join(COMFY_DIR, "launch.sh"))
BASE_PORT, FLOOR_GB = 8600, 4.0
TYPES = ["checkpoints", "diffusion_models", "unet", "text_encoders", "clip", "clip_vision", "vae", "loras", "controlnet", "upscale_models", "embeddings", "style_models", "audio_encoders", "vae_approx",
         "ipadapter", "configs", "model_patches", "latent_upscale_models", "frame_interpolation", "optical_flow", "detection", "geometry_estimation"]
COMMON_PACKS = ["comfyui_parametric_studio", "kijai__ComfyUI-KJNodes"]
REPO_LIB = paths.setting("PSN_REPO_LIB", default=paths.home("nodepack_library", "repos"))
FAMILY_PACKS = {"PartCrafter": ["tungthedev__ComfyUI-TripoSG"], "LTX-2.5": ["Lightricks__ComfyUI-LTXVideo"], "Wan2.1": ["kijai__ComfyUI-WanVideoWrapper"], "Wan2.2": ["kijai__ComfyUI-WanVideoWrapper"], "Wan2.2-Animate": ["kijai__ComfyUI-WanVideoWrapper"],
                "Wan2.2-Dancer": ["kijai__ComfyUI-WanVideoWrapper"], "TurboWan2.2-I2V": ["kijai__ComfyUI-WanVideoWrapper"], "Wan-SCAIL-2": ["kijai__ComfyUI-WanVideoWrapper"],
                "MiniMax-H3": ["Larryvrh__ComfyUI-MiniMax-H3-Turbo", "TripleHeadedMonkey__ComfyUI-MiniMaxH3_LatentUpscaler", "T8mars__comfyui-minimax-h3-audio-T8", "vizart-vj__ComfyUI-MiniMax-H3-LongMedia", "YJX-Research__comfyui-controlfoley-official"],
                "SeedVR2": ["bbaudio-2025__Comfyui-MMH3-UltimateUpscale"]}                                      # a pack is its directory name, owner__Repo: a bare repo name never resolves (MiniMax-H3 once got no packs that way)
ALIASES = {"LTX-2.5": ["ltx 2.5", "ltx"], "Flux.3-Klein": ["flux3-klein", "flux3_klein"], "Flux.1": ["flux"], "Flux.2": ["flux2"], "Qwen-Image-2.1": ["qwen-image", "qwen_image"], "Wan2.2": ["wan2.2"], "Wan2.1": ["wan2.1"]}

# Families whose weights are not laid out the way ComfyUI's loaders expect. Each file is shown to the instance under a loader-friendly name through a symlink view (instance/models/<type>/<name>).
# loader: "core" = ComfyUI's own loaders read it (verified by a CPU load test); "core+psn" = needs one of our loader nodes (psn_nodes/loaders.py); "needs-pack" = no loader exists here yet (files are linked, not claimed loadable).
WRAPS = {
 "PixArt-Sigma": {"loader": "core", "files": [("diffusion_models", "pixart-sigma_transformer.safetensors", "_complete_pipelines/PixArt-Sigma/diffusers/diffusion_pytorch_model.safetensors"),
                  ("text_encoders", "t5xxl_fp16.safetensors", "_complete_pipelines/Flux.1/text_encoders/t5xxl_fp16.safetensors"), ("vae", "sdxl_vae.safetensors", "vae/SDXL/sdxl_vae.safetensors")],
                  "note": "diffusers transformer shown as a diffusion model; the T5-XXL encoder and the SDXL VAE are shared from the library (the folder holds neither)"},
 "LDM3D-4C": {"loader": "core+psn", "files": [("diffusion_models", "ldm3d-4c_unet.safetensors", "_complete_pipelines/LDM3D-4C/pipeline/unet/diffusion_pytorch_model.safetensors"),
              ("text_encoders", "ldm3d-4c_text_encoder.safetensors", "_complete_pipelines/LDM3D-4C/pipeline/text_encoder/model.safetensors"), ("vae", "ldm3d-4c_vae.safetensors", "_complete_pipelines/LDM3D-4C/pipeline/vae/diffusion_pytorch_model.safetensors")],
              "note": "RGB-D model: load the VAE with PSN_VAELoaderChannels (4 colour channels) and split the result with PSN_RGBDSplit"},
 "Hunyuan3D-2.1": {"loader": "core", "files": [("checkpoints", "hunyuan_3d_v2.1.safetensors", "checkpoints/3d/hunyuan_3d_v2.1.safetensors")],
                   "note": "the converted single-file checkpoint; the raw HF repo folder (.ckpt files, paint pipeline) is not read by ComfyUI"},
 "PartCrafter": {"loader": "pack", "files": [("diffusion_models", "partcrafter_transformer.safetensors", "_complete_pipelines/PartCrafter/pipeline/transformer/diffusion_pytorch_model.safetensors"),
                 ("clip_vision", "partcrafter_dinov2.safetensors", "_complete_pipelines/PartCrafter/pipeline/image_encoder_dinov2/model.safetensors"), ("vae", "partcrafter_vae.safetensors", "_complete_pipelines/PartCrafter/pipeline/vae/diffusion_pytorch_model.safetensors")],
                 "note": "core ComfyUI cannot detect this model; its nodes come from the ComfyUI-TripoSG pack (PartCrafter module, import-tested with this venv); original source: wgsxm/PartCrafter"},
 "Stable-Fast-3D": {"loader": "needs-pack", "files": [("checkpoints", "stable-fast-3d_model.safetensors", "_complete_pipelines/Stable-Fast-3D/pipeline/model.safetensors")],
                    "note": "core ComfyUI cannot detect this model; it needs the Stable-Fast-3D inference code wrapped as nodes"},
}

def slug(family): return re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")
def families(models=None):
    cp = os.path.join(models or MODELS, "_complete_pipelines"); return sorted(d for d in os.listdir(cp) if not d.startswith("_") and os.path.isdir(os.path.join(cp, d)))

def _aliases(family): return [family.lower(), family.lower().replace(".", "_"), family.lower().replace("-", "_"), family.lower().replace("-", " ")] + ALIASES.get(family, [])

def model_dirs(family, models=None):
    """type -> relative folders (to the model root) that belong to this family: its own pipeline folder plus top-level type folders named after it."""
    root, out = models or MODELS, {}
    for t in TYPES:
        paths = []
        if os.path.isdir(f"{root}/_complete_pipelines/{family}/{t}"): paths.append(f"_complete_pipelines/{family}/{t}")
        for a in dict.fromkeys(_aliases(family)):
            if os.path.isdir(f"{root}/{t}/{a}"): paths.append(f"{t}/{a}")
        if paths: out[t] = paths
    return out

def vram_estimate_gb(family, models=None):
    """Working-set estimate: largest main model + largest text encoder + largest VAE, +15% for activations. A planning number, not a measurement."""
    root, tot = models or MODELS, 0.0
    for kinds in (("diffusion_models", "checkpoints", "unet"), ("text_encoders", "clip"), ("vae",)):
        best = 0
        for t in kinds:
            for rel in model_dirs(family, root).get(t, []):
                for dp, _, fs in os.walk(os.path.join(root, rel), followlinks=True):
                    for f in fs:
                        try: best = max(best, os.path.getsize(os.path.join(dp, f)))
                        except OSError: pass
        tot += best
    for kinds in (("diffusion_models", "checkpoints", "unet"), ("text_encoders", "clip"), ("vae",)):                       # wrapped files that sit outside the family folder
        w = [os.path.getsize(os.path.join(root, rel)) for t, _, rel in (WRAPS.get(family) or {}).get("files", []) if t in kinds and os.path.exists(os.path.join(root, rel))]
        if w and max(w) > 0 and not any(model_dirs(family, root).get(t) for t in kinds): tot += max(w)
    return round(tot * 1.15 / 1e9, 1)

def registry_ports(fams, root=None):
    p = os.path.join(root or INSTANCES, "registry.json"); reg = json.load(open(p)) if os.path.exists(p) else {}
    nxt = max([BASE_PORT - 1] + list(reg.values())) + 1
    for f in fams:
        if f not in reg: reg[f] = nxt; nxt += 1
    os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(reg, open(p, "w"), indent=1, sort_keys=True); return reg

def apply_theme(inst_dir):
    """Black, gold and green ComfyUI for this instance (the same merge as scripts/apply_theme.py; other settings are kept). Skipped quietly when the palette file is not there."""
    pal = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio", "theme", "parametric_palette.json"); f = os.path.join(inst_dir, "user", "default", "comfy.settings.json")
    try: palette = json.load(open(pal))
    except (OSError, ValueError): return None
    os.makedirs(os.path.dirname(f), exist_ok=True)
    try: cur = json.load(open(f))
    except (OSError, ValueError): cur = {}
    if cur.get("Comfy.ColorPalette") == "custom_parametric" and (cur.get("Comfy.CustomColorPalettes") or {}).get("parametric") == palette: return f
    cur.setdefault("Comfy.CustomColorPalettes", {})["parametric"] = palette; cur["Comfy.ColorPalette"] = "custom_parametric"; _write(f, json.dumps(cur, indent=2)); return f

def _write(path, text):
    """Replace a generated file atomically: a start that reads instance.env while it is being regenerated sees the old file or the new one, never half of it."""
    tmp = path + ".tmp"; open(tmp, "w").write(text); os.replace(tmp, path)

def generate(family, models=None, root=None, ps_nodes=None, ports=None):
    """Write (or refresh) one instance directory. Returns its instance.json dict. Existing output/input/user folders are kept."""
    root, ps_nodes = root or INSTANCES, ps_nodes or PS_NODES; s = slug(family); d = os.path.join(root, s); md = model_dirs(family, models)
    for sub in ("custom_nodes", "output", "input", "user"): os.makedirs(os.path.join(d, sub), exist_ok=True)
    wanted = COMMON_PACKS + FAMILY_PACKS.get(family, []); linked, absent = [], []
    cn = os.path.join(d, "custom_nodes")
    for e in os.listdir(cn):
        if os.path.islink(os.path.join(cn, e)): os.unlink(os.path.join(cn, e))
    for p in wanted:
        src = os.path.join(ps_nodes, p)
        if not os.path.exists(src): src = os.path.join(REPO_LIB, p)          # a family pack that is not installed in the main instance comes from the library of cloned repos (linked into this instance only)
        if os.path.exists(src): os.symlink(os.path.realpath(src), os.path.join(cn, p)); linked.append(p)
        else: absent.append(p)
    views, wrapped, missing_w = {}, [], []
    spec = WRAPS.get(family)
    if spec:
        import shutil; vroot = os.path.join(d, "models"); shutil.rmtree(vroot, ignore_errors=True)
        for t, name, rel in spec["files"]:
            src = os.path.join(models or MODELS, rel)
            if os.path.exists(src): os.makedirs(os.path.join(vroot, t), exist_ok=True); os.symlink(os.path.realpath(src), os.path.join(vroot, t, name)); views.setdefault(t, os.path.join(vroot, t)); wrapped.append(f"{t}/{name}")
            else: missing_w.append(rel)
    lines = [f"# generated by psn.instances for {family}: this instance sees only this family's models", f"{s}:", f"    base_path: {models or MODELS}"]
    for t in dict.fromkeys(list(md) + list(views)): lines += [f"    {t}: |"] + [f"        {x}" for x in md.get(t, []) + ([views[t]] if t in views else [])]
    _write(os.path.join(d, "extra_model_paths.yaml"), "\n".join(lines) + "\n")
    port = (ports or registry_ports([family], root))[family]
    # ComfyUI reads only the yaml beside its main.py (the shared library list, which lacks folders added later) and the files named by --extra-model-paths-config: without this flag the instance's own yaml was never loaded
    # and a family whose folders were missing from the shared list could not see its own weights (HunyuanDiT-1.2, Stable-Cascade ...). The shared list is still read, so shared encoders and VAEs stay resolvable.
    args = ["--base-directory", d, "--output-directory", os.path.join(d, "output"), "--input-directory", os.path.join(d, "input"), "--user-directory", os.path.join(d, "user"), "--extra-model-paths-config", os.path.join(d, "extra_model_paths.yaml")]
    info = {"family": family, "slug": s, "port": port, "est_vram_gb": vram_estimate_gb(family, models), "model_types": {t: len(v) for t, v in md.items()}, "packs": linked, "packs_not_installed": absent, "args": args,
            "launch": LAUNCH, "unit": f"comfy-family@{s}.service", "loader": (spec or {}).get("loader", "core"), "wrapped": wrapped, "wrap_missing": missing_w, "note": (spec or {}).get("note", "")}
    apply_theme(d)
    _write(os.path.join(d, "instance.json"), json.dumps(info, indent=1)); _write(os.path.join(d, "instance.env"), f"PS_PORT={port}\nARGS={' '.join(args)}\n"); return info

UNIT = """[Unit]
Description=ComfyUI instance for model family %i (on demand; started by psn.instances, never enabled)
[Service]
Type=simple
WorkingDirectory={comfy_dir}
EnvironmentFile={root}/%i/instance.env
ExecStart={launch} $ARGS
Restart=no
TimeoutStopSec=30
KillMode=control-group
# Same GPU/toolchain setup as Parametric Studio (launch.sh). PS_PORT and ARGS come from the instance's instance.env.
"""
def write_unit(root=None, launch=None, unit_dir=None):
    d = unit_dir or os.path.expanduser("~/.config/systemd/user"); os.makedirs(d, exist_ok=True); p = os.path.join(d, "comfy-family@.service")
    open(p, "w").write(UNIT.format(root=root or INSTANCES, launch=launch or LAUNCH, comfy_dir=COMFY_DIR)); return p

# ---- runtime -----------------------------------------------------------------------------------------------------------------------------------------------------
def free_vram_gb():
    o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.split(",")
    return (float(o[1]) - float(o[0])) / 1024

def load(family, root=None): return json.load(open(os.path.join(root or INSTANCES, slug(family), "instance.json")))
def is_up(port):
    try: urllib.request.urlopen(f"http://127.0.0.1:{port}/system_stats", timeout=3); return True
    except Exception: return False

IDLE_GB = 1.5          # a server that has loaded no model holds only its CUDA context and allocator pools; start-only checks (nodes, /object_info) are gated on this, not on the working set

def can_start(family, free_gb=None, root=None, floor=FLOOR_GB, need_gb=None):
    """-> (ok, reason). Refuses when the working set (the estimate, or need_gb when the caller only needs the server up, e.g. IDLE_GB) would leave less than the floor free."""
    info = load(family, root); free = free_vram_gb() if free_gb is None else free_gb; need = info["est_vram_gb"] if need_gb is None else need_gb
    return (free - need >= floor, f"{family}: needs ~{need} GB, {free:.1f} GB free, floor {floor} GB")

def start(family, root=None, wait=240, systemctl=None, need_gb=None):
    info = load(family, root); sc = systemctl or (lambda *a: subprocess.run(["systemctl", "--user", *a], capture_output=True, text=True))
    if is_up(info["port"]): return {"status": "already running", "port": info["port"]}
    ok, why = can_start(family, root=root, need_gb=need_gb)
    if not ok: return {"status": "refused", "reason": why}
    r = sc("start", info["unit"])
    if getattr(r, "returncode", 0): return {"status": "failed", "reason": (r.stderr or "")[:200]}
    t0 = time.time()
    while time.time() - t0 < wait:
        if is_up(info["port"]): return {"status": "started", "port": info["port"], "secs": round(time.time() - t0)}
        time.sleep(2)
    return {"status": "timeout", "port": info["port"]}

def stop(family, root=None, systemctl=None):
    info = load(family, root); sc = systemctl or (lambda *a: subprocess.run(["systemctl", "--user", *a], capture_output=True, text=True)); sc("stop", info["unit"]); return {"status": "stopped", "port": info["port"]}

def status(root=None):
    rows = []
    for f in json.load(open(os.path.join(root or INSTANCES, "registry.json"))):
        try: i = load(f, root)
        except OSError: continue
        rows.append({"family": f, "port": i["port"], "up": is_up(i["port"]), "est_gb": i["est_vram_gb"]})
    return rows

def idle_seconds(port):
    """Seconds since the last finished job (from /history), or None when it has never run one."""
    try: h = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/history?max_items=1", timeout=5))
    except Exception: return None
    for v in h.values():
        for k, m in (v.get("status") or {}).get("messages") or []:
            if k in ("execution_success", "execution_error", "execution_interrupted"): return max(0.0, time.time() - m["timestamp"] / 1000)
    return None

def reap(minutes=15, root=None, systemctl=None):
    """Stop instances that are up, have an empty queue, and have been idle for `minutes`. Never touches a busy one."""
    out = []
    for r in status(root):
        if not r["up"]: continue
        q = json.load(urllib.request.urlopen(f"http://127.0.0.1:{r['port']}/queue", timeout=5))
        if q.get("queue_running") or q.get("queue_pending"): continue
        idle = idle_seconds(r["port"])
        if idle is not None and idle > minutes * 60: stop(r["family"], root, systemctl); out.append(r["family"])
    return out

def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:]); cmd = a.pop(0) if a else "list"
    if cmd == "generate":
        fams = a or families(); ports = registry_ports(fams); write_unit(); subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        for f in fams: i = generate(f, ports=ports); print(f"{f:24} :{i['port']}  ~{i['est_vram_gb']:>5} GB  packs {len(i['packs'])}  model types {len(i['model_types'])}")
    elif cmd in ("list", "status"):
        for r in status(): print(f"{r['family']:24} :{r['port']}  {'UP' if r['up'] else '-'}  ~{r['est_gb']} GB")
    elif cmd == "start": print(start(a[0]))
    elif cmd == "stop": print(stop(a[0]))
    elif cmd == "reap": print(reap(float(a[0]) if a else 15))
    else: print(__doc__)
if __name__ == "__main__": main()
