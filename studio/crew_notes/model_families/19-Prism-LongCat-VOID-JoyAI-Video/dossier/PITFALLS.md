# PITFALLS - 19-Prism-LongCat-VOID-JoyAI-Video

## VRAM and Hardware Limits

### High VRAM Usage in Prism-Alpha Pipeline
*   **Symptom**: Potential out-of-memory errors or extreme slowdowns when running the Prism-Alpha pipeline.
*   **Cause**: The pipeline requires loading multiple large diffusion models simultaneously, including `video_dit.safetensors`, `video_dit_2.safetensors`, `audio_dit.safetensors`, and `dual_tower_bridge.safetensors`.
*   **Fix**: Not explicitly stated in sources; ensure sufficient VRAM is available for simultaneous loading of these components.
*   **Source**: [WORKFLOW_PLAN.md]

### High VRAM Usage in LongCat-Avatar-15
*   **Symptom**: Potential out-of-memory errors or extreme slowdowns when running LongCat-Avatar-15.
*   **Cause**: The main diffusion model `LongCat-Avatar-15_bf16.safetensors` is 31.71 GB, and the audio encoder is also large.
*   **Fix**: Not explicitly stated in sources; ensure sufficient VRAM is available for the 31.71 GB model and audio encoder.
*   **Source**: [WORKFLOW_PLAN.md]

### High VRAM Usage in JoyAI-Video-Edit
*   **Symptom**: Potential out-of-memory errors or extreme slowdowns when running JoyAI-Video-Edit.
*   **Cause**: The main diffusion model `joyai_video_edit_dit_0811.pth` is 32.53 GB, and multiple text encoder parts are loaded.
*   **Fix**: Not explicitly stated in sources; ensure sufficient VRAM is available for the 32.53 GB model and text encoders.
*   **Source**: [WORKFLOW_PLAN.md]

## Precision and Quantization Issues

### Mixed Precision Requirements
*   **Symptom**: Potential compatibility issues or unexpected behavior if precision settings are not managed correctly.
*   **Cause**: Models are stored in various precisions including `bf16`, `fp16`, and `fp8`. For example, `UMT5-XXL` is `fp8` and `LongCat-Avatar-15` DiT is `bf16`. Prism-Alpha text encoder uses mixed precision.
*   **Fix**: Ensure the inference engine and loaders respect the specific precision of each component (e.g., `umt5_xxl_fp8_e4m3fn_scaled.safetensors` is `fp8`).
*   **Source**: [MODEL.md]

### GGUF Quantization Compatibility
*   **Symptom**: Inability to load models or errors when using standard loaders.
*   **Cause**: The local installation includes quantized GGUFs for LongCat-Video-Avatar 1.5 and LongCat-Video-Avatar, which are intended for ComfyUI + WanVideoWrapper.
*   **Fix**: Use the specific ComfyUI + WanVideoWrapper setup for GGUF files.
*   **Source**: [SOURCES.md]

## Incompatibilities and Version Conflicts

