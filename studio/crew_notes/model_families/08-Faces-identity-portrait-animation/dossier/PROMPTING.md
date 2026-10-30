# PROMPTING - 08-Faces-identity-portrait-animation

## Prompt Structure and Inputs
The LongCat-Video-Avatar 1.5 model supports three native tasks that define how prompts are structured: Audio-Text-to-Video (AT2V), Audio-Text-Image-to-Video (ATI2V), and Video Continuation [MODEL.md]. For AT2V and ATI2V tasks, the model accepts text prompts as inputs alongside audio [MODEL.md]. In ATI2V tasks, reference images are also accepted as inputs to condition the generation [MODEL.md]. The InstantCharacter pipeline requires a text prompt and a reference image for identity to generate images with preserved identity [MODEL.md].

## Text Encoder and Processing
The text encoder for the LongCat-Avatar-15 pipeline is `umt5_xxl_fp8_e4m3fn_scaled.safetensors`, which is a UMT5-XXL text encoder [MODEL.md]. This encoder processes the text prompts to condition the diffusion model [MODEL.md]. The workflow involves using a `CLIPLoader` to load the text encoder and a `CLIPTextEncode` node to encode the text prompt, connecting the `CONDITIONING` output to the sampler [WORKFLOW_PLAN.md].

## Language
The model supports prompts in English and Chinese, as indicated by the language tags `en` and `zh` in the model metadata [SOURCES.md]. The human evaluation benchmark for LongCat-Video-Avatar 1.5 specifically tests performance across these two languages [SOURCES.md].

## Style and Domain Vocabulary
The model generalizes to specific visual styles and domains, which can be implied or specified in prompts. These include anime, animals, and complex real-world conditions such as multi-person interactions and object handling [SOURCES.md]. Application scenarios supported by the model include broadcasting, acting, singing, e-commerce marketing, multi-person conversation, animation, and animal characters [SOURCES.md]. The evaluation benchmark distinguishes between Realistic and Animated visual styles [SOURCES.md].

## Negative Prompts
Not in sources: specific guidance on negative prompts or their usage for this model family.

## Prompt Length
Not in sources: specific recommendations for prompt length or character limits.

## Camera and Technical Vocabulary
Not in sources: specific camera vocabulary or technical terms required for prompting.

## Other Models
*   **LivePortrait**: Does not use text prompts; it animates static portraits using motion and appearance features from a source video and target image [MODEL.md].
*   **MuseTalk**: Generates talking head frames conditioned on audio and face inputs; it does not explicitly list text prompts as a primary input for frame generation, though a Whisper Tiny model is present for captioning [MODEL.md].
*   **Face Swapping/Restoration**: Models like InsightFace InSwapper, CodeFormer, and GFPGAN perform direct face replacement or restoration and do not rely on text prompts for their core function [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
