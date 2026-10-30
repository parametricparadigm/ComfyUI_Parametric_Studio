#!/usr/bin/env python3
"""Builds the flagship app workflows (recast, vfx_ltx, reshoot, director_keyframes) as API graphs with ${placeholder} values. Core ComfyUI nodes plus this repo's PSN_FPSResampler, and KJNodes' VRAM_Debug where the
owner's recipe unloads the text encoder before sampling.

Recipes are the owner's tested ones (docs/processes/video-edits.md, h3-special-loras.md, LTX_H3_BATCH 4e-4h). Recast keeps the architecture idea of Comfy-Org/comfy-openjutsu (MIT; built on Akatz Labs' H3 Character Swap workflow
and the akatz-ai swap LoRA) but runs on core nodes, without the GPL `h3_character_swap` pack: <Video 1> + <Picture 1> on MiniMaxH3ReferenceToVideo with the swap LoRA, 12 steps. See docs/CREDITS.md.
Usage: python3 scripts/build_flagship.py"""
import json, os
WF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")
H3_CLIP = "qwen/qwen3-vl-32b/qwen3-vl-32b-minimax-h3-nvfp4-awq.safetensors"; H3_VAE = "minimax_h3_video_vae_fp16.safetensors"; H3_AVAE = "minimax_h3_audio_vae_fp32.safetensors"
def N(cls, **inputs): return {"class_type": cls, "inputs": inputs}
def source_nodes(width="${width}", height="${height}"):
    """Source clip -> the requested part -> 24 fps -> exactly ${frames} frames at the work size. `comp` also carries the source audio for the mux."""
    return {
     "src": N("LoadVideo", file="${video}"),
     "part": N("Video Slice", video=["src", 0], start_time=0.0, duration="${slice_seconds}", strict_duration=False),
     "comp": N("GetVideoComponents", video=["part", 0]),
     "fps24": N("PSN_FPSResampler", image=["comp", 0], source_fps=["comp", 2], target_fps=24.0, mode="nearest"),
     "trim": N("ImageFromBatch", image=["fps24", 0], batch_index=0, length="${frames}"),
     "scale": N("ImageScale", image=["trim", 0], upscale_method="lanczos", width=width, height=height, crop="center"),
    }
def h3_common():
    return {
     "unet": N("UNETLoader", unet_name="minimax_h3/minimax_h3_ref2va_pruned_int8_convrot.safetensors", weight_dtype="default"),
     "clip": N("CLIPLoader", clip_name=H3_CLIP, type="minimax", device="default"),
     "vae": N("VAELoader", vae_name=H3_VAE), "avae": N("VAELoader", vae_name=H3_AVAE),
     "free_te": N("VRAM_Debug", any_input=["ref", 0], empty_cache=True, gc_collect=True, unload_all_models=True),   # the owner's "text encoder unloaded" arm: 51 GB peak instead of 60+
     "noise": N("RandomNoise", noise_seed="${seed}"),
     "dec": N("VAEDecode", samples=["samp", 0], vae=["vae", 0]),
     "mk": N("CreateVideo", images=["dec", 0], audio=["comp", 1], fps=24.0),        # the ORIGINAL audio, muxed back; a silent source stays silent
    }
def recast():
    # h3_character_swap_pro4500_1000 is akatz-ai's LoRA; the owner's proven arm (H3_ADDONS_AB §1b arm D): baked 1.0, res_multistep/simple, 12 steps, no turbo. Below 12 steps cuts become crash-zooms; nvfp4 collapses identity.
    g = {**source_nodes(), **h3_common()}
    g.update({
     "swap": N("LoraLoaderModelOnly", model=["unet", 0], lora_name="minimax_h3/h3_character_swap_pro4500_1000.safetensors", strength_model=1.0),
     "char": N("LoadImage", image="${image}"),
     "ref": N("MiniMaxH3ReferenceToVideo", clip=["clip", 0], vae=["vae", 0], audio_vae=["avae", 0], prompt="${prompt}", width="${width}", height="${height}", length="${frames}", ref_image_size="match", **{"ref_images.ref_image_0": ["char", 0], "ref_videos.ref_video_0": ["scale", 0]}),
     "guider": N("BasicGuider", model=["swap", 0], conditioning=["free_te", 0]),
     "sched": N("BasicScheduler", model=["swap", 0], scheduler="simple", steps=12, denoise=1.0),
     "ksel": N("KSamplerSelect", sampler_name="res_multistep"),
     "samp": N("SamplerCustomAdvanced", noise=["noise", 0], guider=["guider", 0], sampler=["ksel", 0], sigmas=["sched", 0], latent_image=["ref", 1]),
     "save": N("SaveVideo", video=["mk", 0], filename_prefix="recast/recast", format="auto", codec="auto"),
    })
    return g
