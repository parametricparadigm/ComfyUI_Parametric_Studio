# PROMPTING - 30-Wan-2.2

## Prompt Structure and Content
*   **Descriptive Detail**: Prompts should include detailed descriptions of the scene, subjects, and actions. The official examples demonstrate the use of long, descriptive sentences that specify subject appearance, action, background, and atmosphere. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B] [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Cinematic Vocabulary**: The model is trained on curated aesthetic data with labels for lighting, composition, contrast, and color tone. Prompts can utilize vocabulary related to these cinematic elements to achieve precise style control. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]
*   **Camera and Shot Types**: The I2V model supports diverse stylized scenes and reduces unrealistic camera movements. Example prompts explicitly use camera terminology such as "close-up shot" and describe the subject's gaze relative to the camera. [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Style Specification**: Prompts can specify visual styles, such as "Summer beach vacation style," to guide the aesthetic output. [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]

## Prompt Length
*   **Variable Length**: The sources provide examples of both short prompts (e.g., "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage.") and very long, detailed prompts (e.g., the I2V example describing a cat on a surfboard with background details). [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B] [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Not in sources**: Specific maximum token limits or recommended character counts for the text encoder.

## Language
*   **Supported Languages**: The I2V model metadata lists `en` (English) and `zh` (Chinese) as supported languages. [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Prompt Extension Language**: When using the Dashscope API for prompt extension, the target language can be specified (e.g., `--prompt_extend_target_lang 'zh'`). [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]

## Negative Prompts
*   **Not in sources**: The provided evidence does not mention the use of negative prompts, negative conditioning, or specific parameters for negative text encoding in the Wan 2.2 family.

## Text Encoder and Prompt Processing
*   **Text Encoder Model**: The inference commands reference `--t5_cpu` and `--t5_fsdp` options, indicating the use of a T5-based text encoder. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B] [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Prompt Extension**:
    *   **Purpose**: Extending prompts is recommended to enrich details in generated videos and enhance quality. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]
    *   **Methods**:
        *   **Dashscope API**: Uses `qwen-plus` for text-to-video and `qwen-vl-max` for image-to-video tasks. Requires `DASH_API_KEY`. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]
        *   **Local Model**: Can use Qwen models such as `Qwen/Qwen2.5-14B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, or `Qwen/Qwen2.5-3B-Instruct` depending on available GPU memory. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]
    *   **Image-to-Video Specific**: For I2V, prompt extension can generate a prompt solely from the input image if no text prompt is provided. [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Not in sources**: Specific details on how the T5 encoder processes the prompt (e.g., tokenization specifics, attention mechanisms) beyond the command-line flags.

## Task-Specific Prompting Notes
*   **Text-to-Video (T2V)**: Prompts describe the entire video content from scratch. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B]
*   **Image-to-Video (I2V)**: Prompts describe the motion, style, and context for the provided reference image. The `size` parameter represents the area of the generated video, with the aspect ratio following the original input image. [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B]
*   **Speech-to-Video (S2V) / Dancer**: These variants are conditioned by audio features extracted from music or speech, implying the text prompt may be secondary or used in conjunction with audio conditioning. [MODEL.md] [LOCAL_MODELS.tsv]
*   **Animate**: Designed for character animation and replacement, replicating movement and expressions from a source video/image. [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
