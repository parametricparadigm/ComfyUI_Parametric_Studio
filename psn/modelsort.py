"""Sort model files/folders into model families from EVIDENCE: tensor layout (safetensors header or GGUF header), the folder's model_index.json / config.json class names, model-card base_model tags, sidecar metadata and file names.
The family index is learned from the families already on disk (a layout signature -> families seen with it), so a new file that has the same layout as known files lands with them. Scoring is additive and reported in full; ambiguous files are
returned with their candidates, never forced. --apply only ADDS symlinks inside _complete_pipelines/<family>/<type>/ (never moves or deletes). Original code.
CLI: python3 -m psn.modelsort FOLDER [FOLDER...] [--apply] [--llm]"""
import collections, hashlib, json, os, re, struct, sys, time
from psn import instances
MODELS = instances.MODELS; EXT = (".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx", ".sft")
CLASS_MAP = {"FluxPipeline": "Flux.1", "FluxKontextPipeline": "Flux-Kontext", "Flux2Pipeline": "Flux.2", "StableDiffusionXLPipeline": "SDXL", "StableDiffusionPipeline": "SD15", "StableDiffusion3Pipeline": "SD3-SD3.5", "WanPipeline": "Wan2.2",
             "WanImageToVideoPipeline": "Wan2.2", "QwenImagePipeline": "Qwen-Image-2.1", "LTXPipeline": "LTX-2.5", "LTXImageToVideoPipeline": "LTX-2.5", "HunyuanVideoPipeline": "HunyuanVideo", "CogVideoXPipeline": "CogVideoX",
             "PixArtSigmaPipeline": "PixArt-Sigma", "HiDreamImagePipeline": "HiDream", "Lumina2Pipeline": "Lumina-2", "MochiPipeline": "Mochi", "AllegroPipeline": "Allegro", "SanaPipeline": "SANA-Video", "ZImagePipeline": "Z-Image"}
BASE_MAP = [(r"sdxl|xl_base", "SDXL"), (r"sd_?v?1|sd15|stable-diffusion-v1", "SD15"), (r"flux\.?1|flux-dev|flux-schnell", "Flux.1"), (r"flux\.?2", "Flux.2"), (r"flux\.?3|klein", "Flux.3-Klein"), (r"wan2\.?2", "Wan2.2"), (r"wan2\.?1", "Wan2.1"),
            (r"qwen[-_ ]?image", "Qwen-Image-2.1"), (r"ltx", "LTX-2.5"), (r"hunyuan[-_ ]?video", "HunyuanVideo"), (r"hidream", "HiDream"), (r"sd3|stable-diffusion-3", "SD3-SD3.5"), (r"z[-_ ]?image", "Z-Image"), (r"lumina", "Lumina-2")]
