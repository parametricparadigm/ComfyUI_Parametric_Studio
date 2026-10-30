# PROMPTING - 31-Z-Image-Lumina2

## Prompt Structure and Language

**Z-Image Family**
*   **Languages:** The Z-Image family supports text prompts in both English and Chinese. [MODEL.md]
*   **Bilingual Rendering:** Z-Image-Turbo is specifically optimized for rendering English and Chinese text within images. [MODEL.md]
*   **Instruction Adherence:** Z-Image-Turbo is noted for robust instruction adherence. [SOURCES.md: Tongyi-MAI/Z-Image-Turbo]
*   **Editing Instructions:** Z-Image-Edit supports creative image-to-image generation with impressive instruction-following capabilities, allowing for precise edits based on natural language prompts. [SOURCES.md: Tongyi-MAI/Z-Image-Turbo]
*   **Prompt Enhancer:** A "Prompt Enhancer" feature is mentioned that empowers the model with reasoning capabilities, enabling it to transcend surface-level descriptions and tap into underlying world knowledge. [SOURCES.md: Tongyi-MAI/Z-Image-Turbo]

**Lumina-Image-2**
*   **Language:** Not in sources: Specific supported languages for Lumina-Image-2 prompts are not explicitly stated, though the text encoder is `gemma2-2b-fp16.safetensors`. [MODEL.md]

## Prompt Length and Complexity

*   **Z-Image:** The official usage example provides a highly detailed, long-form prompt describing specific subjects, clothing, accessories, poses, lighting, and background elements in Chinese. [SOURCES.md: Tongyi-MAI/Z-Image]
*   **Z-Image-Turbo:** Not in sources: Specific maximum or recommended prompt length limits for Z-Image-Turbo are not stated.
*   **Lumina-Image-2:** Not in sources: Specific prompt length guidelines for Lumina-Image-2 are not stated.

## Negative Prompts

**Lumina-Image-2**
*   **Support:** Not in sources: Whether Lumina-Image-2 supports negative prompts is not stated in the provided material.

## Style and Camera Vocabulary

**Z-Image Family**
*   **Stylistic Coverage:** Z-Image masters a vast spectrum of visual languages, including hyper-realistic photography, cinematic digital art, intricate anime, and stylized illustrations. [SOURCES.md: Tongyi-MAI/Z-Image]
*   **Photorealism:** Z-Image-Turbo excels in photorealistic image generation. [MODEL.md]
*   **Camera/Lighting Terms:** The example prompt for Z-Image includes specific photographic terminology such as "natural light illumination," "soft shadows," "medium depth of field," "focus on face and upper body," and "indoor environment." [SOURCES.md: Tongyi-MAI/Z-Image]
*   **Diversity:** Z-Image delivers significantly higher variability in composition, facial identity, and lighting across different seeds. [SOURCES.md: Tongyi-MAI/Z-Image]

**Lumina-Image-2**
*   **Style Vocabulary:** Not in sources: Specific style or camera vocabulary recommendations for Lumina-Image-2 are not provided.

## Text Encoder Behavior

**Z-Image Family**
*   **Architecture:** Z-Image utilizes a Scalable Single-Stream DiT (S3-DiT) architecture. In this setup, text, visual semantic tokens, and image VAE tokens are concatenated at the sequence level to serve as a unified input stream. [SOURCES.md: Tongyi-MAI/Z-Image-Turbo]
*   **Encoder Model:** The ComfyUI repackaging for Z-Image-Turbo lists `qwen_3_4b.safetensors` (and fp4/fp8 mixed variants) as the text encoder. [SOURCES.md: Comfy-Org/Z-Image-Turbo]
*   **CFG Interaction:** Z-Image (base) supports full Classifier-Free Guidance (CFG), providing precision for complex prompt engineering. Z-Image-Turbo does not use CFG. [SOURCES.md: Tongyi-MAI/Z-Image]

**Lumina-Image-2**
*   **Encoder Model:** Lumina-Image-2 utilizes `gemma2-2b-fp16.safetensors` (Gemma2 2B) as its text encoder. [MODEL.md]
*   **Function:** The text encoder processes prompts for image generation within the ComfyUI ecosystem. [MODEL.md]

## Recommended Settings for Prompting

**Z-Image (Base)**
*   **Guidance Scale:** 3.0 – 5.0. [SOURCES.md: Tongyi-MAI/Z-Image]
*   **Inference Steps:** 28 – 50. [SOURCES.md: Tongyi-MAI/Z-Image]
*   **Resolution:** 512×512 to 2048×2048 (total pixel area, any aspect ratio). [SOURCES.md: Tongyi-MAI/Z-Image]

**Z-Image-Turbo**
*   **Inference Steps:** 8 NFEs (Number of Function Evaluations). [MODEL.md]
*   **CFG:** No CFG. [MODEL.md]
*   **Resolution:** Not in sources: Specific resolution recommendations for Z-Image-Turbo are not stated in the provided text, though a 2K upscaling workflow is mentioned. [MODEL.md]

**Lumina-Image-2**
*   **Settings:** Not in sources: Specific step, CFG, or guidance scale settings for Lumina-Image-2 are not stated in the provided material. [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
