# PROMPTING - 12-HunyuanVideo-FramePack

## Prompt Structure and Language
*   **Languages:** The model supports English and Chinese. [SOURCES.md]
*   **Structure:** The model utilizes a "Dual-stream to Single-stream" hybrid Transformer architecture where video and text tokens are processed independently in the dual-stream phase and concatenated for multimodal fusion in the single-stream phase. [MODEL.md]
*   **System Instructions:** The Multimodal Large Language Model (MLLM) text encoder can act as a zero-shot learner by following system instructions prepended to user prompts, which helps text features pay more attention to key information. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]

## Prompt Length and Style
*   **Variability:** The model is designed to address variability in linguistic style and length of user-provided prompts. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Prompt Rewrite:** A fine-tuned Hunyuan-Large model is used to adapt original user prompts to model-preferred prompts. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
    *   **Normal Mode:** Designed to enhance the video generation model's comprehension of user intent, facilitating a more accurate interpretation of instructions. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
    *   **Master Mode:** Enhances the description of aspects such as composition, lighting, and camera movement, leaning towards generating videos with higher visual quality, though this may occasionally result in the loss of some semantic details. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Prompt Handbook:** A specific prompt handbook is available for HunyuanVideo-1.5. [SOURCES.md]

## Negative Prompts
Not in sources: Specific guidance on the use or structure of negative prompts.

## Style and Camera Vocabulary
*   **Camera Movement:** The "Master mode" of the prompt rewrite model specifically enhances descriptions of camera movement. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Composition and Lighting:** The "Master mode" also enhances descriptions of composition and lighting. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Visual Quality:** The MLLM text encoder has demonstrated superior ability in image detail description and complex reasoning compared to CLIP. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]

## Text Encoder Behavior
*   **Encoder Type:** The model uses a pre-trained Multimodal Large Language Model (MLLM) with a Decoder-Only structure as the text encoder. [MODEL.md]
*   **Advantages over CLIP/T5:**
    *   Compared to T5, the MLLM has better image-text alignment in the feature space after visual instruction finetuning, alleviating the difficulty of instruction following in diffusion models. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
    *   Compared to CLIP, the MLLM has superior ability in image detail description and complex reasoning. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
    *   The MLLM is based on causal attention, whereas T5-XXL utilizes bidirectional attention. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Token Refiner:** An extra bidirectional token refiner is introduced to enhance text features because the MLLM uses causal attention. [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]
*   **Local Encoder Files:**
    *   `qwen2.5-vl-7b-bf16.safetensors` is listed as a text encoder used for encoding text prompts. [MODEL.md]
    *   `HunyuanVideo LLaVA Llama3 text encoder` is listed as an 8B parameter FP8 text encoder for video generation. [MODEL.md]
    *   `qwen_2.5_vl_7b.safetensors` and `qwen_2.5_vl_7b_fp8_scaled.safetensors` are listed as valid text encoders for HunyuanVideo 1.5 in the ComfyUI folder structure. [SOURCES.md]
    *   `byt5_small_glyphxl_fp16.safetensors` is listed in the text encoders folder for HunyuanVideo 1.5. [SOURCES.md]

## FramePack Specifics
*   **Technique:** FramePack is a method for packing input frame context in next-frame prediction models, associated with the HunyuanVideo ecosystem. [MODEL.md]
*   **Community Contribution:** FramePack is listed as a community contribution for "Packing Input Frame Context in Next-Frame Prediction Models for Video Generation" by Lvmin Zhang. [PUBLIC README https://raw.githubusercontent.com/Tencent-Hunyuan/HunyuanVideo/HEAD/README.md]
*   **Prompting Specifics:** Not in sources: Specific prompting guidelines unique to the FramePack technique beyond general HunyuanVideo prompting.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
