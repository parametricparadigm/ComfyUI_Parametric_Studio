# PROMPTING - Upscale / restore models

## Prompt Applicability
Prompts are only relevant for diffusion-based upscalers within this family. The sources state that specific models may require additional inputs such as prompts for diffusion-based upscalers like SeedVR2 [MODEL.md]. For non-diffusion models (such as Real-ESRGAN, ESRGAN, RGT, HAT, Thera, NAFNet, CRM, IRN, and the SD 2x Latent Upscaler), the sources do not indicate that text prompts are an input; these models operate on image, video, or latent tensor inputs [MODEL.md].

## Text Encoder and Model Architecture
The sources do not specify which text encoders are used by the SeedVR2 models or how the text encoder processes the prompt for this specific family. The sources mention text encoders (OpenCLIP-ViT/G and CLIP-ViT/L) only in the context of the SDXL base model, which is listed as a source but is not part of the local Upscale/restore model files [SOURCES.md].
Not in sources: The specific text encoder architecture used by SeedVR2.
Not in sources: How the text encoder processes the prompt for SeedVR2.

## Prompt Structure and Content
Not in sources: Recommended prompt structure for SeedVR2.
Not in sources: Recommended prompt length for SeedVR2.
Not in sources: Recommended language for SeedVR2 prompts.
Not in sources: Style or camera vocabulary specific to SeedVR2 prompting.

## Negative Prompts
Not in sources: Whether negative prompts are supported or recommended for SeedVR2.
Note: The sources state that SDXL-Turbo does not make use of `negative_prompt`, but SDXL-Turbo is not listed as a local model in the Upscale/restore family [SOURCES.md].

## Guidance Scale
For diffusion-based upscalers, guidance scale may be a parameter [MODEL.md].
Not in sources: The specific default or recommended guidance scale value for SeedVR2.

## Other Inputs
Specific models may require additional inputs such as reference images [MODEL.md].
Not in sources: How reference images interact with text prompts in SeedVR2.

## Non-Diffusion Models
For the majority of the family (Super-resolution GANs, Latent Upscalers, Image Restoration, Color Rescaling), the inputs are low-resolution images, video frames, or latent tensors [MODEL.md].
Not in sources: Any text prompt input for Real-ESRGAN, ESRGAN, RGT, HAT, Thera, NAFNet, CRM, IRN, or SD 2x Latent Upscaler.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
