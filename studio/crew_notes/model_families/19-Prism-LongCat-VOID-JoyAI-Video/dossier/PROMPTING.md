# PROMPTING - 19-Prism-LongCat-VOID-JoyAI-Video

## Prompt Structure and Content
*   **Descriptive Detail:** For LongCat-Video-Avatar 1.5, longer, more descriptive prompts yield better consistency and naturalness than short ones. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Required Elements:** Prompts should include rich details such as character appearance, actions, and scene context. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Example:** A recommended prompt structure is: *"A young woman with long black hair is speaking and smiling, wearing a white blouse, sitting in a bright café"*. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Input Type:** Text prompts are provided via `STRING` inputs in the ComfyUI workflows for Prism-Alpha, LongCat-Avatar-15, and JoyAI-Video-Edit. [WORKFLOW_PLAN.md]

## Language
*   **Supported Languages:** The models support English and Chinese. [SOURCES.md]
*   **Evaluation Context:** The LongCat-Video-Avatar 1.5 benchmark encompasses 2 languages (Chinese/English). [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

## Negative Prompts
*   Not in sources: Specific guidance on negative prompts or their usage for this model family.

## Style and Camera Vocabulary
*   **Stylized Domains:** LongCat-Video-Avatar 1.5 generalizes to anime, animals, and complex real-world conditions such as multi-person interactions and object handling. [MODEL.md]
*   **Application Scenarios:** Supported scenarios include broadcasting, acting, singing, e-commerce marketing, multi-person conversation, animation, and animal characters. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Visual Styles:** The evaluation benchmark covers Realistic and Animated visual styles. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   Not in sources: Specific camera angle, lens, or cinematography vocabulary recommendations.

## Text Encoder Behavior
*   **LongCat-Avatar-15:** Uses `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (UMT5-XXL, 5.7B params, fp8) to encode text prompts for avatar generation. [LOCAL_MODELS.tsv]
*   **LongCat-Image:** Uses a Qwen2.5-VL 7B text encoder (bf16) to encode text prompts for image generation. [LOCAL_MODELS.tsv]
*   **Prism-Alpha:** Uses a text encoder (`text_encoder.safetensors`, mixed precision) to encode text prompts into embeddings for the generation pipeline. [LOCAL_MODELS.tsv]
*   **JoyAI-Video-Edit:** Uses a multi-part text encoder (components `model-00001-of-00004.safetensors` through `model-00004-of-00004.safetensors`) to condition the large DiT for video editing. [MODEL.md]
*   **General Role:** All models rely on text encoders for prompt conditioning. [MODEL.md]

## Additional Prompting-Related Settings
*   **Audio CFG:** For LongCat-Video-Avatar 1.5, Audio CFG works optimally between 3–5. Increasing the audio CFG value improves lip synchronization accuracy. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Reference Image Index:** Setting the reference image index (`--ref_img_index`, default 10) between 0 and 24 ensures better consistency; setting it to 30 helps reduce repeated actions. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Mask Frame Range:** Increasing the mask frame range (`--mask_frame_range`, default 3) can help mitigate repeated actions, but excessively large values may introduce artifacts. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Resolution:** The model is compatible with 480P and 720P, controlled via `--resolution`. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
*   **Dual-Audio Modes:**
    *   **Merge mode:** Set `audio_type` to `para`. Requires two audio clips of equal length; resulting audio is the sum of the two clips. [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]
    *   **Concatenation mode:** Set `audio_type` to `add`. Does not require equal-length inputs; resulting audio is sequentially concatenated with silence padding for gaps (person1 speaks first, then person2). [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