def reshoot():
    # A new take, not a re-film: the official H3 I2V graph (FL2VA int8, 8-step turbo) starts from the clip's first frame, the camera move is in the prompt, and H3 regenerates the action and its sound.
    # Tested and rejected: Ref2VA with the clip as <Video 1> copies the source camera (the prompt's move does not happen). A true re-film needs Meridian, which needs nodes that are not installed.
    g = json.load(open(os.path.join(WF, "h3_i2v_api.json")))
    for dead in ("114", "115", "105:107", "105:111"): del g[dead]
    g.update({
     "src": N("LoadVideo", file="${video}"),
     "part": N("Video Slice", video=["src", 0], start_time=0.0, duration=0.5, strict_duration=False),
     "comp": N("GetVideoComponents", video=["part", 0]),
     "first": N("ImageFromBatch", image=["comp", 0], batch_index=0, length=1),
     "scale": N("ImageScale", image=["first", 0], upscale_method="lanczos", width="${width}", height="${height}", crop="center"),
    })
    g["105:104"]["inputs"].update(first_frame=["scale", 0], width="${width}", height="${height}", length="${frames}")
    next(n for n in g.values() if n["class_type"] == "SaveVideo")["inputs"]["filename_prefix"] = "reshoot/reshoot"
    return g
def vfx_ltx():
    # LTX-2.5 22B distilled with an IC-LoRA: the source clip is the guide; 8 sigmas, CFG 1, euler_ancestral (owner's ltx_ic_v2v graph, LTX_H3_BATCH 4e-4h). The sound is LTX's own unless the effect asks for the source audio.
    g = source_nodes()
    g.update({
     "unet": N("UNETLoader", unet_name="ltx 2.5/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", weight_dtype="default"),
     "lora": N("LTXICLoRALoaderModelOnly", model=["unet", 0], lora_name="${lora}", strength_model="${strength}"),
     "clip": N("CLIPLoader", clip_name="gemma/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", type="ltxv", device="default"),
     "vae": N("VAELoader", vae_name="ltx/ltx-2.5-video-vae-conv-bf16.safetensors"), "avae": N("VAELoader", vae_name="ltx/ltx-2.5-audio-vae-bf16.safetensors"),
     "pos": N("CLIPTextEncode", clip=["clip", 0], text="${prompt}"), "neg": N("CLIPTextEncode", clip=["clip", 0], text="${negative}"),
     "cond": N("LTXVConditioning", positive=["pos", 0], negative=["neg", 0], frame_rate=24.0),
     "lat": N("EmptyLTXVLatentVideo", width="${width}", height="${height}", length="${frames}", batch_size=1),
     "guide": N("LTXAddVideoICLoRAGuide", positive=["cond", 0], negative=["cond", 1], vae=["vae", 0], latent=["lat", 0], image=["scale", 0], frame_idx=0, strength=1.0, latent_downscale_factor=["lora", 1], crop="disabled", use_tiled_encode=False, tile_size=256, tile_overlap=64),
     "guider": N("CFGGuider", model=["lora", 0], positive=["guide", 0], negative=["guide", 1], cfg=1.0),
     "noise": N("RandomNoise", noise_seed="${seed}"), "ksel": N("KSamplerSelect", sampler_name="euler_ancestral"),
     "sig": N("ManualSigmas", sigmas="1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"),
     "aud": N("LTXVEmptyLatentAudio", audio_vae=["avae", 0], frames_number="${frames}", frame_rate=24, batch_size=1),
     "av": N("LTXVConcatAVLatent", video_latent=["guide", 2], audio_latent=["aud", 0]),
     "samp": N("SamplerCustomAdvanced", noise=["noise", 0], guider=["guider", 0], sampler=["ksel", 0], sigmas=["sig", 0], latent_image=["av", 0]),
     "sep": N("LTXVSeparateAVLatent", av_latent=["samp", 0]),
     "crop": N("LTXVCropGuides", positive=["guide", 0], negative=["guide", 1], latent=["sep", 0]),
     "dec": N("VAEDecodeTiled", samples=["crop", 2], vae=["vae", 0], tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8),
     "adec": N("LTXVAudioVAEDecode", samples=["sep", 1], audio_vae=["avae", 0]),
     "sound": N("ComfySwitchNode", switch="${new_sound}", on_true=["adec", 0], on_false=["comp", 1]),      # LTX's own track from the prompt, or the source audio (a matte)
     "mk": N("CreateVideo", images=["dec", 0], audio=["sound", 0], fps=24.0),
     "save": N("SaveVideo", video=["mk", 0], filename_prefix="vfx/ltx_vfx", format="auto", codec="auto"),
    })
    return g
