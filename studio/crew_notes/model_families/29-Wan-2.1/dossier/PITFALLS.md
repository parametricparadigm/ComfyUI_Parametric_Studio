# PITFALLS - 29-Wan-2.1

## VRAM and Memory Limits

### Out-of-Memory (OOM) errors during inference
- **Symptom**: The inference process crashes or fails due to insufficient GPU memory, particularly when running larger models or higher resolutions. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Cause**: The model and associated tensors exceed the available VRAM on the GPU. The 14B models require substantial VRAM, and the 1.3B model, while smaller, can still hit limits without optimization. [MODEL.md]
- **Fix**: Use the `--offload_model True` and `--t5_cpu` options to offload models to CPU and run the T5 encoder on CPU, respectively, to reduce GPU memory usage. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

### Insufficient VRAM for 14B models on consumer hardware
- **Symptom**: The 14B models cannot be loaded or run on standard consumer-grade GPUs without additional measures. [MODEL.md]
- **Cause**: The 14B models are significantly larger than the 1.3B model (which requires only 8.19 GB VRAM) and often necessitate offloading or quantization to fit within standard high-end consumer or professional GPU limits. [MODEL.md]
- **Fix**: Use quantized formats such as `fp8_e4m3fn` or `fp8_scaled` for the diffusion models, and consider offloading strategies. [MODEL.md]

## Resolution and Stability Issues

### Unstable results at 720P with the 1.3B model
- **Symptom**: Generated videos at 720P resolution using the `T2V-1.3B` model are generally less stable compared to 480P. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]
- **Cause**: Limited training of the 1.3B model at 720P resolution. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]
- **Fix**: Use 480P resolution for optimal performance with the `T2V-1.3B` model. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]

### Incorrect resolution support for specific model variants
- **Symptom**: Attempting to run a model variant at a resolution it does not support (e.g., `T2V-1.3B` at 720P or `I2V-14B-720P` at 480P). [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Cause**: The model variants are trained and optimized for specific resolutions. `T2V-1.3B` supports only 480P, while `I2V-14B-720P` supports only 720P. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Fix**: Ensure the resolution parameter matches the supported resolution of the specific model variant being used. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

## Parameter and Configuration Warnings

### Suboptimal generation quality with default or incorrect sampling parameters
- **Symptom**: Generated videos may lack detail or have poor motion dynamics if sampling parameters are not tuned. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]
- **Cause**: The `--sample_guide_scale` and `--sample_shift` parameters significantly impact output quality. For the `T2V-1.3B` model, default or unadjusted values may not yield the best results. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]
- **Fix**: For the `T2V-1.3B` model, set `--sample_guide_scale 6`. Adjust `--sample_shift` within the range of 8 to 12 based on performance. [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/raw/main/README.md]

### Missing or incorrect prompt extension
- **Symptom**: Generated videos may lack detail or fail to fully capture the intent of the prompt. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Cause**: Skipping the prompt extension step can result in less detailed or less accurate video generation. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Fix**: Enable prompt extension using the `--use_prompt_extend` flag. Use the `qwen-plus` model for text-to-video tasks and `qwen-vl-max` for image-to-video tasks. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

## Incompatibilities and Missing Features

### Lack of Diffusers and ComfyUI integration in the official repository
- **Symptom**: Users expecting to use the official `Wan2.1` repository with `diffusers` or `ComfyUI` directly may find these integrations missing. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Cause**: The official repository's todo list indicates that `Diffusers integration` and `ComfyUI integration` are not yet completed. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]
- **Fix**: Use the repackaged model files from `Comfy-Org/Wan-2.1` for ComfyUI integration. [https://huggingface.co/Comfy-Org/Wan-2.1/raw/main/README.md]

### Missing audio input nodes for InfiniteTalk in ComfyUI
- **Symptom**: The InfiniteTalk workflow for audio-driven video dubbing cannot be completed in ComfyUI because the necessary audio input nodes are not present in the available node list. [WORKFLOW_PLAN.md]
- **Cause**: The provided node list for ComfyUI does not include specific nodes for feeding audio into the InfiniteTalk model. [WORKFLOW_PLAN.md]
- **Fix**: Not in sources: A specific fix for missing audio input nodes in ComfyUI is not provided in the evidence.

### Unclear mechanism for applying InfiniteTalk model patches
- **Symptom**: It is unclear how to correctly apply the `Wan2_1-InfiniteTalk-Single_fp8_e4m3fn_scaled_KJ.safetensors` or `wan2.1_infiniteTalk_multi_fp16.safetensors` model patches in ComfyUI. [WORKFLOW_PLAN.md]
- **Cause**: The provided material does not explicitly detail the mechanism for applying these model patches, such as whether to use `ModelMergeWAN2_1` or `Wan21BlockLoraSelect`. [WORKFLOW_PLAN.md]
- **Fix**: Not in sources: A specific fix for applying InfiniteTalk model patches is not provided in the evidence.

## General Unknowns

### Exact VRAM requirements for 14B models without offloading or quantization
- **Symptom**: Users may not know the exact VRAM required to run the 14B models without using offloading or quantization. [MODEL.md]
- **Cause**: The sources do not state the exact VRAM requirements for the 14B models in this configuration. [MODEL.md]
- **Fix**: Not in sources: A specific fix for determining exact VRAM requirements is not provided in the evidence.

### Specific Python dependencies for node packs
- **Symptom**: Users may not know the specific Python dependencies required for the ComfyUI node packs used with Wan 2.1. [MODEL.md]
- **Cause**: The sources do not list the specific Python dependencies for the node packs. [MODEL.md]
- **Fix**: Not in sources: A specific fix for identifying Python dependencies is not provided in the evidence.

### Exact ComfyUI server configuration for Wan 2.1
- **Symptom**: Users may not know the exact configuration of the ComfyUI server for Wan 2.1, such as specific node graph structures. [MODEL.md]
- **Cause**: The sources do not detail the exact configuration of the ComfyUI server beyond the existence of API-format graphs. [MODEL.md]
- **Fix**: Not in sources: A specific fix for determining exact ComfyUI server configuration is not provided in the evidence.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
