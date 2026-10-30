# PROMPTING - 05-CogVideoX-Mochi-Cosmos-SVD-AnimateDiff-older-video

## Prompt Structure and Language
*   **Language**: The sources indicate that the models are trained on English data. The Hugging Face metadata for `zai-org/CogVideoX-5b` and `genmo/mochi-1-preview` lists `en` as the language [SOURCES.md]. The SVD model card notes that human evaluation was performed by "fluent English-speaking contractors" [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md].
*   **Structure**: The sources do not provide a specific syntactic structure (e.g., "subject, action, environment") for prompts. However, the demo captions for `CogVideoX-5b` demonstrate long, descriptive sentences that include subject, action, environment, and atmospheric details (e.g., "A garden comes to life as a kaleidoscope of butterflies flutters amidst the blossoms...") [PUBLIC README https://huggingface.co/zai-org/CogVideoX-5b/raw/main/README.md].
*   **Mochi Prompt Adherence**: The `genmo/mochi-1-preview` README states the model has "strong prompt adherence in preliminary evaluation" [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md].

## Prompt Length
*   **Not in sources**: Specific maximum token limits or recommended character counts for prompts are not explicitly stated in the provided evidence.
*   **Mochi Text Tokens**: The `genmo/mochi-1-preview` architecture table lists `256` for "Text Tokens" in the AsymmDiT model specs, which may imply a processing limit or context window for the text stream [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md].

## Negative Prompts
*   **Mochi**: Supports negative prompts. The API example in the `genmo/mochi-1-preview` README includes a `negative_prompt` parameter, shown as an empty string `""` in the example [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]. The `MODEL.md` file confirms "Negative Prompts: Supported by Mochi" [MODEL.md].
*   **CogVideoX**: The `WORKFLOW_PLAN.md` for CogVideoX-5B includes a step to "Use `CLIPTextEncode` to encode the negative prompt," implying support for negative conditioning in the ComfyUI workflow [WORKFLOW_PLAN.md].
*   **SVD**: The `SVD` model card states, "The model cannot be controlled through text" [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md]. Therefore, text prompts (positive or negative) are not applicable for SVD.
*   **AnimateDiff/Cosmos**: Not in sources: Specific negative prompt support or usage for AnimateDiff or Cosmos is not detailed in the provided evidence.

## Style and Camera Vocabulary
*   **CogVideoX**: The demo captions for `CogVideoX-5b` utilize descriptive vocabulary for camera angles and scene composition, such as "close-up," "background artfully blurred," "from a distance," and "dashes towards the viewer" [PUBLIC README https://huggingface.co/zai-org/CogVideoX-5b/raw/main/README.md].
*   **Mochi**: The `genmo/mochi-1-preview` README provides a prompt example using "Close-up" and "Ultra high resolution 4k" [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md].
*   **SVD**: The `SVD` model card notes that the model "may generate videos without motion, or very slow camera pans" [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md]. It does not accept text prompts to control camera movement.
*   **General**: Not in sources: A specific glossary of supported style or camera keywords for the entire family is not provided.

## Text Encoder Behavior
*   **Mochi**: Uses a single `T5-XXL` language model for prompt encoding [MODEL.md]. The `AsymmDiT` architecture "jointly attends to text and visual tokens with multi-modal self-attention" and uses "separate MLP layers for each modality" [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]. The text stream has a hidden dimension of `1536` and processes `256` text tokens [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md].
*   **CogVideoX**: Uses a text encoder located at `_complete_pipelines/CogVideoX/text_encoders/t5xxl_fp16.safetensors` [MODEL.md]. The architecture involves a diffusion model that "processes prompts and generates video latents" [MODEL.md].
*   **SVD**: Does not use a text encoder for generation control as it is an image-to-video model that "cannot be controlled through text" [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md].
*   **AnimateDiff/Cosmos**: Not in sources: Specific details on the text encoder architecture or behavior for AnimateDiff or Cosmos are not provided in the evidence.

## Model-Specific Prompting Notes
*   **SVD**: Prompts are not used. The model takes a "still image as a conditioning frame" [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md].
*   **Mochi**: The model is "optimized for photorealistic styles so does not perform well with animated content" [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md].
*   **CogVideoX**: Supports text-to-video, video continuation, and image-to-video generation [MODEL.md]. For image-to-video, it can "take an image as a background input and generate a video combined with prompt words" [PUBLIC README https://raw.githubusercontent.com/zai-org/CogVideo/HEAD/README.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
