"""Readiness: which model files a workflow needs, and whether they are on disk. A missing model is a clear, listed state (with a download hint when we know one), never a crash at run time.
Idea carried over from the home studio's readiness registry; here it reads the workflow itself instead of a hand-kept list. Original code."""
import csv, glob, json, os, re
from psn import paths

MODELS = paths.setting("PSN_MODELS_ROOT", "STUDIO_MODELS_ROOT", default=paths.home("ComfyUI", "models"))
LOADERS = {"UNETLoader": [("unet_name", "diffusion_models")], "CLIPLoader": [("clip_name", "text_encoders")], "DualCLIPLoader": [("clip_name1", "text_encoders"), ("clip_name2", "text_encoders")],
           "VAELoader": [("vae_name", "vae")], "CheckpointLoaderSimple": [("ckpt_name", "checkpoints")], "LoraLoader": [("lora_name", "loras")], "LoraLoaderModelOnly": [("lora_name", "loras")],
           "ControlNetLoader": [("control_net_name", "controlnet")], "UpscaleModelLoader": [("model_name", "upscale_models")], "CLIPVisionLoader": [("clip_name", "clip_vision")],
           "StyleModelLoader": [("style_model_name", "style_models")], "AudioEncoderLoader": [("audio_encoder_name", "audio_encoders")]}
_PH = re.compile(r"\$\{[A-Za-z_]\w*\}")

def required_models(graph):
    """-> [{node, class, field, value, kind}] for every loader input holding a concrete file name (placeholders are skipped)."""
    out = []
    for nid, n in graph.items():
        for field, kind in LOADERS.get(n.get("class_type"), []):
            v = (n.get("inputs") or {}).get(field)
            if isinstance(v, str) and v and not _PH.search(v): out.append({"node": nid, "class": n["class_type"], "field": field, "value": v, "kind": kind})
    return out

def _find(models, kind, value):
    cands = [f"{models}/{kind}/{value}"] + [f"{p}/{value}" for p in glob.glob(f"{models}/_complete_pipelines/*/{kind}")]
    for c in cands:
        if os.path.exists(c): return os.path.realpath(c)
    base = os.path.basename(value)         # same file filed under another folder name: still counts, and says where
    for p in [f"{models}/{kind}"] + glob.glob(f"{models}/_complete_pipelines/*/{kind}") + glob.glob(f"{models}/{kind}/*"):
        if os.path.exists(f"{p}/{base}"): return os.path.realpath(f"{p}/{base}")
    return None

def hints(tsv_paths=None):
    """basename -> 'repo: ...' from the owner's download lists, when those files are present."""
    out = {}
    for p in tsv_paths or glob.glob(os.path.expanduser("~/Documents/MODELS_STILL_TO_DOWNLOAD*.tsv")):
        try:
            for r in csv.DictReader(open(p), delimiter="\t"):
                name = (r.get("file") or r.get("filename") or r.get("name") or "").strip(); src = (r.get("repo") or r.get("source") or r.get("url") or "").strip()
                if name and src: out[os.path.basename(name)] = src
        except OSError: pass
    return out

def check(graph, models=None, hint_map=None):
    models, hm, rows = models or MODELS, hint_map if hint_map is not None else hints(), []
    for m in required_models(graph):
        p = _find(models, m["kind"], m["value"]); r = dict(m, present=bool(p))
        if p: r.update(path=p, size_gb=round(os.path.getsize(p) / 1e9, 2), hash_verified=os.path.exists(p + ".sha256-ok") or os.path.exists(os.path.join(models, m["kind"], m["value"] + ".sha256-ok")))
        else: r["hint"] = hm.get(os.path.basename(m["value"]), "no download source on record")
        rows.append(r)
    miss = [r for r in rows if not r["present"]]
    return {"ready": not miss, "models": rows, "missing": miss, "total_gb": round(sum(r.get("size_gb", 0) for r in rows), 1)}

def render_md(name, rep):
    L = [f"### {name}: {'READY' if rep['ready'] else 'NOT READY (' + str(len(rep['missing'])) + ' missing)'}  ({rep['total_gb']} GB of models)"]
    L += [f"- {'OK ' if r['present'] else 'MISSING'} `{r['value']}` ({r['kind']}) " + (f"{r['size_gb']} GB" + ("" if r.get("hash_verified") else ", hash not recorded") if r["present"] else f"-> {r['hint']}") for r in rep["models"]]
    return "\n".join(L)
