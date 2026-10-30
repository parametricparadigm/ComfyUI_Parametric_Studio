#!/usr/bin/env python3
"""Builds the MiniMax H3 (text-to-video+audio, image-to-video+audio) and MiniMax Music 3 core workflows from ComfyUI's OFFICIAL LOCAL templates (video_minimax_h3_t2v / _i2v, audio_minimax_music_3; not the paid
api_* variants): converts the template (studio.ui2api), binds the user-facing fields to ${placeholders}, and remaps the template's model file names to the closest file the server really has (a name is
accepted only when it is a close match; anything else is reported). Usage: python3 scripts/build_h3_music.py [--server http://127.0.0.1:8200]"""
import argparse, difflib, json, re, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from studio.ui2api import ui_to_api
from psn.graph import GraphBuilder
from studio.graph_template import fill
def _templates():
    import comfyui_workflow_templates_json as t
    return str(Path(t.__file__).parent / "templates") + "/"
TPL = _templates()
def norm(s): return re.sub(r"[^a-z0-9.]+", "_", s.lower().split("/")[-1])
SUBSTITUTE = {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors", "minimax_music3_text_encoder_pruned_int8_convrot.safetensors": "minimax_music3_text_encoder_pruned_bf16.safetensors"}   # quantised file not on this box -> the unquantised one that is
def remap_names(g, oi):
    report = []
    for nid, n in g.items():
        info = oi.get(n["class_type"], {}); req = {**(info.get("input", {}).get("required") or {}), **(info.get("input", {}).get("optional") or {})}
        for k, v in list(n["inputs"].items()):
            spec = req.get(k)
            if not spec or not isinstance(v, str): continue
            opts = spec[0] if isinstance(spec[0], list) else (spec[1].get("options") if len(spec) > 1 and isinstance(spec[1], dict) else None)
            if not opts or v in opts or "${" in v or not all(isinstance(o, str) for o in opts): continue
            if v in SUBSTITUTE and SUBSTITUTE[v] in opts: n["inputs"][k] = SUBSTITUTE[v]; report.append(f"  {nid}.{k}: {v}  ->  {SUBSTITUTE[v]} (substituted: unquantised variant)"); continue
            best = max(opts, key=lambda o: difflib.SequenceMatcher(None, norm(v), norm(o)).ratio()); r = difflib.SequenceMatcher(None, norm(v), norm(best)).ratio()
            if r >= 0.86: n["inputs"][k] = best; report.append(f"  {nid}.{k}: {v}  ->  {best} ({r:.2f})")
            else: report.append(f"  !! {nid}.{k}: {v} has no close local match (best {best}, {r:.2f})")
    return report

def fix_save_nodes(g):
    """SaveVideo/SaveAudioAdvanced need their dynamic-combo selector and sub-input as plain keys (verified by a real LTX render through the studio)."""
    for n in g.values():
        i = n["inputs"]
        if n["class_type"] == "SaveVideo":
            fmt = i.pop("format", "auto"); codec = i.pop("codec", None) or i.pop("format.codec", "auto"); i["format"] = fmt if isinstance(fmt, str) else "auto"; i["codec"] = codec if isinstance(codec, str) else "auto"
        if n["class_type"] == "SaveAudioAdvanced": i["format"] = i.get("format") if isinstance(i.get("format"), str) else "flac"
    return g
def one(g, cls): return next(k for k, v in g.items() if v["class_type"] == cls)
def src(g, nid, inp): return g[nid]["inputs"][inp][0]
def build(name, oi):
    ui = json.load(open(TPL + name + ".json")); g, probs = ui_to_api(ui, oi); assert not probs, probs
    if name.startswith("audio"):
        e = one(g, "MiniMaxMusic3TextEncode"); g[e]["inputs"].update(caption="${caption}", lyrics="${lyrics}", max_duration="${duration}"); g[one(g, "SeedNode")]["inputs"]["seed"] = "${seed}"
    else:
        v = one(g, "MiniMaxH3ImageToVideo"); g[v]["inputs"]["prompt"] = "${prompt}"; g[one(g, "RandomNoise")]["inputs"]["noise_seed"] = "${seed}"
        rs = src(g, v, "width"); g[rs]["inputs"].update(aspect_ratio="${aspect}", megapixels="${megapixels}")
        g[src(g, src(g, v, "length"), "values.a")]["inputs"]["value"] = "${seconds}"
        sw = one(g, "PrimitiveBoolean"); g[sw]["inputs"]["value"] = "${turbo}"
        if "first_frame" in g[v]["inputs"]: g[src(g, v, "first_frame")]["inputs"]["image"] = "${image}"
    return fix_save_nodes(g), remap_names(g, oi)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--server", default="http://127.0.0.1:8200"); a = ap.parse_args(); oi = json.load(urllib.request.urlopen(a.server + "/object_info", timeout=60))
    asp = oi["ResolutionSelector"]["input"]["required"]["aspect_ratio"][0]; print("aspect choices:", asp)
    for tpl, out, vals in (("video_minimax_h3_t2v", "h3_t2v", dict(prompt="a fox walks through snow", seed=5, aspect=asp[0], megapixels=0.4, seconds=2.0, turbo=False)),
                           ("video_minimax_h3_i2v", "h3_i2v", dict(prompt="the fox turns its head", seed=5, aspect=asp[0], megapixels=0.4, seconds=2.0, turbo=False, image="example.png")),
                           ("audio_minimax_music_3", "music3", dict(caption="warm acoustic folk, fingerpicked guitar, gentle", lyrics="", duration=30, seed=7))):
        g, rep = build(tpl, oi); (ROOT / "workflows" / f"{out}_api.json").write_text(json.dumps(g, indent=1) + "\n"); print("wrote", out, len(g), "nodes"); print(*rep, sep="\n")
        errs = [e for e in GraphBuilder.from_prompt(fill(g, vals)).validate(oi) if "COMFY_MATCHTYPE" not in e]; print(f"  {len(errs)} validation problems (strict-type false alarms ignored)", *errs[:6], sep="\n    ")
