# PROMPTING - 24-SDXL

## Prompt Structure and Language
The model accepts text prompts as input for both text-to-image and image-to-image tasks [MODEL.md]. The sources provide examples of prompts in English, such as "An astronaut riding a green horse" and "A cinematic shot of a baby racoon wearing an intricate italian priest robe." [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md].

Not in sources: Specific guidance on prompt length, token limits, or non-English language support.

## Text Encoders
The SDXL 1.0 Base model uses two fixed, pretrained text encoders: `OpenCLIP-ViT/G` and `CLIP-ViT/L` [MODEL.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]. The refiner model also utilizes these two fixed, pretrained text encoders [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md]. In the Diffusers pipeline for the base+refiner ensemble, the refiner is loaded with `text_encoder_2` from the base model [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md].

## Negative Prompts
*   **SDXL 1.0 Base/Refiner:** The workflow plans indicate the use of a negative text prompt encoded via `CLIPTextEncode` for the base model [WORKFLOW_PLAN.md].
*   **SDXL-Turbo:** SDXL-Turbo does not make use of `negative_prompt`. It is disabled by setting `guidance_scale=0.0` [MODEL.md, PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md].

## Style and Camera Vocabulary
The sources do not provide a specific vocabulary list for style or camera terms. However, example prompts include descriptive terms such as "cinematic shot," "detailed," "fantasy," "cute," "adorable," "Pixar," "Disney," and "8k" [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md].

## Prompting Limitations
The model cannot render legible text [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]. The model struggles with difficult tasks involving compositionality, such as rendering an image corresponding to "A red cube on top of a blue sphere" [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md]. Faces and people in general may not be generated properly [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md].

## Pipeline-Specific Prompting Notes
*   **Base + Refiner Ensemble:** When using the ensemble of experts pipeline, the same prompt is passed to both the base model and the refiner model [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md].
*   **SDEdit (img2img):** When using the two-stage pipeline with SDEdit, the same prompt used in the first step is used for the second step [MODEL.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md, PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md].
*   **SDXL-Turbo:** For image-to-image generation with SDXL-Turbo, the prompt is provided alongside the initial image, with `guidance_scale` set to 0.0 [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
