# PROMPTING - 13-Kandinsky-OmniGen-Ovis-HunyuanImage

## Prompt Structure and Inputs

**Kandinsky 5.0 T2I Lite**
*   **Inputs**: The model accepts a text prompt, an optional negative prompt, height, and width [MODEL.md].
*   **Negative Prompts**: The pipeline explicitly supports a `negative_prompt` parameter. In the provided usage example, an empty string `""` is passed for the negative prompt [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].
*   **Example Prompt**: The documentation provides a detailed example prompt: "A fluffy, expressive cat wearing a bright red hat with a soft, slightly textured fabric. The hat should look cozy and well-fitted on the cat’s head. On the front of the hat, add clean, bold white text that reads “SWEET”, clearly visible and neatly centered. Ensure the overall lighting highlights the hat’s color and the cat’s fur details." [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].

**Kandinsky 2.x Series**
*   **Inputs**: Kandinsky 2.2 accepts a text prompt, an optional image for inpainting or fusion, and a mask for inpainting [MODEL.md].
*   **Example Prompts**:
    *   Kandinsky 2.2: "red cat, 4k photo" [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
    *   Kandinsky 2.1: "Einstein in space around the logarithm scheme" [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
    *   Kandinsky 2.0: "A teddy bear на красной площади" (Russian: A teddy bear on Red Square) [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
    *   Kandinsky 2.0 Inpainting: "Девушка в красном платье" (Russian: Girl in a red dress) [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].

**Ovis-Image**
*   **Inputs**: The model processes text and visual inputs via the Ovis-2.5 encoder [MODEL.md].
*   **Not in sources**: Specific example prompts or prompt structure guidelines for Ovis-Image are not provided in the evidence.

## Language Support

## Text Encoding and Conditioning

**Kandinsky 5.0 (T2I Lite and Video Pro)**
*   **Mechanism**: The model uses **dual text encoding** using **Qwen2.5-VL** and **CLIP** for comprehensive text understanding [MODEL.md] [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].
*   **Conditioning**: The Diffusion Transformer (DiT) backbone uses **cross-attention** to condition on these text embeddings [MODEL.md] [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].
*   **Optimization**: An NF4 version of Qwen2.5-VL from Bitsandbytes is supported to reduce memory usage [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md].

**Ovis-Image**
*   **Mechanism**: Relies on the **Ovis-2.5 VLM** to provide text and visual embeddings that condition the diffusion process [MODEL.md].
*   **Local Component**: The local text encoder file is `ovis_2.5.safetensors` (5.14 GB), located in `_complete_pipelines/Ovis-Image/text_encoders` [MODEL.md] [LOCAL_MODELS.tsv].

**Kandinsky 2.2**
*   **Mechanism**: Uses a multi-stage approach. The text encoder is **XLM-Roberta-Large-Vit-L-14** (560M parameters) [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
*   **Prior**: A diffusion image prior maps text embeddings to image embeddings [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].

**Kandinsky 2.1**
*   **Mechanism**: Uses **CLIP** (ViT-L/14) as the text and image encoder, along with a diffusion image prior mapping between latent spaces [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].

**Kandinsky 2.0**
*   **Mechanism**: Uses two multilingual text encoders: **mCLIP-XLMR** (560M parameters) and **mT5-encoder-small** (146M parameters) [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].

## Style and Camera Vocabulary

*   **Kandinsky 5.0 Video Pro**: Supports **controllable camera motion** [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md].
*   **LoRAs for Camera Control**: Specific LoRAs for camera control are open-sourced for Kandinsky 5.0 Video Lite and Pro models [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md].
*   **Kandinsky 2.2**: The switch to CLIP-ViT-G as the image encoder increases the capability to generate "more aesthetic pictures" [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
*   **Not in sources**: Specific style keywords, camera angle terminology, or prompt syntax for camera control (e.g., "zoom in", "pan left") are not detailed in the provided text.

## Prompt Length and Complexity

## Generation Settings Influencing Prompt Adherence

While not strictly "prompting" syntax, these settings directly affect how the prompt is interpreted:

*   **Kandinsky 5.0 T2I Lite**:
    *   `guidance_scale`: Example value `3.5` [MODEL.md] [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].
    *   `num_inference_steps`: Example value `50` [MODEL.md] [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md].
*   **Kandinsky 2.2**:
    *   `guidance_scale`: Example value `4` [MODEL.md].
    *   `prior_cf_scale`: Example value `4` [MODEL.md].
    *   `decoder_steps`: Example value `50` [MODEL.md].
*   **Kandinsky 2.1**:
    *   `guidance_scale`: Example value `4` or `5` [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
    *   `prior_cf_scale`: Example value `4` [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
*   **Kandinsky 2.0**:
    *   `guidance_scale`: Example value `10` [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].
    *   `denoised_type`: Example value `'dynamic_threshold'` [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md].

## Not in Sources

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
