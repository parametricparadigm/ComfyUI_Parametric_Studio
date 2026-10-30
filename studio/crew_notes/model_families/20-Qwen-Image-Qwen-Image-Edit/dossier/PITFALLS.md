# PITFALLS - 20-Qwen-Image-Qwen-Image-Edit

## Version and Repository Incompatibilities

**Symptom**: Using outdated or incorrect model repositories leads to suboptimal performance or missing features.
**Cause**: The `Qwen/Qwen-Image-2.1` repository is superseded by `Comfy-Org/Qwen-Image-2.1`, which has significantly higher downloads and is the standard for ComfyUI integration. Additionally, `Comfy-Org/Qwen-Image` is an older version superseded by `Comfy-Org/Qwen-Image-2.1`. The `Qwen/Qwen-Image-Edit` repository is also noted as an older version, superseded by newer edit models or covered by the main `Qwen-Image-Edit` HF repo.
**Fix**: Use `Comfy-Org/Qwen-Image-2.1` for ComfyUI integration. For the latest editing capabilities, refer to `Qwen/Qwen-Image-Edit-2511` or `Qwen/Qwen-Image-Edit-2509` as indicated in the news sections, rather than the initial `Qwen/Qwen-Image-Edit` release.
[MODEL.md] [SOURCES.md]

**Symptom**: License conflicts or unexpected restrictions when using repackaged models.
**Cause**: The base models are licensed under Apache 2.0, but specific ComfyUI repackaged versions (such as `Comfy-Org/Qwen-Image-2.1`) are under a "qwen-research" license.
**Fix**: Verify the license terms for `Comfy-Org/Qwen-Image-2.1` before commercial use, as it differs from the Apache 2.0 license of the base `Qwen/Qwen-Image` models.
[MODEL.md] [SOURCES.md]

## Precision and VRAM Constraints

**Symptom**: High VRAM usage or potential out-of-memory errors during inference.
**Cause**: The model utilizes a 20B MMDiT architecture. The largest local file, `diffusion_pytorch_model.safetensors`, is 40.86 GB. While this fits within the 96 GB VRAM of the local Blackwell GPU, the total local size is 111 GB, and simultaneous loading of multiple large components (e.g., 14.23 GB diffusion model + 3.54 GB ControlNet) increases memory pressure.
**Fix**: Ensure the backend is running on a GPU with sufficient VRAM (96 GB confirmed locally). Monitor VRAM usage when combining large diffusion models with ControlNets or other adapters.
[MODEL.md] [WORKFLOW_PLAN.md]

**Symptom**: Suboptimal performance or errors when using incorrect data types.
**Cause**: The model is designed for `bfloat16` precision on CUDA devices. Using `float32` on CUDA or incorrect dtypes may lead to inefficiencies or errors.
**Fix**: Use `torch.bfloat16` for CUDA inference. The local model files are provided in `bf16` format (e.g., `qwen_image_2.1_bf16.safetensors`).
[MODEL.md] [SOURCES.md]

## Inference Settings and Turbo Variants

**Symptom**: Poor image quality or failure to converge when using Turbo models with standard settings.
**Cause**: Turbo LoRAs and models are optimized for reduced inference steps and specific CFG scales. Standard models typically use 50 steps and `true_cfg_scale` of 4.0, whereas Turbo LoRAs are designed for 5, 6, or 8 steps and `true_cfg_scale` of 1.0.
**Fix**: When using Turbo LoRAs (e.g., `p_q_image_2.1_5_steps_v0.1_comfyui_bf16.safetensors`), set the inference steps to 5, 6, or 8 and `true_cfg_scale` to 1.0. Do not use the standard 50 steps and 4.0 CFG for Turbo variants.
[MODEL.md] [SOURCES.md] [WORKFLOW_PLAN.md]

**Symptom**: Missing Turbo LoRA files or confusion about available step counts.
**Cause**: The specific file names for Turbo LoRAs are not always listed in local file scans beyond the `loras_extra` folder, though the Comfy-Org documentation lists specific files like `p_q_image_2.1_5_steps_v0.1_comfyui_bf16.safetensors` (5 steps, cfg 1), `p_q_image_2.1_6_steps_v0.2_comfyui_bf16.safetensors` (6 steps, cfg 1), and `p_q_image_2.1_8_steps_v0.1_comfyui_bf16.safetensors` (8 steps, cfg 1).
**Fix**: Ensure the correct Turbo LoRA files are downloaded and placed in the `loras` folder as specified in the Comfy-Org README.
[MODEL.md] [SOURCES.md]

## Quantization and Format Issues

**Symptom**: Incompatibility or performance degradation when using quantized models.
**Cause**: Third-party quantized formats (e.g., `unsloth/Qwen-Image-2.1-GGUF`) are not the primary official sources. The official ComfyUI repackaged models include `int8_convrot` and `nvfp4` variants (e.g., `qwen_image_2.1_turbo_nvfp4.safetensors`), but these may have different compatibility requirements than the standard `bf16` models.
**Fix**: Prefer the official `bf16` models for maximum compatibility. If using quantized models, ensure they are from the official `Comfy-Org/Qwen-Image-2.1` repository and verify that the ComfyUI version supports the specific quantization format (e.g., `int8_convrot`, `nvfp4`).
[MODEL.md] [SOURCES.md]

## Workflow and Node Specifics

**Symptom**: Workflow failures due to incorrect node connections or missing dependencies.
**Cause**: The workflow plans are marked as "DRAFT: not run or tested" and have automatic checks flagging unknown node IDs or local files. For example, connections to `KSampler` inputs like `latent_image` or `model` may not match the actual node IDs in the installed ComfyUI version.
**Fix**: Verify node IDs and connections against the installed ComfyUI version. Ensure all Python dependencies for node packs are installed in the Parametric Studio venv.
[WORKFLOW_PLAN.md] [MODEL.md]

**Symptom**: Ineffective prompt enhancement.
**Cause**: The `qwen3.5_9b_qwen_image_2.1_pe` models are specifically for prompt enhancement and must be used with the `Generate Text` node. Using them in standard text encoding nodes may not yield the intended results.
**Fix**: Use the `Generate Text` node to leverage the Prompt Enhancer models for T2I and I2I tasks.
[SOURCES.md] [MODEL.md]

## Known Performance Misalignments

**Symptom**: Performance misalignments in Qwen-Image-Edit, particularly in identity preservation and instruction following.
**Cause**: An issue was observed in the initial release of Qwen-Image-Edit.
**Fix**: Update to the latest `diffusers` commit to ensure optimal results. The news section notes that improvements are expected in identity preservation and instruction following with the update.
[SOURCES.md]

## Not in Sources

- Specific VRAM usage numbers for individual inference steps or batch sizes.
- Detailed error messages for specific quantization format incompatibilities.
- Specific node IDs for all 714 nodes across 185 packs.
- Exact performance metrics for `int8_convrot` vs `bf16` models.
- Specific steps or CFG values for the `Qwen-Image-Edit-2509` or `Qwen-Image-Edit-2511` models beyond the general 50 steps and 4.0 CFG for standard models.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
