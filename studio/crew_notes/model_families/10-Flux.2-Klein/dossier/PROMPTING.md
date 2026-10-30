# PROMPTING - 10-Flux.2-Klein

## Prompt Structure and Inputs
The models accept text prompts as primary inputs for both text-to-image generation and image editing. For editing tasks, the inputs include reference images (single or multiple) alongside the text prompt [MODEL.md]. The `FLUX.2 [dev]` model also accepts control signals such as canny and depth when using ControlNets [MODEL.md].

## Prompt Length and Style
Not in sources: specific prompt length limits or character counts.
Not in sources: specific style or camera vocabulary lists.
The model card notes that "Prompt following is heavily influenced by the prompting style" [https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md].

## Text Encoder and Prompt Processing
The text encodes text prompts into embeddings for the diffusion model [LOCAL_MODELS.tsv].
For the `FLUX.2 [klein] 4B` model, the specified text encoder is `qwen_3_4b.safetensors` [SOURCES.md].
The `FLUX.2 [dev]` model benefits from prompt upsampling, which can be performed locally using a `Mistral-Small-3.2-24B-Instruct-2506` model or via external APIs [MODEL.md].
A local `Flux.3-Klein Qwen3.5 9B prompt upsampler, int8` is present on the system, described as an LLM-based prompt upsampler that expands or refines user prompts before feeding them to the main text encoder [MODEL.md].

## Guidance and Inference Settings
The `FLUX.2 [klein]` models are guidance-distilled [MODEL.md].
In the provided Diffusers example for `FLUX.2 [klein] 4B`, the `guidance_scale` is set to `1.0` [https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md].
The distilled Klein models use 4-step inference for production, while Base models use 50-step inference [MODEL.md].

## Limitations
The model may fail to generate output that matches the prompts [https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md].
Text rendered in the output may be inaccurate or subject to distortion [https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 58888 chars.
