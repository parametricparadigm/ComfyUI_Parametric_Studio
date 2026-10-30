#!/usr/bin/env python3
"""Builds the Apache-2.0 'open' core workflows (API format), from ComfyUI's own official templates: FLUX.2 Klein 4B text-to-image (image_flux2_klein_text_to_image; distilled 4 steps / base 20 steps)
and Wan 2.2 TI2V-5B text-to-video and image-to-video (video_wan2_2_5B_ti2v). Local open-weights nodes only. Usage: python3 scripts/build_open_core.py [--validate http://127.0.0.1:8200]"""
import argparse, json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from psn.graph import GraphBuilder
from studio.graph_template import fill
WAN_NEG = "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走"   # the official template's negative prompt
def klein():
    g = GraphBuilder(); unet = g.add("UNETLoader", unet_name="${unet}", weight_dtype="default"); clip = g.add("CLIPLoader", clip_name="qwen_3_4b.safetensors", type="flux2", device="default"); vae = g.add("VAELoader", vae_name="flux2-vae.safetensors")
    pos = g.add("CLIPTextEncode", clip=clip, text="${prompt}"); neg = g.add("CLIPTextEncode", clip=clip, text="${negative}"); lat = g.add("EmptyFlux2LatentImage", width="${width}", height="${height}", batch_size=1)
    sig = g.add("Flux2Scheduler", steps="${steps}", width="${width}", height="${height}"); guider = g.add("CFGGuider", model=unet, positive=pos, negative=neg, cfg="${cfg}"); samp = g.add("KSamplerSelect", sampler_name="euler"); noise = g.add("RandomNoise", noise_seed="${seed}")
    out = g.add("SamplerCustomAdvanced", noise=noise, guider=guider, sampler=samp, sigmas=sig, latent_image=lat)
    g.add("SaveImage", images=g.add("VAEDecode", samples=out, vae=vae), filename_prefix="open_klein4b"); return g
def wan(i2v):
    g = GraphBuilder(); unet = g.add("UNETLoader", unet_name="wan2.2_ti2v_5B_fp16.safetensors", weight_dtype="default"); clip = g.add("CLIPLoader", clip_name="umt5_xxl_fp8_e4m3fn_scaled.safetensors", type="wan", device="default"); vae = g.add("VAELoader", vae_name="wan2.2_vae.safetensors")
    model = g.add("ModelSamplingSD3", model=unet, shift=8.0); pos = g.add("CLIPTextEncode", clip=clip, text="${prompt}"); neg = g.add("CLIPTextEncode", clip=clip, text="${negative}")
    kw = dict(vae=vae, width="${width}", height="${height}", length="${frames}", batch_size=1)
    if i2v: kw["start_image"] = g.add("LoadImage", image="${image}")
    lat = g.add("Wan22ImageToVideoLatent", **kw)
    ks = g.add("KSampler", model=model, seed="${seed}", steps=20, cfg=5.0, sampler_name="uni_pc", scheduler="simple", positive=pos, negative=neg, latent_image=lat, denoise=1.0)
    g.add("SaveVideo", video=g.add("CreateVideo", images=g.add("VAEDecode", samples=ks, vae=vae), fps="${fps}"), filename_prefix="video/open_wan22_5b", format="auto", codec="auto"); return g
TESTS = {"flux2_klein4b_t2i": (klein, dict(unet="flux-2-klein-4b.safetensors", prompt="a red fox in snow", negative="", seed=7, width=1024, height=1024, steps=4, cfg=1.0)),
         "wan22_5b_t2v": (lambda: wan(False), dict(prompt="a fox walks through snow", negative=WAN_NEG, seed=7, width=832, height=480, frames=121, fps=24)),
         "wan22_5b_i2v": (lambda: wan(True), dict(prompt="the fox turns its head", negative=WAN_NEG, seed=7, width=832, height=480, frames=121, fps=24, image="example.png"))}
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--validate", default=""); a = ap.parse_args(); oi = json.load(urllib.request.urlopen(a.validate.rstrip("/") + "/object_info", timeout=60)) if a.validate else None
    for name, (fn, vals) in TESTS.items():
        g = fn(); p = ROOT / "workflows" / f"{name}_api.json"; p.write_text(json.dumps(g.to_prompt(), indent=1) + "\n"); print("wrote", p.relative_to(ROOT))
        if oi: errs = GraphBuilder.from_prompt(fill(g.to_prompt(), vals)).validate(oi); print(f"  {len(errs)} validation problems", *errs[:5], sep="\n    ")