def director_keyframes():
    # The official H3 I2V graph (workflows/h3_i2v_api.json, FL2VA int8) with the core node's optional last_frame wired: the owner's first/last-frame mode (video-h3-pipelines).
    g = json.load(open(os.path.join(WF, "h3_i2v_api.json")))
    g["116"] = N("LoadImage", image="${last_image}")
    g["105:104"]["inputs"]["last_frame"] = ["116", 0]
    next(n for n in g.values() if n["class_type"] == "SaveVideo")["inputs"]["filename_prefix"] = "director/keyframes"
    return g
ORBIT_PROMPT = "One frozen instant. Only the camera moves. In a continuous 360 orbit. Preserve every person and object in exactly the same world position, orientation, shape and pose throughout the shot. Airborne objects remain suspended at the captured height and angle: no wobbling, shaking, spinning, drifting, falling or continued action. Keep faces, hands, clothing, liquids and the background motionless while retaining their natural appearance. Camera parallax is the only source of apparent movement. No cuts, zoom, morphing or added objects."
def orbit360():
    # pablodawson's MiniMax-H3 360 Orbit LoRA (FL2VA): the same frame as first AND last keyframe, its prompt verbatim, 768x768x73, 28 steps, audio off, per its card. Bypass loader: baking it gave no orbit in the owner's test (h3-special-loras).
    return {
     "src": N("LoadVideo", file="${video}"),
     "comp": N("GetVideoComponents", video=["src", 0]),
     "moment": N("ImageFromBatch", image=["comp", 0], batch_index="${frame_index}", length=1),
     "scale": N("ImageScale", image=["moment", 0], upscale_method="lanczos", width=768, height=768, crop="center"),
     "unet": N("UNETLoader", unet_name="minimax_h3/minimax_h3_fl2va_pruned_int8_convrot.safetensors", weight_dtype="default"),
     "orbit": N("LoraLoaderBypassModelOnly", model=["unet", 0], lora_name="minimax_h3/orbit360/minimax_h3_flf2v_lora_v1.safetensors", strength_model=1.0),
     "clip": N("CLIPLoader", clip_name=H3_CLIP, type="minimax", device="default"),
     "vae": N("VAELoader", vae_name=H3_VAE),
     "i2v": N("MiniMaxH3ImageToVideo", clip=["clip", 0], vae=["vae", 0], prompt=ORBIT_PROMPT, width=768, height=768, length=73, first_frame=["scale", 0], last_frame=["scale", 0]),
     "guider": N("BasicGuider", model=["orbit", 0], conditioning=["i2v", 0]),
     "sched": N("BasicScheduler", model=["orbit", 0], scheduler="simple", steps=28, denoise=1.0),
     "ksel": N("KSamplerSelect", sampler_name="res_multistep"),
     "noise": N("RandomNoise", noise_seed="${seed}"),
     "samp": N("SamplerCustomAdvanced", noise=["noise", 0], guider=["guider", 0], sampler=["ksel", 0], sigmas=["sched", 0], latent_image=["i2v", 1]),
     "dec": N("VAEDecode", samples=["samp", 0], vae=["vae", 0]),
     "mk": N("CreateVideo", images=["dec", 0], fps=24.0),
     "save": N("SaveVideo", video=["mk", 0], filename_prefix="reshoot/orbit360", format="auto", codec="auto"),
    }
