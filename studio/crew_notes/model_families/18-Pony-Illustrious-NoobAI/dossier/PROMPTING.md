# PROMPTING - 18-Pony-Illustrious-NoobAI

## Prompt Structure and Templates

### Pony Diffusion V6 XL
The model utilizes a specific prompt structure that includes quality scores and source tags to guide generation [MODEL.md]. The recommended default prompt template is:
`score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up, just describe what you want, tag1, tag2` [LyliaEngine/Pony_Diffusion_V6_XL README].

*   **Quality Modifiers**: The full string `score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up` is required for optimal quality. While `score_9` alone can be used, it has a much weaker effect compared to the full string due to a training issue [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Data Selection Tags**: Optional tags include `source_pony`, `source_furry`, `source_cartoon`, and `source_anime` [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Rating Tags**: Optional tags include `rating_safe`, `rating_questionable`, and `rating_explicit` [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Pony Style Specifics**: For pony-specific styles, the recommended templates are `anthro/feral pony, rest of the prompt` or `source_pony, rest of the prompt` [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Trigger Words**: The model uses `None` as the trigger word [LyliaEngine/Pony_Diffusion_V6_XL README].

### SDXL Base and SDXL-Turbo
These models accept standard natural language text prompts without specific mandatory template prefixes [stabilityai/stable-diffusion-xl-base-1.0 README]. Example prompts from sources include "An astronaut riding a green horse" and "A cinematic shot of a baby racoon wearing an intricate italian priest robe." [stabilityai/stable-diffusion-xl-base-1.0 README, stabilityai/sdxl-turbo README].

## Prompt Language and Content

*   **Natural Language vs. Tags**: Pony Diffusion V6 XL is trained on a combination of natural language prompts and tags and is capable of understanding both. Describing the intended result using normal language works in most cases, although adding tags after the main prompt can boost them [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Character Recognition**: Pony Diffusion V6 XL is capable of recognizing many popular and obscure characters and series [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Style and Aesthetics**: The model supports a wide array of styles and aesthetics [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **Limitations**: The model cannot render legible text [stabilityai/stable-diffusion-xl-base-1.0 README, stabilityai/sdxl-turbo README]. It may struggle with compositionality tasks (e.g., "A red cube on top of a blue sphere") [stabilityai/stable-diffusion-xl-base-1.0 README].

## Negative Prompts

*   **Pony Diffusion V6 XL**: The model is designed to not need negative prompts in most cases [LyliaEngine/Pony_Diffusion_V6_XL README]. It does not need other quality modifiers like "hd" or "masterpiece" [LyliaEngine/Pony_Diffusion_V6_XL README]. Note: The model may generate pseudo-signatures that are hard to remove even with negative prompts [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **SDXL-Turbo**: This model does not make use of `negative_prompt` [stabilityai/sdxl-turbo README].
*   **SDXL Base**: The sources do not explicitly state whether negative prompts are required or recommended for the base model, though standard pipelines often include them. Not in sources: Specific negative prompt requirements for SDXL Base.

## Text Encoder and Clip Skip

*   **Text Encoders**: SDXL models (Base, Turbo, and derivatives like Pony) use two fixed, pretrained text encoders: OpenCLIP-ViT/G and CLIP-ViT/L [stabilityai/stable-diffusion-xl-base-1.0 README].
*   **Clip Skip Requirement**: Pony Diffusion V6 XL must be loaded with clip skip 2 (or -2 in some software) to avoid low-quality results (described as "low quality blobs") [LyliaEngine/Pony_Diffusion_V6_XL README, MODEL.md].
*   **Not in sources**: Specific clip skip requirements for SDXL Base or SDXL-Turbo.

## Generation Settings Affecting Prompting

While not strictly part of the text prompt, these settings are critical for the prompt to function as intended:

*   **Pony Diffusion V6 XL**:
    *   **Sampler**: Euler a is recommended [LyliaEngine/Pony_Diffusion_V6_XL README].
    *   **Steps**: 25 steps are recommended [LyliaEngine/Pony_Diffusion_V6_XL README].
    *   **Resolution**: 1024px is recommended, though the model can handle most supported SDXL resolutions [LyliaEngine/Pony_Diffusion_V6_XL README].
*   **SDXL-Turbo**:
    *   **Guidance Scale**: Must be set to 0.0 (disabled) [stabilityai/sdxl-turbo README].
    *   **Steps**: 1 to 4 steps are sufficient, with 1 step often enough for high quality [stabilityai/sdxl-turbo README].
    *   **Resolution**: 512x512 is preferred, though higher sizes work [stabilityai/sdxl-turbo README].

## Not in Sources

*   Specific prompt length limits or token counts.
*   Detailed internal mechanics of how the text encoder processes the prompt beyond the identification of the encoder models (OpenCLIP-ViT/G and CLIP-ViT/L).
*   Specific negative prompt strings recommended for SDXL Base.
*   Guidance scale recommendations for Pony Diffusion V6 XL or SDXL Base.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
