# PITFALLS - 24-SDXL

## SDXL-Turbo Configuration Errors

### Symptom: Poor image quality or failure to generate high-fidelity images in low-step regime
**Cause:** Using non-zero `guidance_scale` or providing a `negative_prompt`. SDXL-Turbo is distilled using Adversarial Diffusion Distillation (ADD) and does not utilize these parameters.
**Fix:** Set `guidance_scale=0.0` and do not use `negative_prompt`.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

### Symptom: Image-to-image generation fails or produces incorrect step counts
**Cause:** The product of `num_inference_steps` and `strength` is less than 1. The pipeline runs for `int(num_inference_steps * strength)` steps, which would result in 0 steps if the product is < 1.
**Fix:** Ensure `num_inference_steps * strength` is greater than or equal to 1.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

### Symptom: Suboptimal image quality compared to potential
**Cause:** Using only 1 step when higher quality is desired. While 1 step is sufficient for high quality, performance improves with more steps.
**Fix:** Use 4 steps for further improved performance.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

## VRAM and Performance Limits

### Symptom: Out of memory errors or slow inference on limited GPU hardware
**Cause:** Loading the full model to GPU without memory optimization.
**Fix:** Enable CPU offloading by calling `pipe.enable_model_cpu_offload()` instead of `.to("cuda")`.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Slower inference than possible on modern PyTorch versions
**Cause:** Not utilizing compiler optimizations available in newer PyTorch versions.
**Fix:** If using `torch >= 2.0`, wrap the UNet with `torch.compile` (e.g., `pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)`) to improve inference speed by 20-30%.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

## Dependency and Version Incompatibilities

### Symptom: Pipeline loading errors or missing features when using Diffusers
**Cause:** Using an outdated version of the `diffusers` library.
**Fix:** Upgrade `diffusers` to >= 0.19.0 for the base model or >= 0.18.0 for the refiner.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md] [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md]

### Symptom: Missing dependencies when running the pipeline
**Cause:** Not installing required auxiliary libraries.
**Fix:** Install `transformers`, `safetensors`, `accelerate`, and `invisible_watermark`.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

## Model Architecture and Usage Pitfalls

### Symptom: Lower quality output than expected from the SDXL family
**Cause:** Using the base model as a standalone module when the ensemble of experts pipeline is available. The base model generates noisy latents that are intended to be refined.
**Fix:** Use the base model in conjunction with the refiner model for the best overall performance.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Incorrect refiner behavior or errors when loading the refiner pipeline
**Cause:** Not sharing the correct text encoder and VAE from the base model to the refiner.
**Fix:** When loading the refiner, pass `text_encoder_2=base.text_encoder_2` and `vae=base.vae` from the base pipeline instance.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Slower generation times than the standard ensemble pipeline
**Cause:** Using the alternative two-stage pipeline with SDEdit (img2img) instead of the base+refiner ensemble.
**Fix:** Use the base+refiner ensemble for faster generation, as the SDEdit technique requires more function evaluations.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

## Known Model Limitations

### Symptom: Generated images contain illegible text
**Cause:** The model architecture does not support rendering legible text.
**Fix:** Not fixable within the model; use external tools for text overlay.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Poor generation of faces or people
**Cause:** The model struggles with generating faces and people properly.
**Fix:** Not fixable within the base model; consider using specific adapters like PuLID or IP-Adapters if available in the workflow.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Loss of detail or artifacts in generated images
**Cause:** The autoencoding part of the model is lossy.
**Fix:** Not fixable within the model; inherent to the latent diffusion architecture.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: Failure to render complex compositional prompts (e.g., "A red cube on top of a blue sphere")
**Cause:** The model struggles with difficult tasks involving compositionality.
**Fix:** Simplify prompts or use ControlNets for spatial control if available.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Symptom: SDXL-Turbo outputs are limited in resolution
**Cause:** The model is optimized for 512x512 pixels.
**Fix:** While higher sizes work, 512x512 is the preferred/optimized size.
**Source:** [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

## Not in sources:
- Specific VRAM requirements in GB for inference.
- Specific quantization formats (e.g., FP8, INT8) compatibility or limitations.
- Specific scheduler recommendations (e.g., Euler, DPM++).
- Specific `denoising_end`/`denoising_start` values other than the 80/20 example.
- Specific ControlNet strength or end_percent values.
- Specific LoRA or IP-Adapter compatibility issues.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
