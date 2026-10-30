# PLAYBOOK.md: 11-HiDream

## Prompt structure

*   **Use natural language prose.** The model uses an LLM encoder (Gemma-based CLIP from the checkpoint), so prompts should be written as descriptive sentences rather than comma-separated tags. [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [CHARACTER_BUILDER_MODELS.md]
*   **Keep the negative prompt empty.** For the full bf16 model used in the studio, the negative prompt is explicitly set to an empty string (`""`). [image-hidream-anime.md]
*   **Name specific visual elements.** When generating anime or illustration styles, explicitly name the desired elements such as "key-frame," "speed lines," "cel shading," or "line weight." [image-hidream-anime.md]
*   **For character anchors, use a standardized portrait description.** The character builder uses a specific prompt structure: "clean, front-facing, evenly lit head-and-shoulders portrait, plain light grey background, neutral expression." [CHARACTER_BUILDER_MODELS.md]
*   **Do not use the optional TextGenerate rewriter.** The template includes a rewriter node, but it is not downloaded/active; prompts must be fed straight to `CLIPTextEncode`. [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]

## Words and phrasing that work

*   **"Prose" style.** The rules page for the model specifies `prompt_style prose`. [image-hidream-anime.md]
*   **Anime-specific terminology.** Words like "key-frame," "speed lines," "cel shading," and "line weight" are cited as effective for achieving the anime/illustration look. [image-hidream-anime.md]
*   **Standardized character look.** For character consistency, the phrasing "clean, front-facing, evenly lit head-and-shoulders portrait, plain light grey background, neutral expression" is the tested standard. [CHARACTER_BUILDER_MODELS.md]
*   **Not in notes:** Specific trigger words or "magic words" unique to HiDream are not listed in the provided documents, other than the general instruction to use natural language and name specific visual elements.

## Settings that worked

**Full Model (bf16) - Recommended for Quality/Anime:**
*   **Model File:** `hidream_o1_image_bf16.safetensors` [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [image-hidream-anime.md]
*   **Steps:** 40 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [image-hidream-anime.md]
*   **Sampler:** `dpmpp_2m_sde_gpu` [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [image-hidream-anime.md]
*   **Scheduler:** `normal` [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [image-hidream-anime.md]
*   **CFG:** 5 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md] [image-hidream-anime.md]
*   **Noise Scale:** 8 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Seam Smoothing:** Start 0.8, End 1.0, Pattern `single_shift`, Passes `ramp_2_4`, Blend `median`, Strength 1 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Negative Prompt:** `""` (Empty) [image-hidream-anime.md]
*   **Latent:** `EmptyHiDreamO1LatentImage` (dimensions must be multiples of 32) [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Tested Sizes:** 1728x2304 (3:4), 2048x2048 (1:1), 2304x1728 (4:3) [image-hidream-anime.md]
*   **Default Seed:** 4242 [image-hidream-anime.md]

**Dev Model (fp8) - Distilled/Faster:**
*   **Model File:** `hidream_o1_image_dev_fp8_scaled.safetensors` [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Steps:** 28 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Sampler:** `SamplerLCM` (s_noise 1, s_noise_end 1, noise_clip_std 2.5) [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Scheduler:** `BasicScheduler` normal [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **CFG:** 1 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Noise Scale:** 7.6 [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Negative Prompt:** `""` (Empty) [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]
*   **Latent:** `EmptyHiDreamO1LatentImage` [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]

**General:**
*   **VRAM:** The full bf16 model peaks at 22 GiB in code, requiring 26 GiB free VRAM. [image-hidream-anime.md]
*   **Speed:** ~25 seconds per image for the full model. [image-hidream-anime.md]

## Processes built on it

*   **Anime / Illustration Generation:** A dedicated studio entry (`img:anime`) uses the Full bf16 model to generate anime key-frames and illustrations at 2048-class resolution. It is optimized for speed lines and clean line art. [image-hidream-anime.md]
*   **Character Builder Anchor:** HiDream is one of the models used to generate the initial "anchor" headshot for character sheets. It uses the standardized portrait prompt and specific size selection (closest to 3:4 aspect ratio). [CHARACTER_BUILDER_MODELS.md]
*   **Reference Image Support:** The model supports up to 10 reference images via the `HiDreamO1ReferenceImages` node, allowing for image-to-image or reference-based generation. [NEW_IMAGE_MODELS_BRIEF_2026-10-09.md]

## What to avoid

*   **Do not use the Dev (fp8) model for text-heavy prompts.** The Dev model is noted to produce "garbled text" on specific test prompts (S01). The studio uses the Full bf16 model to avoid this. [image-hidream-anime.md]
*   **Do not use unsupported aspect ratios.** The studio only offers 3:4, 1:1, and 4:3. Requests for 9:16 or 16:9 are refused by the system. [image-hidream-anime.md]
*   **Do not rely on the default seed for variations.** Generating twice with the same prompt and default seed (4242) returns the cached file. Use the "Variations" feature to get new results. [image-hidream-anime.md]
*   **Do not use LoRAs in the studio.** There is no `lora_library` family configured for HiDream entries in the studio. [image-hidream-anime.md]
*   **Do not use tag-based prompting.** Unlike SDXL or Anima, HiDream expects natural language prose, not booru-style tags. [CHARACTER_BUILDER_MODELS.md]
*   **Do not ignore VRAM requirements.** The full model requires significant VRAM (26 GiB free). [image-hidream-anime.md]
