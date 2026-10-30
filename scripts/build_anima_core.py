#!/usr/bin/env python3
"""Builds the Anima (anime / illustration) text-to-image core workflow in API format: UNETLoader + Qwen3-0.6B text encoder (CLIP type stable_diffusion, as ComfyUI's own 'Text to Image (Anima)' blueprint uses)
+ Qwen Image VAE, KSampler euler/simple. Variants differ only in ${unet}, ${steps}, ${cfg} (see studio/goals.py). Local open-weights nodes only.
Usage: python3 scripts/build_anima_core.py [--validate http://127.0.0.1:8200]"""
import argparse, json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from psn.graph import GraphBuilder
from studio.graph_template import fill
TEXT_ENC, VAE = "qwen/qwen_3_06b_base.safetensors", "qwen/qwen_image_vae.safetensors"
DEFAULTS = dict(unet="anima/anima-aesthetic-v1.1.safetensors", prompt="masterpiece, best quality, safe, 1girl, silver hair, school uniform, cherry blossoms, soft light", negative="worst quality, low quality, blurry", seed=7, width=1024, height=1024, steps=30, cfg=3.0)
def build():
    g = GraphBuilder(); unet = g.add("UNETLoader", unet_name="${unet}", weight_dtype="default"); clip = g.add("CLIPLoader", clip_name=TEXT_ENC, type="stable_diffusion", device="default"); vae = g.add("VAELoader", vae_name=VAE)
    pos = g.add("CLIPTextEncode", clip=clip, text="${prompt}"); neg = g.add("CLIPTextEncode", clip=clip, text="${negative}"); lat = g.add("EmptyLatentImage", width="${width}", height="${height}", batch_size=1)
    ks = g.add("KSampler", model=unet, seed="${seed}", steps="${steps}", cfg="${cfg}", sampler_name="euler", scheduler="simple", positive=pos, negative=neg, latent_image=lat, denoise=1.0)
    g.add("SaveImage", images=g.add("VAEDecode", samples=ks, vae=vae), filename_prefix="anima_core"); return g
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--validate", default=""); a = ap.parse_args(); (ROOT / "workflows").mkdir(exist_ok=True)
    g = build(); p = ROOT / "workflows" / "anima_core_t2i_api.json"; p.write_text(json.dumps(g.to_prompt(), indent=1) + "\n"); print("wrote", p.relative_to(ROOT))
    if a.validate:
        oi = json.load(urllib.request.urlopen(a.validate.rstrip("/") + "/object_info", timeout=60))
        for name, vals in (("aesthetic", DEFAULTS), ("turbo", {**DEFAULTS, "unet": "anima/anima-turbo-v1.1.safetensors", "steps": 10, "cfg": 1.0})):
            errs = GraphBuilder.from_prompt(fill(g.to_prompt(), vals)).validate(oi); print(f"  {name}: {len(errs)} validation problems", *errs[:5], sep="\n    ")
