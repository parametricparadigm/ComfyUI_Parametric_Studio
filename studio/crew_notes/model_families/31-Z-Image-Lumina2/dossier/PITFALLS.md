# PITFALLS - 31-Z-Image-Lumina2

## Missing Z-Image Text Encoder
- **Symptom**: The workflow fails to execute or the `ZImageLoader` / `ZImageTextEncoderSimple` nodes cannot find the required CLIP/text encoder file.
- **Cause**: The local model file list for the Z-Image pipeline does not include the text encoder (e.g., `qwen_3_4b.safetensors`), which is required by the ComfyUI workflow structure.
- **Fix**: Ensure the text encoder file listed in the Comfy-Org/Z-Image-Turbo README (such as `qwen_3_4b.safetensors`) is present in the `text_encoders` folder.
- **Source**: [WORKFLOW_PLAN.md]

## Node Pack Dependency Conflicts
- **Symptom**: Node packs required for Z-Image or Lumina-2 fail to load or function correctly in the Parametric Studio environment.
- **Cause**: The Python dependencies for the 177 supporting node packs are not installed in the PS venv, or they conflict with the pinned `torch` and `CUDA` versions.
- **Fix**: Install the specific Python dependencies for the required node packs in the PS venv, ensuring they do not conflict with the pinned `torch 2.16.0.dev20261027+cu134` and `CUDA/nvcc 13.4` versions.
- **Source**: [MODEL.md]

## Lumina-2 VAE File Location Ambiguity
- **Symptom**: Potential confusion or failure when loading the VAE for the Lumina-2 pipeline.
- **Cause**: The Lumina-2 README lists `ae.safetensors` in its VAE folder, but in the local file list, `ae.safetensors` is located under the Z-Image folder (`_complete_pipelines/Z-Image/vae/split_files/vae/ae.safetensors`).
- **Fix**: Verify that the `ae.safetensors` file from the Z-Image folder is the correct shared VAE intended for use with Lumina-2, as assumed in the workflow plan.
- **Source**: [WORKFLOW_PLAN.md]

## Diffusers Version Requirement
- **Symptom**: Z-Image support is missing or errors occur when using the `diffusers` library.
- **Cause**: The Z-Image support was added via pull requests that are only available in the latest official `diffusers` release, which may not be included in standard pip installations.
- **Fix**: Install `diffusers` from source using `pip install git+https://github.com/huggingface/diffusers`.
- **Source**: [PUBLIC README https://huggingface.co/Tongyi-MAI/Z-Image-Turbo/raw/main/README.md]

## Not in sources: Specific step and CFG settings for Lumina-Image-2
## Not in sources: Exact file sizes for Z-Image-Omni-Base and Z-Image-Edit
## Not in sources: Specific Python dependencies required for the 177 supporting node packs
## Not in sources: Specific behavior and required settings for the `Sigmax.Lumina2SigmaScheduler` node
## Not in sources: Specific inputs for regional prompts and masks required by `RPRegionalDetailerZImage`

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
