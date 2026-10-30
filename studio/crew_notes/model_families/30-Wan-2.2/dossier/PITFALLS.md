# PITFALLS - 30-Wan-2.2

## VRAM and Memory Limits

### Out-of-Memory (OOM) on Single GPU
- **Symptom**: Inference fails or crashes due to insufficient GPU memory when running A14B models.
- **Cause**: The A14B models require significant VRAM; single-GPU inference is recommended for GPUs with at least 80GB VRAM.
- **Fix**: Use the `--offload_model True`, `--convert_model_dtype`, and `--t5_cpu` options to reduce GPU memory usage. Alternatively, use multi-GPU inference with FSDP and DeepSpeed Ulysses.
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

### High VRAM Requirement for A14B Models
- **Symptom**: Models do not fit in standard consumer GPU memory without offloading.
- **Cause**: The A14B models are large-scale (14 Billion parameters, MoE).
- **Fix**: Ensure GPU has at least 80GB VRAM or utilize offloading techniques (`--offload_model`, `--convert_model_dtype`, `--t5_cpu`).
- **Source**: [MODEL.md]

## Installation and Dependency Issues

### `flash_attn` Installation Failure
- **Symptom**: The installation of dependencies fails specifically at the `flash_attn` package.
- **Cause**: `flash_attn` can be difficult to install in certain environments.
- **Fix**: Try installing the other packages first and install `flash_attn` last.
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B/raw/main/README.md]

### Missing Python Dependencies
- **Symptom**: ComfyUI backend fails to run Wan 2.2 models.
- **Cause**: Necessary Python dependencies are not present in the virtual environment.
- **Fix**: Ensure Python dependencies are present in the virtual environment.
- **Source**: [MODEL.md]

## Node and Workflow Incompatibilities

### MoE Sampler Input Mismatch
- **Symptom**: The `WASWan22MoESamplerCtx` node signature in the provided list does not include a second MODEL input, preventing the connection of both High and Low noise expert models required for the MoE architecture.
- **Cause**: The node definition lists only one `MODEL` input, while the MoE architecture typically requires dual models (High-noise and Low-noise experts).
- **Fix**: The workflow plan notes this as a potential mismatch. It suggests relying on the standard `KSampler` or `KSamplerAdvanced` if the MoE is handled by the model weights, or assuming `WASWan22MoESamplerCtx` handles MoE logic internally. However, the LOW noise model is not connected in the drafted plan due to this signature limitation.
- **Source**: [WORKFLOW_PLAN.md]

### Missing Scheduler Input for MoE Sampler
- **Symptom**: The `WASWan22MoESamplerCtx` node does not list `SIGMAS` as an input, making it incompatible with standard scheduler outputs like `BasicScheduler`.
- **Cause**: The node's input signature lists `COMBO,CONDITIONING,FLOAT,INT,LATENT,MODEL,VAE` but not `SIGMAS`.
- **Fix**: Set the `INT` input of the sampler to the number of steps manually, or use `KSamplerAdvanced` which accepts `SIGMAS`, though it is not MoE-specific.
- **Source**: [WORKFLOW_PLAN.md]

### Missing Text Encoder File
- **Symptom**: The workflow cannot be completed because the specific text encoder model file is not listed in the local model files.
- **Cause**: The local installation inventory does not include a text encoder file for the Wan 2.2 family.
- **Fix**: Not in sources: Specific fix for missing text encoder file.
- **Source**: [WORKFLOW_PLAN.md]

### Missing CLIP Vision Model for Animate
- **Symptom**: The `Wan22AnimateToVideoTiled` node requires a `CLIP_VISION_OUTPUT` input, but the CLIP Vision model file is not listed in the local model files.
- **Cause**: The local installation inventory does not include a CLIP Vision model.
- **Fix**: Not in sources: Specific fix for missing CLIP Vision model.
- **Source**: [WORKFLOW_PLAN.md]

### Missing Mask Input for Animate
- **Symptom**: The `Wan22AnimateToVideoTiled` node requires a `MASK` input, which is not provided in the drafted workflow plan.
- **Cause**: The workflow plan does not specify a source for the mask input.
- **Fix**: Not in sources: Specific fix for missing mask input.
- **Source**: [WORKFLOW_PLAN.md]

## Model and Format Specifics

### TI2V-5B Resolution and Frame Rate Limitation
- **Symptom**: The TI2V-5B model may not support resolutions or frame rates other than its specified capabilities.
- **Cause**: The TI2V-5B model is built with a high-compression VAE (16×16×4) and is specifically designed for 720P resolution at 24fps.
- **Fix**: Use 720P resolution and 24fps for TI2V-5B generation.
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

### I2V Size Parameter Interpretation
- **Symptom**: Incorrect video aspect ratio or resolution when using the I2V-A14B model.
- **Cause**: For the Image-to-Video task, the `size` parameter represents the area of the generated video, with the aspect ratio following that of the original input image.
- **Fix**: Ensure the `size` parameter is set to the desired area, understanding that the aspect ratio will match the input image.
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B/raw/main/README.md]

### Prompt Extension Dependency
- **Symptom**: Reduced video quality or lack of detail in generated videos.
- **Cause**: Skipping the prompt extension step.
- **Fix**: Enable prompt extension using the Dashscope API or a local model (e.g., `Qwen/Qwen2.5-14B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `Qwen/Qwen2.5-3B-Instruct`).
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

### S2V Additional Requirements
- **Symptom**: Speech-to-Video generation fails or lacks speech synthesis capabilities.
- **Cause**: Missing additional requirements for CosyVoice text-to-speech synthesis.
- **Fix**: Install `requirements_s2v.txt` additionally if using CosyVoice to synthesize speech for Speech-to-Video Generation.
- **Source**: [https://huggingface.co/Wan-AI/Wan2.2-Animate-14B/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