def reshoot_wan():
    # ComfyUI's official template video_wan2_2_14B_fun_camera (its 20-step arm, converted with studio/ui2api.py): a real camera path from WanCameraEmbedding, conditioned on the clip's first frame. The motion is new, so the source audio is not in sync with it.
    g = {
     "src": N("LoadVideo", file="${video}"),
     "part": N("Video Slice", video=["src", 0], start_time=0.0, duration="${slice_seconds}", strict_duration=False),
     "comp": N("GetVideoComponents", video=["part", 0]),
     "first": N("ImageFromBatch", image=["comp", 0], batch_index=0, length=1),
     "scale": N("ImageScale", image=["first", 0], upscale_method="lanczos", width="${width}", height="${height}", crop="center"),
     "high": N("UNETLoader", unet_name="wan2.2_fun_camera_high_noise_14B_fp8_scaled.safetensors", weight_dtype="default"),
     "low": N("UNETLoader", unet_name="wan2.2_fun_camera_low_noise_14B_fp8_scaled.safetensors", weight_dtype="default"),
     "shift_h": N("ModelSamplingSD3", model=["high", 0], shift=8.0), "shift_l": N("ModelSamplingSD3", model=["low", 0], shift=8.0),
     "clip": N("CLIPLoader", clip_name="umt5/umt5_xxl_fp8_e4m3fn_scaled.safetensors", type="wan", device="default"),
     "vae": N("VAELoader", vae_name="wan/wan_2.1_vae.safetensors"),
     "pos": N("CLIPTextEncode", clip=["clip", 0], text="${prompt}"), "neg": N("CLIPTextEncode", clip=["clip", 0], text="${negative}"),
     "cam": N("WanCameraEmbedding", camera_pose="${pose}", width="${width}", height="${height}", length="${frames}", speed=1.0, fx=0.5, fy=0.5, cx=0.5, cy=0.5),
     "i2v": N("WanCameraImageToVideo", positive=["pos", 0], negative=["neg", 0], vae=["vae", 0], start_image=["scale", 0], camera_conditions=["cam", 0], width=["cam", 1], height=["cam", 2], length=["cam", 3], batch_size=1),
     "k1": N("KSamplerAdvanced", model=["shift_h", 0], positive=["i2v", 0], negative=["i2v", 1], latent_image=["i2v", 2], add_noise="enable", noise_seed="${seed}", steps=20, cfg=3.5, sampler_name="euler", scheduler="simple", start_at_step=0, end_at_step=10, return_with_leftover_noise="enable"),
     "k2": N("KSamplerAdvanced", model=["shift_l", 0], positive=["i2v", 0], negative=["i2v", 1], latent_image=["k1", 0], add_noise="disable", noise_seed=0, steps=20, cfg=3.5, sampler_name="euler", scheduler="simple", start_at_step=10, end_at_step=10000, return_with_leftover_noise="disable"),
     "dec": N("VAEDecode", samples=["k2", 0], vae=["vae", 0]),
     "mk": N("CreateVideo", images=["dec", 0], audio=["comp", 1], fps=16.0),
     "save": N("SaveVideo", video=["mk", 0], filename_prefix="reshoot/reshoot_wan", format="auto", codec="auto"),
    }
    return g
BUILDS = {"h3_orbit360_api.json": orbit360, "wan_camera_api.json": reshoot_wan, "h3_recast_api.json": recast, "h3_reshoot_api.json": reshoot, "ltx25_vfx_api.json": vfx_ltx, "h3_fl2v_api.json": director_keyframes}
if __name__ == "__main__":
    for name, fn in BUILDS.items():
        with open(os.path.join(WF, name), "w") as f: json.dump(fn(), f, indent=1, ensure_ascii=False)
        print("wrote", name)
