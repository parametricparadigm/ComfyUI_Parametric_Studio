# PLAYBOOK.md: 12-HunyuanVideo-FramePack

## Prompt structure

*   **Style:** Use "style prose." For Image-to-Video (I2V) tasks, describe the **change** or motion, not just the static picture [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].
*   **Detail Level:** The model is "prompt-hungry." Short prompts underperform, and detailed prompting is required for best results [HUNYUANVIDEO15_PROMPTING.md].
*   **Text Rendering:** To render text within the video (English or Chinese), put the text in quotes. This utilizes the byT5 glyph encoder [HUNYUANVIDEO15_PROMPTING.md].
*   **Negative Prompt:** Leave the negative prompt **empty**. At CFG 1.0, the negative pass is skipped, so a negative prompt does nothing [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Example:**
    ```text
    A red kite rises over a grassy hill on a windy afternoon, the camera tilting up to follow it against fast clouds.
    ```
    [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md]

## Words and phrasing that work

*   **Motion Descriptors:** Phrases describing "alive" realistic micro-motion such as hair, cloth, and expressions work well [HUNYUANVIDEO15_PROMPTING.md].
*   **Camera Instructions:** While you can include camera moves in the prompt (e.g., "camera tilting up"), the model often ignores these requests and defaults to a static camera [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Style Keywords:** The model supports realistic, anime, 2D, 3D, low-poly, and ink-wash styles [HUNYUANVIDEO15_PROMPTING.md].
*   **Not in notes:** Specific magic words or trigger phrases for specific character identities or complex physics interactions are not listed in the provided documents.

## Settings that worked

*   **Sampler/Scheduler:** `euler` sampler with `simple` scheduler [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Steps:** **50 steps** is the official requirement for the cfg-distilled model to generate correct results. The template ships with 20, but 50 is recommended [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **CFG:** **1.0** (cfg-distilled) [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Shift:** **7.0** for 720p I2V [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Resolution:** **1280x720** is the native and best-performing resolution ("by far best at 1280x720") [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Frames/FPS:** **121 frames** at **24 fps** (5 seconds). Use frame counts that are 4n+1 [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Loaders:**
    *   **UNET:** `UNETLoader` with weight_dtype `default` (file is already fp8_scaled) [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].
    *   **Text Encoder:** `DualCLIPLoader` type `hunyuan_video_15` using `qwen_2.5_vl_7b` (bf16) and `byt5_small_glyphxl_fp16` [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
    *   **VAE:** `hunyuanvideo15_vae_fp16` [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].
    *   **CLIP Vision:** `sigclip_vision_patch14_384` [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **VAE Decode:** If using `VAEDecodeTiled`, set `temporal_size` to **4096** (max) to avoid artifacts [HUNYUANVIDEO15_PROMPTING.md].
*   **VRAM:** Approximately 30 GB peak VRAM is estimated. Keep at least 4 GB free on the GPU [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].

## Processes built on it

*   **Super-Resolution (SR):**
    *   **480p to 720p:** Use `hunyuanvideo1.5_720p_sr_distilled_fp8_scaled` with the matching latent upsampler [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].
    *   **720p to 1080p:** Use `hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled` with the matching latent upsampler. Note: This is untested on the box and adds potential artifacts [hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Drafting/Speed:**
    *   **480p Step-Distilled:** Use `hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled` for faster drafts (8 steps). This produces 480p output which requires SR for delivery [hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.md].
*   **Saved Workflows:**
    *   the ComfyUI workflows folder
    *   the ComfyUI workflows folder
    *   the ComfyUI workflows folder
    *   the ComfyUI workflows folder
    *   the ComfyUI workflows folder
    *   the ComfyUI workflows folder
    [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.md, hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.md]

## What to avoid

*   **Reducing Steps:** Do not cut steps below 50 for the cfg-distilled 720p model. Running at 6 steps causes "smearing" [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Short Prompts:** Avoid short prompts as they underperform significantly [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Complex Physics/Action:** Avoid relying on this model for complex physics or fast action, as Wan 2.2 is rated better for these tasks [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Camera Moves:** Do not expect requested camera moves to be followed; the model often defaults to a static camera [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, HUNYUANVIDEO15_PROMPTING.md].
*   **Merging Weights:** Do not use this quantized (fp8_scaled) file as a merge input. Merge bf16/fp16 weights first, then quantize [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md, hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.md].
*   **Untiled VAE Decode:** Avoid untiled VAE decode if VRAM is tight, as it can drop free VRAM to critical levels (4.7 GB observed). Use tiled decode with temporal 4096 [hunyuanvideo1.5_720p_i2v_cfg_distilled_fp8_scaled.md].
*   **Cache Nodes:** `EasyCache` is bypassed by default and lowers quality. Avoid using it unless necessary [HUNYUANVIDEO15_PROMPTING.md].
*   **Not in notes:** Specific audio generation capabilities are not supported (no native audio), and specific licensing restrictions for commercial use beyond the "Tencent Hunyuan Community" license (EU/UK/KR excluded) are not detailed further in the notes [HUNYUANVIDEO15_PROMPTING.md, hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.md].