### Attention Mechanism Configuration
*   **Symptom**: Performance degradation or errors if the attention mechanism is not supported by the hardware or software stack.
*   **Cause**: `FlashAttention-2` is enabled by default in the model config.
*   **Fix**: You can change the model config to use `FlashAttention-3` or `xformers` if `FlashAttention-2` is not suitable.
*   **Source**: [MODEL.md], [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Python Dependency Requirements
*   **Symptom**: Node packs failing to load or execute.
*   **Cause**: The Python dependencies for the node packs must be present in the Parametric Studio venv. The exact dependencies for "model-bound only" node packs are not listed.
*   **Fix**: Ensure all required Python dependencies are installed in the correct virtual environment.
*   **Source**: [MODEL.md]

### Torch/CUDA Version Pins
*   **Symptom**: Potential conflicts if the environment does not match the model requirements.
*   **Cause**: The models are standard diffusion models and do not conflict with PS torch/CUDA pins, but specific versions are recommended for the base LongCat-Video repo (e.g., `torch==2.6.0+cu124`).
*   **Fix**: Follow the installation instructions for the base model if using the native repo, ensuring `torch` and `flash_attn` versions match.
*   **Source**: [MODEL.md], [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

## Configuration and Parameter Pitfalls

### Audio CFG Value for Lip Sync
*   **Symptom**: Poor lip synchronization accuracy.
*   **Cause**: The Audio CFG value is not set optimally.
*   **Fix**: Audio CFG works optimally between 3–5. Increase the audio CFG value for better synchronization.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Reference Image Index for Repeated Actions
*   **Symptom**: Repeated actions in the generated video.
*   **Cause**: The `--ref_img_index` is not set appropriately.
*   **Fix**: Setting the reference image index (`--ref_img_index`, default to 10) between 0 and 24 ensures better consistency. Setting it to 30 helps reduce repeated actions.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Mask Frame Range for Repeated Actions
*   **Symptom**: Repeated actions or artifacts in the video.
*   **Cause**: The `--mask_frame_range` is not set appropriately.
*   **Fix**: Increasing the mask frame range (`--mask_frame_range`, default to 3) can help mitigate repeated actions, but excessively large values may introduce artifacts.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Dual-Audio Mode Length Requirements
*   **Symptom**: Errors or unexpected audio output in dual-audio modes.
*   **Cause**: In Merge mode (`audio_type` set to `para`), the two audio clips are not of equal length.
*   **Fix**: Merge mode requires two audio clips of equal length. Concatenation mode (`audio_type` set to `add`) does not require equal-length inputs.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Prompt Length and Detail
*   **Symptom**: Poor consistency and naturalness in generated videos.
*   **Cause**: Using short or vague prompts.
*   **Fix**: Longer, more descriptive prompts yield better consistency and naturalness. Include rich details such as character appearance, actions, and scene context.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

### Resolution Control
*   **Symptom**: Output resolution does not match expectations.
*   **Cause**: The `--resolution` parameter is not set.
*   **Fix**: The model is compatible with both 480P and 720P, controlled via `--resolution`.
*   **Source**: [PUBLIC README https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5/raw/main/README.md]

## Missing Information and Unknowns

### Specific Performance Benchmarks
*   **Symptom**: Uncertainty about generation speed or quality metrics on local hardware.
*   **Cause**: Specific performance benchmarks are not stated in the sources.
*   **Fix**: Not in sources: Specific performance benchmarks (e.g., generation speed, quality metrics) for these models on the local hardware.
*   **Source**: [MODEL.md]

### Python Dependencies for Model-Bound Packs
*   **Symptom**: Uncertainty about which Python packages are needed for specific node packs.
*   **Cause**: The exact Python dependencies required for the "model-bound only" node packs are not listed.
*   **Fix**: Not in sources: The exact Python dependencies required for the "model-bound only" node packs.
*   **Source**: [MODEL.md]

### Prism-Alpha and JoyAI-Video-Edit Configuration
*   **Symptom**: Uncertainty about how to configure specific parameters for these pipelines.
*   **Cause**: The specific configuration settings for the Prism-Alpha and JoyAI-Video-Edit pipelines beyond the model file names are not detailed.
*   **Fix**: Not in sources: The specific configuration settings for the Prism-Alpha and JoyAI-Video-Edit pipelines beyond the model file names.
*   **Source**: [MODEL.md]

### Relationship Between VOID Packs and Models
*   **Symptom**: Uncertainty about how "VOID" node packs interact with the "Prism / LongCat / JoyAI" models.
*   **Cause**: The relationship is not explicitly defined in the material.
*   **Fix**: Not in sources: The relationship between the "VOID" node packs and the "Prism / LongCat / JoyAI" models.
*   **Source**: [MODEL.md]

### Workflow Plan Validation
*   **Symptom**: Potential errors when executing the drafted workflow plans.
*   **Cause**: The workflow plans are marked as "DRAFT: not run or tested" and have automatic check flags for unknown node IDs or local files.
*   **Fix**: Review and test the workflow plans before production use.
*   **Source**: [WORKFLOW_PLAN.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
