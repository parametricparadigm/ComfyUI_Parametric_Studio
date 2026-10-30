# PROMPTING - 29-Wan-2.1

## Prompt Structure and Content
The Wan 2.1 family accepts text prompts for both Text-to-Video and Image-to-Video tasks [MODEL.md]. The prompts are designed to describe the visual content, motion, and style of the generated video. For example, a Text-to-Video prompt might describe characters, actions, and settings such as "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage" [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B]. An Image-to-Video prompt can include detailed descriptions of the scene, subject, and atmosphere, such as "Summer beach vacation style, a white cat wearing sunglasses sits on a surfboard... A close-up shot highlights the feline's intricate details and the refreshing atmosphere of the seaside" [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P].

The model is capable of generating both Chinese and English text within the video content, making it the first video model to support this feature [MODEL.md].

## Prompt Extension
The system supports a prompt extension step to enhance generation quality by enriching details in the generated videos [MODEL.md]. This step is optional; basic inference can skip it [MODEL.md].

Two methods for prompt extension are provided:
1.  **Dashscope API**: Uses the `qwen-plus` model for text-to-video tasks and `qwen-vl-max` for image-to-video tasks. This requires setting the `DASH_API_KEY` environment variable [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B].
2.  **Local Model**: Uses `Qwen/Qwen2.5-VL-7B-Instruct` for local prompt extension, particularly demonstrated for Image-to-Video tasks [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P].

The parameter `--use_prompt_extend` enables this feature, and `--prompt_extend_model` allows specifying the model used for extension [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B].

## Language
The model supports prompts in English and Chinese, as indicated by the `language` tags in the model metadata (`en`, `zh`) [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B].

## Negative Prompts
Not in sources: Specific guidance on negative prompts or their usage in the Wan 2.1 pipeline. The workflow plans note that no negative prompt node is explicitly listed in the available nodes for the specific flow, suggesting standard negative encoding may be required but is not detailed [WORKFLOW_PLAN.md].

## Style and Camera Vocabulary
Prompts can include descriptive vocabulary for style, camera angles, and atmosphere. The Image-to-Video example uses terms like "Summer beach vacation style," "close-up shot," "blurred beach scenery," and "relaxed expression" [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P]. The Text-to-Video example uses "spotlighted stage" and "intensely" to describe lighting and action [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B].

## Text Encoder
The text encoder used for processing prompts is `umt5_xxl_fp16.safetensors` or its quantized version `umt5_xxl_fp8_e4m3fn_scaled.safetensors` [MODEL.md]. The encoder can be offloaded to CPU using the `--t5_cpu` option to reduce GPU memory usage [MODEL.md].

## Inference Parameters Affecting Prompting
While not strictly part of the prompt text, the following parameters influence how the prompt is interpreted and generated:
-   **Guide Scale**: For the `T2V-1.3B` model, a `--sample_guide_scale` of 6 is recommended [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B].
-   **Sample Shift**: For the `T2V-1.3B` model, the `--sample_shift` parameter can be adjusted within the range of 8 to 12 [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B].
-   **Inference Steps**: Typically 10 steps for basic inference [MODEL.md].

## Not in Sources
-   Specific prompt length limits or token counts.
-   Detailed syntax rules or weighting syntax (e.g., `(word:1.2)`).
-   Specific negative prompt examples or recommended negative prompt strings.
-   Detailed internal processing of the text encoder beyond its file name and offloading options.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
