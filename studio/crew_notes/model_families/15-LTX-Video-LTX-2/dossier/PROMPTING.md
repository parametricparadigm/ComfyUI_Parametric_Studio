# PROMPTING - 15-LTX-Video-LTX-2

## Prompt Structure and Language
*   **Language**: The model is trained on English. [MODEL.md]
*   **Structure**: The sources do not provide a specific syntactic structure (e.g., subject-verb-object) or a required order of elements (e.g., style before subject). [MODEL.md]
*   **Style Influence**: Prompt following is heavily influenced by the prompting-style. [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]
*   **External Guide**: For tips on writing effective prompts, the official documentation directs users to the "Prompting guide" at `https://ltx.video/blog/how-to-prompt-for-ltx-2`. [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

## Prompt Length
*   Not in sources: Specific character or token limits for prompts.

## Negative Prompts
*   **Usage**: Negative prompts are supported in the Diffusers pipeline for LTX-2. [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]
*   **Example Content**: The provided example uses the following negative prompt: "shaky, glitchy, low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, fused fingers, bad anatomy, weird hand, ugly, transition, static." [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]
*   **Distilled Models**: For LTX-Video v0.9.6 distilled models, the sources state that "no STG/CFG required," implying negative prompts (which typically rely on CFG) may not be used or are handled differently in that specific distilled variant. [PUBLIC README https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md]

## Style and Camera Vocabulary
*   **Camera Logic**: LTX-2 supports "3D camera logic" as a feature for creative control. [PUBLIC README https://raw.githubusercontent.com/Lightricks/LTX-Video/HEAD/README.md]
*   **Style Customization**: Standard LoRA support is available for style customization. [MODEL.md]
*   **Specific Vocabulary**: Not in sources: A specific list of recommended camera angles, lens types, or style keywords.

## Text Encoder Behavior
*   **Model**: The LTX-2.5 pipeline uses a `Gemma4 12B` text encoder. [MODEL.md]
*   **Function**: The text encoder encodes text prompts for video generation. [MODEL.md]
*   **Integration**: In ComfyUI workflows, the text encoder is loaded via `LTXVGemmaCLIPModelLoader` and the prompt is encoded via `CLIPTextEncode` to produce `CONDITIONING`. [WORKFLOW_PLAN.md]
*   **Projection**: The downloaded text encoder file is named `gemma4-12b-with-proj-ltx-2.5-bf16.safetensors`, indicating a projection layer is included for the LTX-2.5 model. [SOURCES.md]

## Limitations and Notes
*   **Audio Quality**: When generating audio without speech, the audio may be of lower quality. [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]
*   **Prompt Adherence**: The model may fail to generate videos that match the prompts perfectly. [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