# ---- evidence from files -----------------------------------------------------------------------------------------------------------------------------------
def safetensors_header(p):
    with open(p, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        if n > 200_000_000: return None
        return json.loads(f.read(n))
def gguf_header(p, max_kv=64):
    """general.architecture / general.name from a GGUF file (v2/v3), reading only the key-value header."""
    with open(p, "rb") as f:
        if f.read(4) != b"GGUF": return None
        ver, _, nkv = struct.unpack("<IQQ", f.read(20)); out = {}
        def rd(t):
            if t == 8: n = struct.unpack("<Q", f.read(8))[0]; return f.read(n).decode("utf-8", "replace")
            sizes = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f", 7: "?", 10: "Q", 11: "q", 12: "d"}
            if t in sizes: return struct.unpack("<" + sizes[t], f.read(struct.calcsize(sizes[t])))[0]
            if t == 9: et, n = struct.unpack("<IQ", f.read(12)); [rd(et) for _ in range(n)]; return None
            raise ValueError("unknown gguf type")
        for _ in range(min(nkv, max_kv)):
            kn = struct.unpack("<Q", f.read(8))[0]; k = f.read(kn).decode(); t = struct.unpack("<I", f.read(4))[0]; v = rd(t)
            if k in ("general.architecture", "general.name", "general.basename", "general.size_label"): out[k] = v
        return out
SZ = {"F32": 4, "F16": 2, "BF16": 2, "F8_E4M3": 1, "F8_E5M2": 1, "I8": 1, "U8": 1, "I64": 8, "I32": 4}
def facts_of(p):
    f = {"path": p, "name": os.path.basename(p), "size_gb": round(os.path.getsize(p) / 1e9, 3), "format": os.path.splitext(p)[1].lstrip(".")}
    try:
        if p.endswith((".safetensors", ".sft")):
            h = safetensors_header(p) or {}; meta = h.pop("__metadata__", {}) or {}; by = collections.Counter(); params = 0; pre = collections.Counter()
            for k, v in h.items():
                by[v["dtype"]] += v["data_offsets"][1] - v["data_offsets"][0]; n = 1
                for d in v["shape"]: n *= d
                params += n; pre[".".join(k.split(".")[:2])] += 1
            f.update(tensors=len(h), params_m=round(params / 1e6, 1), dtype=by.most_common(1)[0][0] if by else "?", prefixes=[k for k, _ in pre.most_common(12)], keys=list(h)[:400],
                     meta={k: str(v)[:80] for k, v in meta.items() if k.startswith(("ss_base_model", "ss_sd_model_name", "modelspec.", "ss_network"))})
        elif p.endswith(".gguf"): f["gguf"] = gguf_header(p) or {}
    except Exception as e: f["error"] = f"{type(e).__name__}: {str(e)[:60]}"
    return f
def role_of(f):
    """Which ComfyUI model folder a file belongs in, from its tensor names (None when unsure)."""
    k = " ".join(f.get("keys", [])[:400]); n = f["name"].lower(); pre = " ".join(f.get("prefixes", []))
    if f.get("gguf") is not None and f["format"] == "gguf": return "llm_gguf"
    if re.search(r"lora_(down|up|A|B)|lora_unet_|\.lora_|lora_te", k) or "lora" in n and f.get("size_gb", 9) < 3: return "loras"
    if re.search(r"controlnet|input_hint_block|control_model|zero_convs", k) or "controlnet" in n: return "controlnet"
    if re.search(r"vision_model|visual\.", k) and f.get("size_gb", 9) < 3: return "clip_vision"
    if re.search(r"^(encoder\.down|decoder\.up|post_quant_conv|quant_conv|encoder\.conv_in|decoder\.conv_in)", pre) or "vae" in n and f.get("size_gb", 9) < 1.5: return "vae"
    if re.search(r"encoder\.block|shared\.weight|embed_tokens|model\.layers|text_model\.|t5|umt5|gemma|qwen.*vl|mistral", k + " " + n) and not re.search(r"double_blocks|single_blocks|joint_blocks|transformer_blocks|input_blocks", k): return "text_encoders"
    if re.search(r"esrgan|realesr|swinir|upscal", n): return "upscale_models"
    if re.search(r"model\.diffusion_model\.|first_stage_model|cond_stage_model", k): return "checkpoints"
    return "diffusion_models"
def signature(prefixes): return hashlib.sha1("|".join(sorted(p for p in prefixes if p))[:2000].encode()).hexdigest()[:16]
def folder_context(d):
    c = {"pipeline_class": None, "arch": None, "base_model": None, "text": ""}
    for name, key in (("model_index.json", "_class_name"), ("config.json", "architectures")):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            try: j = json.load(open(p)); v = j.get(key) or j.get("_class_name") or j.get("model_type"); c["pipeline_class" if name.startswith("model_index") else "arch"] = v[0] if isinstance(v, list) else v
            except Exception: pass
    for rd in ("README.md", "readme.md"):
        p = os.path.join(d, rd)
        if os.path.isfile(p):
            t = open(p, errors="replace").read(4000); m = re.search(r"base_model:\s*\[?\s*[-\s]*([^\n\]]+)", t); c["base_model"] = m.group(1).strip() if m else None; c["text"] = t[:800]
    return c
# ---- the learned family index ----------------------------------------------------------------------------------------------------------------------------------
def build_index(models=None, limit_per_family=40, min_bytes=20_000_000):
    """layout signature -> Counter(families); plus per-family parameter sizes. Learned from the real files in _complete_pipelines (deduplicated by inode)."""
    models = models or MODELS; cp = f"{models}/_complete_pipelines"; sig = collections.defaultdict(collections.Counter); params = collections.defaultdict(list); seen = set()
    for fam in instances.families(models):
        n = 0
        for dp, _, fs in os.walk(f"{cp}/{fam}", followlinks=True):
            for fn in fs:
                p = os.path.join(dp, fn)
                if not fn.endswith(".safetensors") or n >= limit_per_family: continue
                try: st = os.stat(p)
                except OSError: continue
                if st.st_size < min_bytes or (st.st_dev, st.st_ino) in seen: continue
                seen.add((st.st_dev, st.st_ino)); f = facts_of(p)
                if f.get("prefixes"): sig[signature(f["prefixes"])][fam] += 1; params[fam].append(f["params_m"]); n += 1
    return {"sig": sig, "params": params, "families": instances.families(models)}
def classify(path, index, ctx=None, aliases=None):
    f = facts_of(path); ctx = ctx or folder_context(os.path.dirname(path)); fams = index["families"]; score = collections.Counter(); why = collections.defaultdict(list)
    f["role"] = role_of(f)
    text = " ".join([f["name"], os.path.dirname(path).split("/")[-1], ctx.get("base_model") or "", json.dumps(f.get("meta", {})), json.dumps(f.get("gguf") or {})]).lower()
    if f.get("prefixes"):
        for fam, n in index["sig"].get(signature(f["prefixes"]), {}).items():
            score[fam] += 3; why[fam].append(f"same tensor layout as {n} known {fam} file(s)")
            if any(abs(f["params_m"] - q) <= 0.15 * max(q, 1) for q in index["params"].get(fam, [])): score[fam] += 2; why[fam].append("parameter count matches a known file")
    pc = ctx.get("pipeline_class")
    if pc in CLASS_MAP: score[CLASS_MAP[pc]] += 4; why[CLASS_MAP[pc]].append(f"model_index class {pc}")
    for rx, fam in BASE_MAP:
        if re.search(rx, text) and fam in fams: score[fam] += 3; why[fam].append(f"name/metadata mentions '{rx.split('|')[0]}'")
    for fam in fams:
        for a in dict.fromkeys(instances._aliases(fam) + (aliases or {}).get(fam, [])):
            if len(a) >= 4 and re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", text): score[fam] += 2; why[fam].append(f"name contains '{a}'"); break
    ranked = score.most_common(4); top, second = (ranked + [(None, 0), (None, 0)])[:2]
    f["candidates"] = [{"family": k, "score": v, "why": why[k][:3]} for k, v in ranked]
    if top[0] and top[1] >= 4 and top[1] - second[1] >= 2: f.update(family=top[0], confidence="high" if top[1] >= 6 else "medium", decision="family")
    elif top[0] and top[1] >= 3: f.update(family=top[0], confidence="low", decision="ambiguous")
    else: f.update(family=None, confidence="none", decision="unknown")
    f.pop("keys", None); return f
def scan(folder):
    out = []
    for dp, ds, fs in os.walk(folder, followlinks=False):
        ds[:] = [d for d in ds if d not in (".git", "__pycache__", ".cache")]
        for fn in sorted(fs):
            if fn.lower().endswith(EXT) and os.path.getsize(os.path.join(dp, fn)) > 1_000_000: out.append(os.path.join(dp, fn))
    return out
def apply_links(rows, models=None, dry=True):
    """Add symlinks _complete_pipelines/<family>/<role>/<name> -> file, only for confident decisions with a ComfyUI role folder. Never overwrites or deletes."""
    models = models or MODELS; made = []
    for r in rows:
        if r["decision"] != "family" or r["role"] in ("llm_gguf", None): continue
        d = f"{models}/_complete_pipelines/{r['family']}/{r['role']}"; dst = f"{d}/{r['name']}"
        if os.path.lexists(dst) or any(os.path.samefile(r["path"], os.path.join(d, x)) for x in (os.listdir(d) if os.path.isdir(d) else []) if os.path.exists(os.path.join(d, x))): continue
        made.append(dst)
        if not dry: os.makedirs(d, exist_ok=True); os.symlink(os.path.realpath(r["path"]), dst)
    return made
def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:]); apply = "--apply" in a; folders = [x for x in a if not x.startswith("--")]
    idx = build_index(); rows = [classify(p, idx) for fo in folders for p in scan(fo)]
    c = collections.Counter(r["decision"] for r in rows); print(f"{len(rows)} model files: {dict(c)}")
    for r in rows: print(f"  {r['decision']:9} {str(r['family'] or '-'):18} {r['confidence']:6} {r['role'] or '-':16} {r['size_gb']:>7} GB  {r['name'][:46]}  | " + ("; ".join(r['candidates'][0]['why'][:1]) if r['candidates'] else "no evidence"))
    links = apply_links(rows, dry=not apply); print(("LINKED " if apply else "WOULD LINK ") + str(len(links)) + " (symlinks only, nothing moved)")
    out = os.path.expanduser(f"~/Documents/MODEL_SORT_{time.strftime('%Y%m%d-%H%M%S')}.tsv")
    with open(out, "w") as o:
        o.write("path\tdecision\tfamily\tconfidence\trole\tsize_gb\tparams_m\tdtype\tevidence\n"); [o.write("\t".join(str(x).replace("\t", " ") for x in (r["path"], r["decision"], r["family"], r["confidence"], r["role"], r["size_gb"], r.get("params_m", ""), r.get("dtype", ""), "; ".join(r["candidates"][0]["why"]) if r["candidates"] else "")) + "\n") for r in rows]
    print("report:", out)
if __name__ == "__main__": main()
