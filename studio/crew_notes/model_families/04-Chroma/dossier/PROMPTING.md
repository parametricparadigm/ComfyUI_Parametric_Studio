# PROMPTING - 04-Chroma

## Prompt Structure and Inputs
The Chroma family utilizes a standard text-to-image diffusion pipeline that accepts a positive text prompt and a negative text prompt. The positive prompt is a text description of the desired image, while the negative prompt describes elements to avoid [MODEL.md]. In the `diffusers` library implementation, both `prompt` and `negative_prompt` are passed as lists of strings to the `ChromaPipeline` call [lodestones/Chroma1-HD README].

In ComfyUI workflows, the prompt structure involves using `CLIPTextEncode` nodes to process both the positive and negative prompts separately. The output conditioning from the positive `CLIPTextEncode` node connects to the positive conditioning input of the `BasicGuider`, while the negative `CLIPTextEncode` output connects to the negative conditioning input [WORKFLOW_PLAN.md].

## Prompt Length and Language
Not in sources: Specific guidelines on optimal prompt length or character limits.
Not in sources: Specific language requirements (e.g., English-only) beyond the examples provided.

The provided examples use English natural language descriptions. The example prompt is a detailed, multi-sentence description: "A high-fashion close-up portrait of a blonde woman in clear sunglasses. The image uses a bold teal and red color split for dramatic lighting. The background is a simple teal-green. The photo is sharp and well-composed, and is designed for viewing with anaglyph 3D glasses for optimal effect. It looks professionally done." [lodestones/Chroma1-HD README].

## Negative Prompts
Negative prompts are supported and recommended in the provided examples. The standard negative prompt used in the `diffusers` and ComfyUI examples is: "low quality, ugly, unfinished, out of focus, deformed, disfigure, blurry, smudged, restricted palette, flat colors" [MODEL.md, lodestones/Chroma1-HD README, WORKFLOW_PLAN.md].

## Style and Camera Vocabulary
The model is trained on a 5M sample dataset covering artistic, photographic, and niche styles [MODEL.md]. The example prompt includes specific stylistic and compositional vocabulary such as "high-fashion close-up portrait," "bold teal and red color split," "dramatic lighting," "simple teal-green" background, "sharp and well-composed," and "anaglyph 3D glasses" [lodestones/Chroma1-HD README].

## Text Encoder Behavior
The model uses a T5 XXL text encoder to process prompts [MODEL.md]. The specific file required for this encoder in ComfyUI is `t5xxl_fp16.safetensors` [MODEL.md, lodestones/Chroma1-HD README].

Architectural modifications to the model include "MMDiT Masking," which involves masking T5 padding tokens. This modification is stated to have enhanced fidelity and increased training stability by preventing the model from focusing on irrelevant `<pad>` tokens [lodestones/Chroma1-HD README].

## Guidance and Sampling Parameters
While not strictly part of the text prompt, the following parameters are used in conjunction with the prompt in the standard pipeline:
*   `guidance_scale`: The example uses a value of `3.0` [MODEL.md, lodestones/Chroma1-HD README].
*   `num_inference_steps`: The example uses a value of `40` [MODEL.md, lodestones/Chroma1-HD README].
*   `seed`: An integer for reproducibility, with `433` used in the examples [MODEL.md, lodestones/Chroma1-HD README].

## Variant Specifics
*   **Chroma1-Flash**: Described as a "fast CFG 'baked' version" of the model. No specific prompting differences or additional parameters are detailed in the sources [MODEL.md, lodestones/Chroma1-HD README].
*   **Quantized Versions (GGUF)**: Quantization levels (e.g., `Q8_0`, `Q4_K_M`) affect memory usage and quality but do not change the prompt structure or text encoder requirements [MODEL.md, silveroxides/Chroma-GGUF README].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 49716 chars.
