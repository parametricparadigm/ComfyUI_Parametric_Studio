"""Pinned, sourced model recipes. A recipe is only valid if it names where it came from (a file in an official package or the owner's research notes) and quotes the line. Nothing is invented: when we do not have a source, there is no recipe.
LTX-2.5 long-clip decode rule: the owner's research notes (LTX25_RESEARCH.md) say decode stalls over 5-10 s; use tile 512, temporal 64 / overlap 16, or the Conv VAE; temporal seams appear with overlap 8. Original code."""
import copy
LTX_CONV_VAE, LTX_DIFF_VAE = "ltx/ltx-2.5-video-vae-conv-bf16.safetensors", "ltx/ltx-2.5-video-vae-bf16.safetensors"
RECIPES = {
 "ltx25-distilled": {"sampler": "euler_ancestral", "sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0", "cfg": 1.0, "steps": 8,
                     "source": "Lightricks/ComfyUI-LTXVideo example_workflows/2.5/LTX-2.5_T2V_I2V_Single_Stage_Distilled.json (Sampler - Distilled 8 steps)", "quote": "ManualSigmas '1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0'; KSamplerSelect euler_ancestral; CFGGuider 1"},
 "flux3-klein": {"sampler": "er_sde", "scheduler": "simple", "steps": 15, "cfg": 1.0, "source": "ComfyUI workflow templates image_flux3_klein_t2i.json and image_flux3_klein_distilled_t2i.json", "quote": "KSampler [3, 'randomize', 15, 1, 'er_sde', 'simple', 1]"},
 "ltx25-long-decode": {"vae": LTX_CONV_VAE, "tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 16, "applies_over_seconds": 5.0,
                       "source": "comfy-studio-contest-notes/LTX25_RESEARCH.md, Gotchas", "quote": "decode stalls over 5-10 s (use tile 512, temporal 64 / overlap 16, or the Conv VAE); temporal seams with overlap 8"},
}
def recipe_problems(r=None):
    """Every recipe must cite a source and a quote."""
    return [f"recipe '{k}' has no {f}" for k, v in (r or RECIPES).items() for f in ("source", "quote") if not str(v.get(f, "")).strip()]
def ltx_decode_settings(frames, fps):
    """-> the tiled-decode settings for a clip. Clips over ~5 s get the Conv VAE and the 16-frame temporal overlap from the research notes."""
    secs = (frames - 1) / float(fps); long = secs > RECIPES["ltx25-long-decode"]["applies_over_seconds"]; base = {"tile_size": 512, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}
    if long: base.update({k: RECIPES["ltx25-long-decode"][k] for k in ("tile_size", "overlap", "temporal_size", "temporal_overlap")})
    return {**base, "vae": LTX_CONV_VAE if long else None, "long_clip": long, "seconds": round(secs, 2)}
def apply_ltx_safe_decode(graph, frames, fps):
    """A copy of an API graph with the decode set up safely for this clip length. Only touches VAEDecodeTiled nodes and (for long clips) an LTX video VAELoader that points at the heavy DiffVAE."""
    g = copy.deepcopy(graph); s = ltx_decode_settings(frames, fps)
    for n in g.values():
        if n.get("class_type") == "VAEDecodeTiled": n["inputs"].update({k: s[k] for k in ("tile_size", "overlap", "temporal_size", "temporal_overlap")})
        if s["long_clip"] and n.get("class_type") == "VAELoader" and n["inputs"].get("vae_name") == LTX_DIFF_VAE: n["inputs"]["vae_name"] = LTX_CONV_VAE
    return g
