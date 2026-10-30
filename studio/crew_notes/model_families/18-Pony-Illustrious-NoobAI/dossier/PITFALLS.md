# PITFALLS - 18-Pony-Illustrious-NoobAI

## Pony Diffusion V6 XL

### Low-quality blobs
- **Symptom**: Generation results in "low quality blobs".
- **Cause**: The model is not loaded with the correct CLIP skip setting.
- **Fix**: Load the model with `clip skip 2` (or `-2` in some software).
- **Source**: [PUBLIC README https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md]

### Weak quality control
- **Symptom**: Quality modifiers have a "much weaker effect" than expected.
- **Cause**: Using only the simple `score_9` tag instead of the full V6 XL prompt template. This is noted as a "training issue that was too late to correct during training".
- **Fix**: Use the full string: `score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up`.
- **Source**: [PUBLIC README https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md]

### Pseudo signatures
- **Symptom**: The model generates "pseudo signatures" that are hard to remove, even with negative prompts.
- **Cause**: A training issue in the model.
- **Fix**: Try V5.5 or use inpainting.
- **Source**: [PUBLIC README https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md]

### Incorrect resolution or steps
- **Symptom**: Not explicitly stated as a failure, but suboptimal results may occur if deviating from recommendations.
- **Cause**: Using resolutions or step counts outside the recommended range.
- **Fix**: Use `Euler a` sampler with `25` steps and `1024px` resolution.
- **Source**: [PUBLIC README https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md]

## SDXL-Turbo

### Invalid image-to-image generation
- **Symptom**: The image-to-image pipeline may not run correctly or produce expected results.
- **Cause**: The product of `num_inference_steps` and `strength` is less than 1.
- **Fix**: Ensure that `num_inference_steps` * `strength` is larger or equal to 1.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

### Ineffective guidance or negative prompts
- **Symptom**: Guidance scale or negative prompts do not affect the output.
- **Cause**: SDXL-Turbo does not make use of `guidance_scale` or `negative_prompt`.
- **Fix**: Disable guidance by setting `guidance_scale=0.0` and do not rely on negative prompts.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

### Suboptimal resolution
- **Symptom**: Not explicitly stated as a failure, but the model is designed for a specific size.
- **Cause**: Generating images at sizes other than the preferred resolution.
- **Fix**: Preferably generate images of size `512x512`, though higher sizes work.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

## SDXL Base / Refiner

### VRAM Limitations
- **Symptom**: Out of memory errors or slow performance due to high VRAM usage.
- **Cause**: Loading the full model onto the GPU without offloading.
- **Fix**: Enable CPU offloading by calling `pipe.enable_model_cpu_offload` instead of `.to("cuda")`.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

### Dependency Version Conflicts
- **Symptom**: Pipeline fails to load or run.
- **Cause**: Using outdated versions of `diffusers`.
- **Fix**: Upgrade `diffusers` to `>= 0.19.0` (for base) or `>= 0.18.0` (for refiner) and install `transformers`, `safetensors`, `accelerate`, and `invisible_watermark`.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md], [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/raw/main/README.md]

### Incomplete Pipeline
- **Symptom**: Lower quality output compared to the full ensemble.
- **Cause**: Using the base model standalone without the refinement model.
- **Fix**: Use the base model combined with the refinement model for the best overall performance, or use the two-stage SDEdit pipeline.
- **Source**: [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md]

## General / Hardware

### Missing Local Checkpoint
- **Symptom**: Workflow plans for Pony V6 may fail or produce non-Pony-specific outputs.
- **Cause**: The specific Pony Diffusion V6 XL checkpoint file is not present in the provided local file list (`_complete_pipelines/SDXL/checkpoints/`).
- **Fix**: Ensure the correct Pony V6 checkpoint is available or use a compatible SDXL checkpoint as a placeholder (acknowledging this may result in non-Pony-specific outputs).
- **Source**: [WORKFLOW_PLAN.md]

### Missing Vision Model for IP-Adapter
- **Symptom**: IP-Adapter workflows cannot be completed.
- **Cause**: The specific vision model file (e.g., `clip_vision_h.safetensors`) is not listed in the local files.
- **Fix**: Not in sources: Specific fix for missing vision model file.
- **Source**: [WORKFLOW_PLAN.md]

### Unrelated Software Confusion
- **Symptom**: Confusion regarding model capabilities or sources.
- **Cause**: Repositories like `DietrichGebert/ponytail` and `ponylang/ponyc` share the name "pony" but are unrelated software (AI agent prompt engineering library and programming language, respectively).
- **Fix**: Verify that the source is a generative AI model and not unrelated software sharing the name.
- **Source**: [MODEL.md]

### Not in sources: Specific VRAM requirements in GB for each model variant.
### Not in sources: Specific quantization format incompatibilities (e.g., FP8 vs FP16 issues).
### Not in sources: Specific scheduler incompatibilities beyond the recommended `Euler a` for Pony.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
