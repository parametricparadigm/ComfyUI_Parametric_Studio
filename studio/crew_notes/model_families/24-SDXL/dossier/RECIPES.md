# RECIPES - 24-SDXL

| Recipe / Variant | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength / Other Values | Outcome | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SDXL-Turbo Text-to-Image | `num_inference_steps=1` | `guidance_scale=0.0` | Not in sources: sampler/scheduler | 512x512 (preferred); higher sizes work | Not in sources: shift | Photorealistic images in a single network evaluation; high image quality | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo Image-to-Image | `num_inference_steps=2` | `guidance_scale=0.0` | Not in sources: sampler/scheduler | 512x512 (input resized) | `strength=0.5` | Image-to-image generation; pipeline runs for `int(num_inference_steps * strength)` steps (e.g., 1 step) | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL Base + Refiner (Ensemble) | `num_inference_steps=40` (for both base and refiner calls) | Not in sources: CFG/guidance | Not in sources: sampler/scheduler | Not in sources: specific resolution | `denoising_end=0.8` (base), `denoising_start=0.8` (refiner) | Best overall performance; base generates noisy latents, refiner processes final denoising steps | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL Base Standalone | Not in sources: specific step count | Not in sources: CFG/guidance | Not in sources: sampler/scheduler | Not in sources: specific resolution | Not in sources: shift/strength | Generates images from text prompts; can be used as a standalone module | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL Refiner (Img2Img) | Not in sources: specific step count | Not in sources: CFG/guidance | Not in sources: sampler/scheduler | Not in sources: specific resolution | Not in sources: shift/strength | Improves images; operates on existing latents/images | [https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0] |

Not in sources: specific sampler or scheduler recommendations for any SDXL variant.
Not in sources: specific CFG/guidance scale values for SDXL Base or Refiner.
Not in sources: specific resolution settings for SDXL Base or Refiner (only SDXL-Turbo specifies 512x512).
Not in sources: frames or fps values (SDXL is a text-to-image model, not video).
Not in sources: specific `strength` values for SDXL Base or Refiner (only SDXL-Turbo img2img specifies `strength=0.5`).
> UNVERIFIED: name not in evidence: num_inference_steps=40

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
