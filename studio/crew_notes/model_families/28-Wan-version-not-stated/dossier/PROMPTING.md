# PROMPTING - 28-Wan-version-not-stated

## Prompt Structure and Language
*   **Supported Languages**: The models accept text prompts in both English and Chinese. [MODEL.md]
*   **Prompt Extension**: The sources recommend enabling prompt extension to enrich details and enhance video quality. This can be done via the Dashscope API (using `qwen-plus` for T2V and `qwen-vl-max` for I2V) or local models (such as `Qwen/Qwen2.5-14B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `Qwen/Qwen2.5-3B-Instruct`, or `Qwen/Qwen2.5-VL-7B-Instruct`). [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md] [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P/raw/main/README.md] [PUBLIC README https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]
*   **Visual Text Generation**: The Wan2.1 family is capable of generating both Chinese and English text within the video. [MODEL.md] [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

## Prompt Length and Style
*   **Length**: Not in sources: Specific character or token limits for prompts.
*   **Style Vocabulary**: Wan2.2 is trained on curated aesthetic data with detailed labels for lighting, composition, contrast, and color tone, allowing for precise and controllable cinematic style generation. [PUBLIC README https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]
*   **Camera Vocabulary**: Not in sources: Specific camera movement or angle vocabulary guidelines.

## Negative Prompts
*   **Usage**: The workflow plans indicate that `CLIPTextEncode` nodes are used to encode both positive and negative prompts, with the conditioning connected to the sampler. [WORKFLOW_PLAN.md]
*   **Guidance**: Not in sources: Specific recommendations on what to include in negative prompts or whether they are strictly required for optimal performance.

## Text Encoder Behavior
*   **Encoder Type**: The models utilize a T5 text encoder. The `--t5_cpu` flag is available to move the T5 text encoder to the CPU to save VRAM. [MODEL.md] [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
*   **Processing**: The text encoder processes the prompt (and optionally the extended prompt) to generate conditioning for the diffusion model. [WORKFLOW_PLAN.md]
*   **Specific Encoder File**: Not in sources: The specific filename of the T5 text encoder used in the local installation is not listed in the provided model files or workflow plans. [WORKFLOW_PLAN.md]

## Inference Parameters Affecting Prompting
*   **Guidance Scale**: The `--sample_guide_scale` parameter controls generation dynamics. For the `T2V-1.3B` model, a value of `6` is recommended. [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
*   **Shift**: The `--sample_shift` parameter can be adjusted within the range of `8` to `12` based on performance. [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
*   **Inference Steps**: The default `num_inference_steps` is `10` for some variants, but this can be adjusted. [MODEL.md] [PUBLIC README https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
