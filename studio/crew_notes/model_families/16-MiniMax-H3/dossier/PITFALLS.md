# PITFALLS - 16-MiniMax-H3

## Guidance Scale Configuration
*   **Symptom:** The model aborts execution or fails to generate output when the guidance scale is set to the default value (7.0) or any value above 1.0.
*   **Cause:** The model is distilled and cfg-free, requiring a specific guidance scale for optimal performance. The default configuration in some tools (like `sd-cli`) is 7.0, which is incompatible.
*   **Fix:** Explicitly set the guidance scale to `1.0`. In `sd-cli`, use the flag `--cfg-scale 1.0`. [https://huggingface.co/unsloth/MiniMax-H3-GGUF/raw/main/README.md] [MODEL.md]

## Denoiser Variant Selection
*   **Symptom:** The model cannot accept the intended input types (e.g., reference videos or audio) or behaves incorrectly for the task.
*   **Cause:** The model family consists of two separate checkpoints (`H3-Base-FL2VA` and `H3-Base-Ref2VA`) rather than a single model with configurable settings. Loading the wrong checkpoint limits the input modalities (e.g., `fl2va_pruned` only accepts text and frames, while `ref2va_pruned` accepts references).
*   **Fix:** Select the checkpoint that matches the task: use `fl2va_pruned` for text/frame inputs and `ref2va_pruned` for multi-modal reference inputs. [https://huggingface.co/unsloth/MiniMax-H3-GGUF/raw/main/README.md] [MODEL.md]

## Quantization Format Compatibility
*   **Symptom:** Suboptimal performance or inability to load the diffusion model on supported hardware.
*   **Cause:** Using `fp8_scaled` when `int8_convrot` is available, or attempting to use `int8_convrot` without PyTorch with `cu130` support.
*   **Fix:** Prefer `int8_convrot` for diffusion models if PyTorch with `cu130` is available. Use `fp8_scaled` only if `int8_convrot` cannot be used. [https://huggingface.co/Comfy-Org/MiniMax-H3/raw/main/README.md] [MODEL.md]

## Text Encoder Hardware Requirements
*   **Symptom:** Potential compatibility issues or unnecessary hardware constraints when loading the text encoder.
*   **Cause:** Misunderstanding the hardware requirements for the `nvfp4_awq` quantization of the Qwen3-VL-32B text encoder.
*   **Fix:** Note that the `nvfp4_awq` text encoder does not require a Blackwell GPU to use. [https://huggingface.co/Comfy-Org/MiniMax-H3/raw/main/README.md] [MODEL.md]

## VAE Input Ambiguity in ComfyUI Nodes
*   **Symptom:** Workflow plans may fail or produce incomplete audio/video output because the node signature lists a single `VAE` input, but the model requires both Video and Audio VAEs.
*   **Cause:** Nodes like `H3MultishotSampler` and `H3LongVideosFL2VA` have a single `VAE` input slot, while the pipeline requires `minimax_h3_video_vae_fp16.safetensors` and `minimax_h3_audio_vae_fp32.safetensors`. It is not stated in the material how the Audio VAE is connected if the node only accepts one VAE input.
*   **Fix:** This is a potential conflict in standard ComfyUI H3 workflows. It may require a specific node configuration, a different node not listed, or the node may handle the audio VAE internally. Verify node capabilities or use specific loaders if available. [WORKFLOW_PLAN.md]

## Missing Local Files for Advanced Features
*   **Symptom:** Inability to use ControlNets, LoRAs, or specific embeddings locally despite them being listed in the official README.
*   **Cause:** The local scan of `_complete_pipelines/MiniMax-H3` only confirmed 8 model files (diffusion models, text encoder, VAEs). Files such as `minimax_h3_fun_controlnet_union_pruned_bf16.safetensors`, LoRAs (e.g., `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`), and embeddings were not listed in the "LARGEST LOCAL FILES" scan.
*   **Fix:** Verify if these files need to be downloaded separately or if they are missing from the local installation. [MODEL.md]

## H3-Context-IR Availability
*   **Symptom:** Inability to use the full official preprocessing pipeline locally.
*   **Cause:** `H3-Context-IR` is a hosted preprocessing and orchestration system that is not included in the open-source release.
*   **Fix:** Use the API for `H3-Context-IR` or follow the "Prompting Guidance" to build a custom context-processing system. [MODEL.md] [https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/README.md]

## Node Pack Dependencies
*   **Symptom:** Node packs fail to function or throw errors due to missing Python dependencies.
*   **Cause:** The node packs require specific Python dependencies to be in the PS venv. For example, `ComfyUI_MiniMaxH3_Director` requires `scenedetect`, `opencv-python-headless`, and `imageio-ffmpeg`.
*   **Fix:** Install the required dependencies in the PS venv. [MODEL.md]

## License Restrictions
*   **Symptom:** Legal or compliance issues when using the model in certain jurisdictions.
*   **Cause:** The model is distributed under the MiniMax H3 Community License Agreement, which defines an Applicable Territory and excludes some jurisdictions.
*   **Fix:** Read the full license text and the Q&A about the license before use. [https://huggingface.co/unsloth/MiniMax-H3-GGUF/raw/main/README.md]

## Sparse Attention Limitation
*   **Symptom:** Higher computational cost for long multimodal sequences.
*   **Cause:** The initial open-source release provides inference with full attention only. Sparse-attention implementation is not yet available.
*   **Fix:** Not in sources: specific workaround for sparse attention. [https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/README.md]

## VRAM Usage During Inference
*   **Symptom:** Potential out-of-memory errors during inference.
*   **Cause:** The exact VRAM usage during inference (including activations and intermediate tensors) is not stated; only file sizes are provided.
*   **Fix:** Not in sources: specific VRAM optimization techniques. [MODEL.md]

## Performance Benchmarks
*   **Symptom:** Uncertainty about generation speed.
*   **Cause:** Performance benchmarks (e.g., generation time per second of video) for the MiniMax H3 models on the specific Blackwell GPU are not stated.
*   **Fix:** Not in sources: performance benchmarks. [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
