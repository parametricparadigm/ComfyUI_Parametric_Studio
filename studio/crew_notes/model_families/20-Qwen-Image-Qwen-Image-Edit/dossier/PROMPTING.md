# PROMPTING - 20-Qwen-Image-Qwen-Image-Edit

## Prompt Structure and Language
The model supports prompts in both English and Chinese, as indicated by the `language` tags in the model metadata [SOURCES.md]. For text-to-image generation, the official quick start code suggests appending specific "magic" phrases to the end of the prompt to enhance quality. For English prompts, the recommended suffix is `, Ultra HD, 4K, cinematic composition.` For Chinese prompts, the recommended suffix is `, 超清，4K，电影级构图.` [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md].

The model is designed for "complex text rendering," meaning prompts can include specific text strings to be rendered within the image. The documentation highlights that text is "seamlessly integrated into the visual fabric" rather than just overlaid, supporting both alphabetic languages like English and logographic scripts like Chinese [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md].

For image editing tasks, the prompt describes the desired change. Examples from the documentation include specific instructions such as "Change the rabbit's color to purple, with a flash light background." [PUBLIC README https://huggingface.co/Qwen/Qwen-Image-Edit/raw/main/README.md]. The editing model supports both semantic editing (e.g., style transfer, object rotation) and appearance editing (e.g., adding/removing elements) [PUBLIC README https://huggingface.co/Qwen/Qwen-Image-Edit/raw/main/README.md].

## Negative Prompts
The pipeline accepts a `negative_prompt` input. The official documentation for both the base model and the edit model explicitly recommends using an empty string or a space (`" "`) if there are no specific concepts to remove [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md] [PUBLIC README https://huggingface.co/Qwen/Qwen-Image-Edit/raw/main/README.md]. The workflow plan notes that the negative prompt can be an empty string as per the README [WORKFLOW_PLAN.md].

## Text Encoder and Prompt Enhancement
The ComfyUI repackaged models include specific text encoders located in the `text_encoders` folder, including `qwen3vl_8b_bf16.safetensors` and its quantized variants [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md].

Additionally, the family includes "Prompt Enhancer" models named `qwen3.5_9b_qwen_image_2.1_pe` (specifically `qwen3.5_9b_qwen_image_2.1_pe_t2i` and `qwen3.5_9b_qwen_image_2.1_pe_i2i`). These models are intended for prompt enhancement and are to be used with the `Generate Text` node in ComfyUI workflows [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md] [MODEL.md].

## Style and Camera Vocabulary
The documentation states that the model supports a "wide range of artistic styles," including photorealistic scenes, impressionist paintings, anime aesthetics, and minimalist design [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md]. The recommended "magic" prompt suffixes include "cinematic composition" (English) and "电影级构图" (Chinese), suggesting that camera and composition terminology is effective [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md].

## Inference Settings Related to Prompting
While not strictly part of the prompt text, the following settings are paired with the prompt in the official examples:
- **Standard Models**: `true_cfg_scale` is typically set to `4.0` and `num_inference_steps` to `50` [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md] [PUBLIC README https://huggingface.co/Qwen/Qwen-Image-Edit/raw/main/README.md].
- **Turbo Models/LoRAs**: `true_cfg_scale` is set to `1.0` and steps are reduced (5, 6, or 8 steps depending on the LoRA) [MODEL.md] [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md].

## Not in sources
- Specific maximum token length or character limit for prompts.
- Detailed guidelines on prompt length optimization beyond the "magic" suffixes.
- Specific negative prompt vocabulary lists or recommended negative concepts.
- Detailed explanation of how the text encoder processes the prompt internally (e.g., tokenization specifics).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
