# PITFALLS - 09-Flux.1-dev-schnell-Kontext-Fill

## 1. Sharded Model Loading Failure
**Symptom**: The workflow plan for Flux.1 Dev with ControlNet or PuLID is not executable because the `FluxLoader` node may not support sharded models natively.
**Cause**: The main diffusion model for Flux.1 Dev is stored as three separate files (`diffusion_pytorch_model-00001-of-00003.safetensors`, `diffusion_pytorch_model-00002-of-00003.safetensors`, `diffusion_pytorch_model-00003-of-00003.safetensors`), but the `FluxLoader` node typically expects a single file or a folder and may not handle sharded models directly without a specific wrapper.
**Fix**: Verify if `FluxLoader` can point to the `_complete_pipelines/Flux.1/diffusers/flux1-dev-pipeline` folder or if a specific wrapper is required. If it cannot load sharded models directly, the plan is invalid with the provided nodes.
**Source**: [WORKFLOW_PLAN.md]

## 2. Missing Face Analysis Model for PuLID
**Symptom**: Plan 3 (Flux.1 Dev with PuLID Face Preservation) is not executable.
**Cause**: The `PulidFluxInsightFaceLoader` node requires a `COMBO` input for a face analysis model (specifically `buffalo_l`), but this model is not listed in the local files. The local installation only contains `pulid_flux_v0.9.1.safetensors`.
**Fix**: The plan must be skipped or an alternative (such as IP-Adapter) must be used, as the required face analysis model is missing from the local environment.
**Source**: [WORKFLOW_PLAN.md]

## 3. Sampler Input Mismatch for Custom Sigmas
**Symptom**: The standard `KSampler` node does not accept the `SIGMAS` output from `Sigmax.Flux1SchnellSigmaScheduler`.
**Cause**: Standard `KSampler` takes `steps`, `cfg`, `sampler_name`, `scheduler`, `seed`, and `denoise`, but does not have a `SIGMAS` input. `KSamplerAdvanced` also does not take `SIGMAS` directly.
**Fix**: Use `SamplerCustomAdvanced` instead, which accepts `SIGMAS` input. Connect the `SIGMAS` from `Sigmax.Flux1SchnellSigmaScheduler` to `SamplerCustomAdvanced`.
**Source**: [WORKFLOW_PLAN.md]

## 4. Unknown Default Sampling Settings
**Symptom**: Specific default sampling steps and guidance scales are not stated in the provided materials, leading to potential configuration errors.
**Cause**: The documentation and local files do not specify default values for sampling steps or guidance scales for the Flux.1 models.
**Fix**: These settings must be determined by the user or defined explicitly in the workflow, as they are not provided in the sources.
**Source**: [MODEL.md]

## 5. License Restrictions for Commercial Use
**Symptom**: Potential legal issues if models are used commercially without proper licensing.
**Cause**: Most variants (dev, Fill, Canny, Depth, Redux, Kontext, Krea) are under the `FLUX.1-dev Non-Commercial License`. Only `FLUX.1 [schnell]` is under `apache-2.0`.
**Fix**: For commercial use, license the models via BFL pricing or enable usage tracking via the BFL API (`--track_usage`) if using open weights commercially.
**Source**: [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux/HEAD/README.md]

## 6. TensorRT Installation Complexity
**Symptom**: Standard installation may not support TensorRT acceleration.
**Cause**: TensorRT support requires installing a specific PyTorch image from NVIDIA using `enroot` and a specific pip install command with `--extra-index-url`.
**Fix**: Follow the specific TensorRT installation steps: install `enroot`, import the `nvidia/pytorch:25.01-py3` image, and run `pip install -e ".[tensorrt]" --extra-index-url https://pypi.nvidia.com`.
**Source**: [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux/HEAD/README.md]

## 7. VRAM and Precision Management
**Symptom**: Large models may exceed VRAM limits on consumer hardware.
**Cause**: The Flux.1 DiT transformer is 11.9B params in BF16, and the total local size is 112 GB.
**Fix**: Use asynchronous weight streaming technology (supported by ComfyUI) to manage VRAM usage, allowing large models to run on consumer hardware. ComfyUI can run models on as low as 4GB vram + 8GB ram using this technology.
**Source**: [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/Comfy-Org/ComfyUI/HEAD/README.md]

## 8. Quantized Model Compatibility
**Symptom**: Potential incompatibility or performance issues when using quantized models.
**Cause**: The local installation includes quantized models such as `svdq-fp4_r32-flux.1-dev.safetensors` (7.04 GB) and `fluxKleinFP8_flux2KleinBase9bFp8-nvfp4.safetensors` (5.83 GB).
**Fix**: Ensure the ComfyUI version and node packs support the specific quantization formats (FP8, FP4) used in these files.
**Source**: [MODEL.md]

## 9. Node Pack Availability
**Symptom**: Some node packs may not be available in the pool pages.
**Cause**: Several top packs (e.g., `ComfyUI-FluxTrainer.disabled`, `PeterMikhai__Doom_Flux_NodePack`, `ComfyUI-Fluxtapoz`) are marked as "not in the pool pages (model-bound only)".
**Fix**: Verify that these specific packs are installed and enabled in the ComfyUI environment, as they are not part of the standard pool pages.
**Source**: [MODEL.md]

## 10. ComfyUI Version Stability
**Symptom**: Potential instability or broken custom nodes.
**Cause**: Commits outside of the stable release tags in ComfyUI may be very unstable and break many custom nodes.
**Fix**: Use a stable release version of ComfyUI (e.g., v0.43.0 as noted in the local setup) rather than master branch commits.
**Source**: [PUBLIC README https://raw.githubusercontent.com/Comfy-Org/ComfyUI/HEAD/README.md], [MODEL.md]

Not in sources: Specific VRAM limits for each precision format (BF16, FP8, FP4) beyond the general asynchronous weight streaming capability.
Not in sources: Specific scheduler incompatibilities beyond the `SIGMAS` input issue with `KSampler` and `KSamplerAdvanced`.
Not in sources: Specific version incompatibilities for the Flux.1 models themselves (e.g., commit hashes or release tags).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
