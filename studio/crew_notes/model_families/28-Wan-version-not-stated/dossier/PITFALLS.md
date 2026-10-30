# PITFALLS - 28-Wan-version-not-stated

## VRAM and Memory Limits

### Out-of-Memory (OOM) errors during inference
- **Symptom**: The inference process crashes or fails to start due to insufficient GPU memory.
- **Cause**: The model weights and intermediate activations exceed the available VRAM on the GPU.
- **Fix**: Use the `--offload_model True` and `--t5_cpu` options to reduce GPU memory usage. For Wan2.2, also use `--convert_model_dtype` to convert model data types. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md] [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

### Insufficient VRAM for Wan2.2 T2V-A14B
- **Symptom**: The model cannot run on GPUs with less than 80GB VRAM without optimization.
- **Cause**: The Wan2.2 T2V-A14B model requires significant memory resources.
- **Fix**: Ensure the GPU has at least 80GB VRAM, or apply memory reduction flags such as `--offload_model True`, `--convert_model_dtype`, and `--t5_cpu`. [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

### Unknown VRAM requirements for specific quantized variants
- **Symptom**: Uncertainty regarding whether a specific quantized model (e.g., FP8, NVFP4) will fit in the available 96 GB VRAM.
- **Cause**: The local documentation does not explicitly state the exact VRAM requirements for each specific quantized variant on the 96 GB Blackwell card.
- **Fix**: Not in sources: Specific VRAM requirements for each quantized variant. Users must test empirically or rely on general offloading options. [MODEL.md]

## Resolution and Stability Issues

### Unstable results at 720P for T2V-1.3B
- **Symptom**: Generated videos at 720P resolution are generally less stable compared to 480P.
- **Cause**: Limited training of the T2V-1.3B model at 720P resolution.
- **Fix**: Use 480P resolution for optimal performance with the T2V-1.3B model. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

### Incorrect resolution support for I2V models
- **Symptom**: Attempting to run the I2V-14B-720P model at 480P or the I2V-14B-480P model at 720P.
- **Cause**: Each I2V variant is trained and optimized for a specific resolution; the 720P model does not support 480P and vice versa.
- **Fix**: Use `Wan2.1-I2V-14B-720P` for 720P generation and `Wan2.1-I2V-14B-480P` for 480P generation. [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P/raw/main/README.md]

## Incompatibilities and Missing Components

### Missing node for Wan2.2-Dancer audio conditioning
- **Symptom**: Inability to construct a complete ComfyUI workflow for Wan2.2-Dancer using only the listed local nodes.
- **Cause**: The node list does not contain a specific "Wan2.2-Dancer Audio Loader" or "Wav2Vec2 Loader" to produce the required `AUDIO_ENCODER_OUTPUT` from the local `wav2vec2_large_english_fp16.safetensors` file.
- **Fix**: Not in sources: A specific node to load the Wav2Vec2 encoder for Dancer. The workflow plan notes this as a risk and suggests the plan is not possible with the current listed nodes. [WORKFLOW_PLAN.md]

### Missing text encoder file in local model list
- **Symptom**: Workflow plans for Wan2.1 and Wan2.2 assume a standard T5 encoder is available, but the specific file is not listed in the local model files.
- **Cause**: The local model inventory does not explicitly list the text encoder file required for `CLIPLoader` or `CLIPTextEncode` steps.
- **Fix**: Not in sources: The specific text encoder file name. Users must verify the presence of a compatible T5 encoder in the local environment. [WORKFLOW_PLAN.md]

### Missing ONNX detection model for Wan2.2-Animate
- **Symptom**: Inability to load the pose detection model required for the Wan2.2-Animate workflow.
- **Cause**: The ONNX detection model file is not listed in the local model files.
- **Fix**: Not in sources: The specific ONNX detection model file. Users must ensure the required pose detection model is present. [WORKFLOW_PLAN.md]

### Unrelated software with similar names
- **Symptom**: Potential confusion when searching for Wan-related repositories or tools.
- **Cause**: Repositories such as `k1tbyte/Wand-Enhancer` (WeMod extension) and `wangeditor-team/wangEditor` (Web rich text editor) share similar names but are unrelated to the Wan video models.
- **Fix**: Verify repository descriptions and authors to ensure the correct Wan-AI or Wan-Video repository is used. [MODEL.md]

## Parameter and Configuration Warnings

### Suboptimal guidance scale for T2V-1.3B
- **Symptom**: Poor generation quality or instability when using default parameters for the T2V-1.3B model.
- **Cause**: The default `--sample_guide_scale` may not be optimal for the smaller 1.3B model.
- **Fix**: Set `--sample_guide_scale 6` for the T2V-1.3B model. Adjust `--sample_shift` within the range of 8 to 12 based on performance. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md]

### Uncertain inference steps for TurboWan2.2-I2V
- **Symptom**: Uncertainty regarding the optimal number of inference steps for the TurboWan2.2-I2V variant.
- **Cause**: The specific number of inference steps required for optimal quality in the TurboWan2.2-I2V variant is not stated in the provided material.
- **Fix**: Not in sources: The exact number of inference steps for TurboWan2.2-I2V. [MODEL.md]

### Unknown version for Wan-SCAIL-2
- **Symptom**: Uncertainty regarding the specific version or capabilities of the "Wan-SCAIL-2" variant.
- **Cause**: The specific version of the Wan model used in the "Wan-SCAIL-2" folder is not detailed in the provided material.
- **Fix**: Not in sources: The specific version details for Wan-SCAIL-2. [MODEL.md]

## Hardware and Environment Constraints

### Dependency on specific PyTorch and CUDA versions
- **Symptom**: Potential compatibility issues if the environment does not match the required software stack.
- **Cause**: The backend uses a Python 3.12.3 venv with torch 2.16.0.dev20261027+cu134 and CUDA 13.4.
- **Fix**: Ensure the environment matches the specified Python, Torch, and CUDA versions to maintain compatibility with the 96 GB Blackwell GPU (sm_120). [MODEL.md]

### Multi-GPU inference requirements
- **Symptom**: Inability to run multi-GPU inference if dependencies are missing.
- **Cause**: Multi-GPU inference using FSDP + xDiT USP or DeepSpeed Ulysses requires specific packages like `xfuser>=0.4.1`.
- **Fix**: Install required dependencies such as `xfuser>=0.4.1` before running multi-GPU inference commands. [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B/raw/main/README.md] [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
