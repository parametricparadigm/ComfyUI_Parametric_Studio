# PITFALLS - 26-Upscale-restore-models

## VRAM and Precision Constraints

### SeedVR2 7B VRAM Usage
- **Symptom**: High memory consumption during video upscaling.
- **Cause**: The `seedvr2_7b_sharp_fp8_e4m3fn.safetensors` model is 8.24 GB in size.
- **Fix**: Ensure the hardware has sufficient VRAM; the model fits within the 96 GB Blackwell GPU, but significant VRAM is required. [WORKFLOW_PLAN.md] [MODEL.md]

### Mixed Precision Compatibility (SeedVR2)
- **Symptom**: Potential hardware compatibility issues when loading the SeedVR2 pipeline.
- **Cause**: The DiT model uses `fp8_e4m3fn` precision while the VAE (`ema_vae_fp16.safetensors`) uses `fp16` precision.
- **Fix**: Ensure hardware compatibility with these specific mixed precisions. [WORKFLOW_PLAN.md]

### SDXL-Turbo Resolution Limitation
- **Symptom**: Generated images may not match desired high-resolution outputs if expecting native high-res generation.
- **Cause**: The model is intended for a fixed resolution of 512x512 pixels, though higher sizes work.
- **Fix**: Use the model for 512x512 generation and apply upscaling models (like those in this family) for higher resolutions. [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

### SDXL-Turbo Step Calculation
- **Symptom**: Incorrect number of inference steps executed in image-to-image pipelines.
- **Cause**: The pipeline runs for `int(num_inference_steps * strength)` steps. If this product is less than 1, the behavior may be unexpected.
- **Fix**: Ensure that `num_inference_steps` * `strength` is larger or equal to 1. [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md]

## Incompatibilities and Environment Issues

### AuraSR Node Pack Status
- **Symptom**: `LoadAuraSR` or `RunAuraSR` nodes may not be available or active in the standard environment.
- **Cause**: The node pack `ComfyUI-AuraSR` is marked as `.disabled` in the material.
- **Fix**: Verify the status of the `ComfyUI-AuraSR` pack in the local environment before attempting to use `aurasr_v2.safetensors`. [WORKFLOW_PLAN.md]

### Python Dependency Uncertainty
- **Symptom**: Node packs may fail to load or execute due to missing libraries.
- **Cause**: The specific Python dependencies required for each node pack are not stated in the provided material.
- **Fix**: Manually verify and install dependencies for each specific node pack in the Parametric Studio virtual environment. [MODEL.md]

### Torch/CUDA Version Conflict Risk
- **Symptom**: Models or nodes may fail to initialize or run.
- **Cause**: Models must not conflict with the pinned `torch` and `CUDA` versions in the Parametric Studio environment, but compatibility of each node pack with these specific versions is not stated.
- **Fix**: Test node packs against the pinned `torch` and `CUDA` versions before deployment. [MODEL.md]

### OptiScaler Fake Website Scams
- **Symptom**: Users may download malicious software or pay for free tools.
- **Cause**: Fake websites present themselves as the OptiScaler team, and fake manager apps exist.
- **Fix**: Only download from the official GitHub, Discord server, or Nitec's NexusMods page. OptiScaler is free; any monetary requirements are scams. [PUBLIC README https://raw.githubusercontent.com/optiscaler/OptiScaler/HEAD/README.md]

### OptiScaler RTSS Compatibility
- **Symptom**: Potential conflicts or issues when using OptiScaler alongside RTSS.
- **Cause**: Known issues regarding RTSS compatibility exist.
- **Fix**: Check the "OptiScaler known issues" section in the official documentation regarding RTSS. [PUBLIC README https://raw.githubusercontent.com/optiscaler/OptiScaler/HEAD/README.md]

### Unreal Engine XeSS Input Limitation
- **Symptom**: Replacing in-game XeSS in Unreal Engine games breaks other upscalers.
- **Cause**: The Unreal Engine plugin does not provide depth information.
- **Fix**: For Unreal Engine games, only UE XeSS -> Opti XeSS/FSR4 works. You can still apply RCAS sharpening to XeSS to reduce blurry visuals. [PUBLIC README https://raw.githubusercontent.com/optiscaler/OptiScaler/HEAD/README.md]

## Missing Information (Not in Sources)

- Not in sources: Specific tile size values for SeedVR2 Tiler or other tiling models.
- Not in sources: Specific denoise strength values for NAFNet.
- Not in sources: Performance benchmarks (speed, quality) for any model in the family.
- Not in sources: Specific URLs for downloading the local models (as they are already present locally).
- Not in sources: Exact configuration parameters for `RunAuraSR` scale factor.
- Not in sources: Specific settings for the `SeedVR2PostProcessing` node.
- Not in sources: Compatibility details for `RealESRGANNode` with specific `torch` versions.
- Not in sources: Known issues for Waifu2x-Extension-GUI specific to the local GPU architecture (sm_120).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
