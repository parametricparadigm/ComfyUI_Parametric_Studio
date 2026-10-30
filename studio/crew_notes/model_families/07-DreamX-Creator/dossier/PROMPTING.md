# PROMPTING - 07-DreamX-Creator

## Prompt Structure and Inputs
The primary input for generation is a text prompt combined with a first frame image. The system generates synchronized video and audio from these inputs [MODEL.md]. In the ComfyUI implementation, the positive prompt is encoded using `CLIPTextEncode` with the CLIP output from `DreamXBundleLoader` [WORKFLOW_PLAN.md]. The negative prompt is also encoded using `CLIPTextEncode` with the CLIP output from `DreamXBundleLoader` [WORKFLOW_PLAN.md].

## Negative Prompts
A negative prompt is an optional input for the model [MODEL.md]. In the native CPU runtime (`rust-model-inference`), the negative prompt is passed via the `--negative-prompt` flag [SOURCES.md]. The provided example uses the value "low quality" for the negative prompt [SOURCES.md]. In the ComfyUI workflow, the negative prompt is encoded separately and connected to the guider or sampler as part of the conditioning [WORKFLOW_PLAN.md].

## Text Encoder
The text encoder used by the model family is UMT5-XXL [SOURCES.md]. In the ComfyUI bundle, the text encoder weights are located in `wan2.2_ti2v_5b/models_t5_umt5-xxl-enc-bf16.pth` and the tokenizer files are in `wan2.2_ti2v_5b/google/umt5-xxl/` [SOURCES.md]. In the GGUF conversion, the UMT5 text encoder is contained within the `mmproj-DreamX-Creator-BF16.gguf` file [SOURCES.md]. The text encoder is used to encode the positive and negative prompts into conditioning for the generator [WORKFLOW_PLAN.md].

## Prompt Content and Speech
The prompt can request exact wording for native speech, but the transcript cannot be guaranteed because native speech is stochastic [T8mars/Comfyui-DreamX-Creator-T8]. The prompt should describe the visual content and any desired audio elements, such as a person speaking [SOURCES.md].

## Not in sources
*   Specific prompt length limits or maximum token counts for the text encoder.
*   Recommended language for prompts (e.g., English vs. other languages).
*   Specific style or camera vocabulary guidelines (e.g., "cinematic," "wide shot," "close-up").
*   Detailed internal processing of the prompt by the text encoder beyond it being encoded into conditioning.
*   Best practices for structuring the prompt (e.g., subject first, then action, then style).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
