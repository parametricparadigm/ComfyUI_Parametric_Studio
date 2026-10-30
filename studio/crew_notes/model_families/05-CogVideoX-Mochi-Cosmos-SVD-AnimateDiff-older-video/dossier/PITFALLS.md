# PITFALLS - 05-CogVideoX-Mochi-Cosmos-SVD-AnimateDiff-older-video

## Missing Core Model Files (Mochi)
*   **Symptom**: Workflow construction fails or is invalid because the main diffusion model weights are absent.
*   **Cause**: The local file list only contains the VAE (`_complete_pipelines/Mochi/vae/mochi_vae.safetensors`) but does not include the main `dit.safetensors` or the T5 text encoder weights required for Mochi 1.
*   **Fix**: Not in sources: specific fix for missing files, but the workflow is noted as "Not possible" with provided local files.
*   **Source**: [WORKFLOW_PLAN.md]

## Missing Base Models for AnimateDiff
*   **Symptom**: AnimateDiff workflows cannot be constructed; nodes from `ComfyUI-AnimateDiff-Evolved` are available but non-functional.
*   **Cause**: The local file list does not include a base Stable Diffusion checkpoint (SD1.5 or SDXL) or an AnimateDiff motion module.
*   **Fix**: Not in sources: specific fix, but the plan is marked "Not possible" with provided local model files.
*   **Source**: [WORKFLOW_PLAN.md]

## High VRAM Requirements for Mochi (Native Repo)
*   **Symptom**: Out-of-memory errors or inability to run on standard consumer GPUs when using the native repository.
*   **Cause**: The native repository requires approximately 60GB VRAM for single-GPU operation.
*   **Fix**: Use ComfyUI, which can optimize Mochi to run on less than 20GB VRAM, or use the `bfloat16` variant in Diffusers which requires 22GB VRAM (with a slight drop in quality).
*   **Source**: [MODEL.md], [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]

## High VRAM Requirements for Mochi (Diffusers Default)
*   **Symptom**: High memory consumption during inference.
*   **Cause**: The default Diffusers example requires 42GB VRAM to ensure the highest quality output.
*   **Fix**: Enable memory savings using `pipe.enable_model_cpu_offload()` and `pipe.enable_vae_tiling()`, or use the lower precision `bfloat16` variant.
*   **Source**: [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]

## CogVideoX Precision Limitations
*   **Symptom**: Potential inference failures or unsupported precision errors.
*   **Cause**: CogVideoX-2B does not support INT4. CogVideoX-5B recommends BF16, while CogVideoX-2B recommends FP16.
*   **Fix**: Use the recommended precision for the specific model variant (BF16 for 5B, FP16 for 2B).
*   **Source**: [PUBLIC README https://huggingface.co/zai-org/CogVideoX-5b/raw/main/README.md]

## SVD Generation Limitations
*   **Symptom**: Generated videos may lack motion, have slow camera pans, fail to render legible text, or improperly generate faces/people.
*   **Cause**: The model is a latent diffusion model trained for short clips (<= 4sec) and is not controlled through text. The autoencoding part is lossy.
*   **Fix**: Not in sources: specific technical fix, but users should be aware of these inherent limitations.
*   **Source**: [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md]

## SVD Inference Speed
*   **Symptom**: Long generation times.
*   **Cause**: SVD-XT takes ~180s on an A100 80GB card with default settings.
*   **Fix**: Apply optimizations to trade off quality/memory/speed for faster inference or lower VRAM usage.
*   **Source**: [MODEL.md], [PUBLIC README https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/raw/main/README.md]

## Mochi Content Limitations
*   **Symptom**: Minor warping and distortions in videos with extreme motion; poor performance with animated content.
*   **Cause**: Mochi 1 is optimized for photorealistic styles and is a research preview checkpoint.
*   **Fix**: Not in sources: specific fix, but users should expect these artifacts in edge cases.
*   **Source**: [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]

## CogVideoX Workflow Node Compatibility
*   **Symptom**: Workflow may fail or produce poor results if standard ComfyUI nodes are used without specific CogVideoX handling.
*   **Cause**: The provided node list does not include specific CogVideoX nodes (e.g., `CogVideoXSampler` or specific context window nodes). The plan relies on standard nodes like `KSampler` and `BasicGuider`.
*   **Fix**: Not in sources: specific fix, but the risk is noted that if CogVideoX requires specific context window handling not covered by standard nodes, the workflow may fail.
*   **Source**: [WORKFLOW_PLAN.md]

## Backend URL Mismatch
*   **Symptom**: API requests may fail or go to the wrong server.
*   **Cause**: `COMFY_BASE_URL` points at the wrong ComfyUI server.
*   **Fix**: Set `COMFY_BASE_URL` to the address of your running ComfyUI.
*   **Source**: [MODEL.md]

## Missing Local Files for Cosmos, SVD, and AnimateDiff
*   **Symptom**: Inability to verify local availability of models for Cosmos, SVD, and AnimateDiff.
*   **Cause**: Specific local model files for these models are not listed in the "LOCAL FOLDERS" or "LARGEST LOCAL FILES" sections; only CogVideoX, Mochi, and Allegro are explicitly detailed.
*   **Fix**: Not in sources: specific fix, but the absence of files is a known unknown.
*   **Source**: [MODEL.md]

## Mochi Installation Dependencies
*   **Symptom**: Installation or execution failures.
*   **Cause**: The model requires `FFMPEG` to turn outputs into videos and specific Python dependencies installed via `uv`.
*   **Fix**: Install `FFMPEG` and follow the `uv` installation steps provided in the repository.
*   **Source**: [PUBLIC README https://huggingface.co/genmo/mochi-1-preview/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
