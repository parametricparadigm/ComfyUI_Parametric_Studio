# PITFALLS - 21-SAM-segmentation-matting

## SAM 2.1 Checkpoint Compatibility
*   **Symptom**: Model fails to load or produces incorrect results when using SAM 2.1 checkpoints with older code versions.
*   **Cause**: SAM 2.1 checkpoints require the latest model code from the `facebookresearch/segment-anything-2` repository. Using an earlier version of the repo causes incompatibility.
*   **Fix**: Uninstall the previous version via `pip uninstall SAM-2`, pull the latest code from the repo using `git pull`, and reinstall the repository following the installation instructions.
*   **Source**: [WORKFLOW_PLAN.md] [PUBLIC README https://raw.githubusercontent.com/facebookresearch/sam2/HEAD/README.md]

## SAM 2 CUDA Extension Build Failure
*   **Symptom**: Installation logs show a message like `Failed to build the SAM 2 CUDA extension`.
*   **Cause**: The custom CUDA kernel compilation failed, often due to missing `nvcc` compiler or version mismatch with PyTorch CUDA version.
*   **Fix**: This can be ignored; SAM 2 can still be used, though some post-processing functionality may be limited. It does not affect results in most cases. Ensure `nvcc` is installed with a version matching the PyTorch CUDA version if full functionality is required.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/facebookresearch/sam2/HEAD/README.md]

## SAM 2.1 VRAM Usage
*   **Symptom**: High memory consumption or potential out-of-memory errors when running the "large" model variant.
*   **Cause**: The `sam2.1_hiera_large-fp16.safetensors` model variant is large and requires significant VRAM.
*   **Fix**: Not explicitly provided in sources, but implies monitoring VRAM usage. The local environment has a 96 GB GPU, which may mitigate this, but the risk is noted for the "large" variant.
*   **Source**: [WORKFLOW_PLAN.md]

## SAM 3 Model Size and VRAM
*   **Symptom**: Potential VRAM pressure or loading issues.
*   **Cause**: The `sam3/sam3.pt` model file is 3.45 GB, which may require significant VRAM.
*   **Fix**: Not explicitly provided in sources.
*   **Source**: [WORKFLOW_PLAN.md]

## BiRefNet Code Version Mismatch
*   **Symptom**: Potential issues if using HuggingFace weights with outdated code.
*   **Cause**: When using weights from HuggingFace with code from HuggingFace, the codes might not be the latest version.
*   **Fix**: Use codes from the GitHub repository (`ZhengPeng7/BiRefNet`) combined with weights from HuggingFace to ensure the codes are always latest.
*   **Source**: [PUBLIC README https://huggingface.co/ZhengPeng7/BiRefNet/raw/main/README.md]

## BiRefNet Resolution Constraints
*   **Symptom**: Incorrect mask alignment or quality issues if input resolution is not handled correctly.
*   **Cause**: BiRefNet supports dynamic resolutions, but the inference example resizes images to `(1024, 1024)` before processing and then resizes the mask back to the original image size.
*   **Fix**: Ensure the pipeline resizes the input to the expected model input size (e.g., 1024x1024 in the example) and resizes the output mask back to the original image dimensions for compositing.
*   **Source**: [PUBLIC README https://huggingface.co/ZhengPeng7/BiRefNet/raw/main/README.md]

## SAM Original Text Input Limitation
*   **Symptom**: Attempting to use text prompts with the original SAM ViT-B model fails or is unsupported.
*   **Cause**: The official model does not support passing text as input at the time of the documentation.
*   **Fix**: Use point or bounding box prompts instead of text for the original SAM ViT-B model.
*   **Source**: [PUBLIC README https://huggingface.co/facebook/sam-vit-base/raw/main/README.md]

## SAM 2.1 Local File Path Mapping
*   **Symptom**: Node fails to find the model or attempts to download it instead of using the local file.
*   **Cause**: The `DownloadAndLoadSAM2Model` node implies a download capability, but the task constraints specify using only local files. If the local path is not correctly mapped in the COMBO selection, it may not load the intended local file.
*   **Fix**: Ensure the local path is correctly mapped in the COMBO selection to point to the local file (e.g., `sam2/sam2.1_hiera_large-fp16.safetensors`).
*   **Source**: [WORKFLOW_PLAN.md]

## SAM 3 Node Input Requirements
*   **Symptom**: Node execution fails or behaves unexpectedly if optional inputs are not handled.
*   **Cause**: The `SAM3Grounding` node requires `SAM3_BOXES_PROMPT` and `SAM3_POINTS_PROMPT` inputs in addition to the model config and image, even if text grounding is the primary mode.
*   **Fix**: Provide these inputs, even if they are empty or default, to satisfy the node signature.
*   **Source**: [WORKFLOW_PLAN.md]

## Environment Dependency Conflicts
*   **Symptom**: Models are not usable in the studio backend.
*   **Cause**: Python dependencies for the node packs may not be in the Parametric Studio (PS) venv, nodes may not be placeable in API-format graphs, or they may conflict with PS torch/CUDA pins.
*   **Fix**: Ensure Python dependencies are in the PS venv, nodes are compatible with API-format graphs, and there are no conflicts with PS torch/CUDA pins.
*   **Source**: [MODEL.md]

## Not in sources: Specific VRAM limits (GB) for each model variant.
## Not in sources: Specific quantization format incompatibilities (e.g., INT8, INT4) beyond FP16/FP32 mentions.
## Not in sources: Specific scheduler incompatibilities.
## Not in sources: Exact API graph configurations for each model.
## Not in sources: Performance benchmarks (FPS, latency) for these specific models on the local hardware.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
