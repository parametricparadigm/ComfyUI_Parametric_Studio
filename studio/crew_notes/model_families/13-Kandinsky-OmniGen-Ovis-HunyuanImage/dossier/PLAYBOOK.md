# PLAYBOOK.md: 13-Kandinsky-OmniGen-Ovis-HunyuanImage

## Prompt structure

*   **Style and Format:** Use "style prose" that mimics the training-caption format, which includes tags [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
*   **Speech Integration:** For video generation, speech must be embedded directly within the video caption using the specific syntax `<S>line<E>` [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Audio Separation:** Non-speech sounds (e.g., ambient noise, traffic) should be described in the audio caption, distinct from the speech tags [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Negative Prompts:** Negative prompts are ignored for distilled models because they use PiFlow with CFG 1.0 [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
*   **Example Structure:** A valid prompt combines visual description, camera movement, and audio cues. Example: "A woman in a red coat walks through a snowy park at dusk while warm street lamps switch on one by one; slow tracking shot from the side, ending on her face as she smiles; soft crunch of snow and distant traffic." [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].

## Words and phrasing that work

*   **Camera Directions:** Specific camera movements such as "slow tracking shot from the side" are effective in describing motion [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Audio Descriptors:** Descriptive phrases for ambient sound like "soft crunch of snow and distant traffic" work well in the audio caption [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Speech Tags:** The exact tags `<S>` and `<E>` are required to delimit spoken lines within the video caption [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Not in notes:** Specific keywords for style (e.g., "cinematic," "photorealistic") or subject-specific vocabulary beyond the generic example are not listed in the provided documents.

## Settings that worked

*   **Resolution:** Native resolution is 864x480 (landscape). Width and height must be multiples of 16 [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Frame Count:** 121 frames is the standard length, corresponding to 5 seconds at 24 fps. Frame counts must follow the pattern 4n+1 [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Sampling (Distilled Pro/Lite):** Use the `Kandinsky6Sampler` (PiFlow) with 10 steps and CFG 1.0 [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_pro_distill_int8_convrot.md].
*   **Sampling (Non-Distilled Lite):** Use standard `KSampler` with `euler` sampler, `simple` scheduler, 50 steps, CFG 5, and denoise 1 [k6_lite_int8_convrot.md].
*   **Audio VAE Scaling:**
    *   For Distilled models: `scaling_factor` 0.417 (model_variant `pretrain / distill`) [k6_pro_distill_int8_convrot.md].
    *   For Non-Distilled Lite: `scaling_factor` 0.5302 (model_variant `base`) [k6_lite_int8_convrot.md].
*   **Text Encoders:** Use `DualCLIPLoader` with `qwen_2.5_vl_7b` and `clip-vit/clip_l` (type `kandinsky5`) [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **VAE:** Use `hunyuan_video_vae_bf16.safetensors` for video and `Kandinsky6AudioVAELoader` with `v1-44.pth` + `bigvgan_vocoder` for audio [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **VRAM Budget:**
    *   Distilled Pro: ~64 GB budget on the port (35 GB DiT + 16.6 GB TE + activations) [k6_pro_distill_int8_convrot.md].
    *   Non-Distilled Lite: ~34 GB budget on the port [k6_lite_int8_convrot.md].
    *   General Rule: Keep ≥ 4 GB free VRAM [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].

## Processes built on it

*   **ComfyUI Workflow:** The primary process uses the `Comfyui-Kandinsky-T8` pack across ports :8191, :8189, and :8190 [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Image-to-Video (I2V) Pipeline:**
    1.  Load Image.
    2.  Scale Image to 864x480 (center).
    3.  `VAEEncode`.
    4.  `Kandinsky6ImageToVideoAudio`.
    5.  After sampling, use `Kandinsky6RemoveReferenceLatent` to feed both decoders [k6_lite_int8_convrot.md].
*   **Standalone Runner:** A standalone runner located at `~/tools/kandinsky-6` can render the bf16 Pro distill, peaking at ~68 GiB [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Super-Resolution (Optional):** A separate `kandinsky6-sr` pack can be used for super-resolution (x2, x4, or x2.25), though it is not installed by default in the base workflows [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [README.md].
*   **Workflow Starting Point:** For int8 Lite models, start from the pack's `K6 INT8 Base` workflows [k6_lite_int8_convrot.md].

## What to avoid

*   **Pack Conflicts:** Do not enable `ComfyUI-Kandinsky6` alongside `Comfyui-Kandinsky-T8` as they register the same node names; the old pack should remain `.disabled` [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Audio VAE Path:** Ensure `kandinsky6_audio_vae` reads from `ComfyUI/models/audio_vae`. If missing, `Kandinsky6AudioVAELoader` will fail with 'v1-44.pth not found' *after* sampling, even if the dropdown shows the file [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Merging Quantized Files:** Do not use an int8 file as a merge input; merge in bf16 first, then quantize [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md] [k6_lite_int8_convrot.md] [k6_pro_distill_int8_convrot.md].
*   **Sampler Mismatch:**
    *   Do not run non-distilled Lite models with `Kandinsky6Sampler` (PiFlow) or CFG 1; that is the recipe for distilled models [k6_lite_int8_convrot.md].
    *   Do not add `Kandinsky6MagCache` to Lite models; it is calibrated for Pro only and will raise an error on Lite [k6_lite_int8_convrot.md].
    *   Do not add `Kandinsky6MagCache` to Distilled Pro; it auto-bypasses or is dropped by PiFlow [k6_pro_distill_int8_convrot.md].
*   **VRAM Overload:** Do not load Distilled Pro (35 GB file, ~64 GB port usage) beside `llama.cpp` :8091 (~50 GB) without checking free VRAM [k6_pro_distill_int8_convrot.md].
*   **Known Failure Modes:**
    *   "Beautifier" tag mangling can cause speech drift (e.g., repeating words) [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
    *   Forced portrait orientation on Text-to-Video (T2V) looks wrong [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
    *   Object permanence issues (e.g., hanger vanishing) and face drift in I2V have been observed [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
    *   "Product orbit" prompts may result in a dolly shot instead [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
    *   Light shifts mid-clip are a known weakness [Kandinsky-6.0-Pro-distill-5s-Diffusers/MODEL.md].
*   **Not in notes:** Specific negative prompt phrases to avoid (since they are ignored for distilled models) or specific hardware driver versions are not detailed in the provided notes.
