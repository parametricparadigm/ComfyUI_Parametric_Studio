# PROMPTING - 11-HiDream

## Prompt Structure and Language
*   **Language**: The `HiDream-I1` model is tagged with the language `en` [https://huggingface.co/HiDream-ai/HiDream-I1-Full].
*   **Structure**: The sources do not specify a required prompt structure (e.g., comma-separated tags vs. natural language sentences) for the `HiDream-I1` series.
*   **Structure (O1-Image)**: The `HiDream-O1-Image` model supports "long-text rendering" and "layout control," implying prompts can contain specific text strings to be rendered and layout instructions [https://huggingface.co/HiDream-ai/HiDream-O1-Image].
*   **Editing Prompts**: For `HiDream-E1.1` and `HiDream-O1-Image` editing tasks, the input is described as an "instruction" or "text prompt (instruction)" [WORKFLOW_PLAN.md].

## Prompt Length
*   Not in sources: Specific maximum or recommended prompt length limits for `HiDream-I1` or `HiDream-O1-Image`.

## Negative Prompts
*   Not in sources: Usage of negative prompts for `HiDream-I1` or `HiDream-O1-Image`. The provided inference scripts and node workflows do not list a negative prompt input [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md, WORKFLOW_PLAN.md].

## Style and Camera Vocabulary
*   **Styles**: `HiDream-I1` is documented to produce results across multiple styles including "photorealistic, cartoon, artistic, and more" [https://huggingface.co/HiDream-ai/HiDream-I1-Full].
*   **Camera Vocabulary**: Not in sources: Specific camera angle or lens vocabulary recommendations.

## Text Encoder Behavior
*   **HiDream-I1 Series**:
    *   This series relies on external components for text encoding [MODEL.md].
    *   It uses `google/t5-v1_1-xxl` for one text encoder and `meta-llama/Meta-Llama-3.1-8B-Instruct` for another text encoder [MODEL.md].
    *   In the ComfyUI repackaged files, the text encoders are listed as `clip_g_hidream.safetensors`, `clip_l_hidream.safetensors`, `llama_3.1_8b_instruct_fp8_scaled.safetensors`, and `t5xxl_fp8_e4m3fn_scaled.safetensors` [https://huggingface.co/Comfy-Org/HiDream].
    *   The inference script automatically downloads `meta-llama/Meta-Llama-3.1-8B-Instruct` model files [https://huggingface.co/HiDream-ai/HiDream-I1-Full].
*   **HiDream-O1-Image Series**:
    *   This model is a "natively unified image generative foundation model built on a Pixel-level Unified Transformer (UiT)" [https://huggingface.co/HiDream-ai/HiDream-O1-Image].
    *   It does **not** use external VAEs or disjoint text encoders [MODEL.md].
    *   It "natively encodes raw pixels, text, and task-specific conditions in a single shared token space" [https://huggingface.co/HiDream-ai/HiDream-O1-Image].
    *   It supports a "Reasoning-Driven Prompt Agent" that "resolves implicit knowledge, layout, and text rendering before generation" [https://huggingface.co/HiDream-ai/HiDream-O1-Image].
    *   A specific "prompt refiner" model (`HiDream-ai/Prompt-Refine`) was open-sourced for the `HiDream-O1-Image-Dev-2604` variant, tailored for text-to-image generation [https://huggingface.co/HiDream-ai/HiDream-O1-Image].

## Inference Settings Related to Prompting
*   **Guidance Scale**:
    *   `HiDream-I1-Full`: `guidance_scale=5.0` [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   `HiDream-I1-Dev`: `guidance_scale=0.0` [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   `HiDream-I1-Fast`: `guidance_scale=0.0` [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   Not in sources: Specific guidance scale values for `HiDream-O1-Image` or `HiDream-E1.1` in the provided text.
*   **Inference Steps**:
    *   `HiDream-I1-Full`: 50 steps [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   `HiDream-I1-Dev`: 28 steps [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   `HiDream-I1-Fast`: 16 steps [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
    *   `HiDream-O1-Image`: 50 steps [https://huggingface.co/HiDream-ai/HiDream-O1-Image].
    *   `HiDream-O1-Image-Dev`: 28 steps [https://huggingface.co/HiDream-ai/HiDream-O1-Image].

## Example Prompts
*   **HiDream-I1**: `'A cat holding a sign that says "HiDream.ai".'` [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md].
*   **HiDream-O1-Image**: Not in sources: Specific example prompt strings for `HiDream-O1-Image` are not provided in the text, though it supports "long-text rendering" and "subject-driven personalization" [https://huggingface.co/HiDream-ai/HiDream-O1-Image].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
