# PITFALLS - 08-Faces-identity-portrait-animation

## LongCat-Video-Avatar 1.5

### Torch and CUDA Version Mismatch
*   **Symptom**: Potential runtime errors or incompatibility when running LongCat-Video-Avatar 1.5 nodes in the Parametric Studio environment.
*   **Cause**: The source README for LongCat-Video-Avatar 1.5 mentions requirements for `torch 2.6.0+cu124` and `flash-attn 2.7.4.post1`, which differ from the Parametric Studio venv's `torch 2.16.0.dev20261027+cu134` and `CUDA 13.4`.
*   **Fix**: Verify if the specific Python dependencies required for the LongCat-Video-Avatar 1.5 nodes are compatible with the current PS venv; the specific dependencies are not listed in the local file scan, so manual verification against the PS torch/CUDA pins is required.
*   **Source**: [MODEL.md]

### Missing Audio Encoder Node
*   **Symptom**: The audio-driven aspect of the LongCat-Avatar 1.5 pipeline may not be fully executable using only the standard listed nodes.
*   **Cause**: The local file `whisper_large_v3_encoder_fp16.safetensors` is present, but no specific node ID for loading this Whisper encoder is listed in the available nodes. The `FantasyTalkingWav2VecEmbeds` node uses `WAV2VECMODEL`, which is not the same as the Whisper encoder.
*   **Fix**: The user must rely on a node not listed in the standard set or assume the `WanVideoSampler` handles audio via an unlisted input; the specific node to load and apply the Whisper encoder is not stated in the provided material.
*   **Source**: [WORKFLOW_PLAN.md]

### VRAM and Model Size
*   **Symptom**: High memory consumption during inference.
*   **Cause**: The `LongCat-Avatar-15_bf16.safetensors` diffusion model is 31.71 GB, and the `umt5_xxl_fp8_e4m3fn_scaled.safetensors` text encoder is 6.74 GB.
*   **Fix**: The hardware is a single shared 96 GB Blackwell card, which should accommodate the bf16 weights and associated encoders, but significant VRAM is required.
*   **Source**: [MODEL.md]

### GGUF Quantization Availability
*   **Symptom**: Uncertainty regarding the availability of quantized versions for lower VRAM setups.
*   **Cause**: The sources mention GGUF quantized versions, but they are not explicitly listed in the local file scan.
*   **Fix**: Only the full precision bf16 and fp8 variants are confirmed present locally; do not assume GGUF files are available without further verification.
*   **Source**: [MODEL.md]

## InstantCharacter

### Missing Flux Base Model
*   **Symptom**: The InstantCharacter identity preservation pipeline is not fully executable with only the listed local files.
*   **Cause**: The local model files do not include a Flux base model (e.g., `flux1-dev.safetensors`), which is required by the `IPAdapterFluxLoader` and `InstantCharacter` nodes designed for Flux.
*   **Fix**: Use `InstantCharacterLoadModelFromLocal` which might handle the full pipeline internally, or ensure a Flux base model is available separately, as the local files only list the IP-Adapter and SigLIP.
*   **Source**: [WORKFLOW_PLAN.md]

### Missing DINOv2 Model File
*   **Symptom**: The `LoadDINOv2Vision` node cannot be used with the local files.
*   **Cause**: The `DINOv2` model is listed in the folder roles but not in the local model files list; only `siglip` is listed.
*   **Fix**: Not in sources: Specific fix for missing DINOv2 file, but the node is available while the model file is not in the local list.
*   **Source**: [WORKFLOW_PLAN.md]

## LivePortrait

### Landmark Model Node Ambiguity
*   **Symptom**: Uncertainty regarding the specific node for loading `landmark.onnx`.
*   **Cause**: The `landmark.onnx` file is listed, but no specific node for loading it is listed in the "AVAILABLE NODES" section.
*   **Fix**: It is potentially used internally by `AdvancedLivePortrait`.
*   **Source**: [WORKFLOW_PLAN.md]

## General / Environment

### Python Version Compatibility for InsightFace/FaceXLib
*   **Symptom**: Potential incompatibility between InsightFace and FaceXLib models and the current environment.
*   **Cause**: The exact compatibility of the InsightFace and FaceXLib models with the current PS venv Python version (3.12.3) is not stated, as the Deep-Live-Cam source recommends Python 3.14.
*   **Fix**: Not in sources: Specific fix, but compatibility is not stated.
*   **Source**: [MODEL.md]

### OmniAvatar Role Uncertainty
*   **Symptom**: Unclear integration of OmniAvatar-14B with other face/identity models.
*   **Cause**: The role of the OmniAvatar-14B model in the context of the other face/identity models is not detailed beyond it being an avatar generation model.
*   **Fix**: Not in sources: Specific fix or detailed role.
*   **Source**: [MODEL.md]

### Node Pack Usability Requirements
*   **Symptom**: Node packs may not be usable in the Parametric Studio backend.
*   **Cause**: For a node pack to be usable, its Python dependencies must be in the Parametric Studio venv, its nodes must be placeable in an API-format graph, it must not conflict with the PS torch/CUDA pins, and any required model files must be present in the local model folders.
*   **Fix**: Ensure all these conditions are met before attempting to use a node pack.
*   **Source**: [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
