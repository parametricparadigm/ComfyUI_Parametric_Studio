# PITFALLS - 11-HiDream

## PyTorch Version Incompatibility (O1 Series)
- **Symptom**: Inference or pipeline failures when using PyTorch 2.9.x.
- **Cause**: A specific issue in PyTorch 2.9.x (linked to `https://github.com/QwenLM/Qwen3-VL/issues/1811`).
- **Fix**: Do not use PyTorch 2.9.x. Use a different version.
- **Source**: [https://huggingface.co/HiDream-ai/HiDream-O1-Image]

## Missing External Dependencies (I1 Series)
- **Symptom**: Inference script fails to download `meta-llama/Meta-Llama-3.1-8B-Instruct` model files due to network issues or license restrictions.
- **Cause**: The inference script attempts to automatically download Llama model files, which requires agreeing to the Llama license and logging in via `huggingface-cli login`.
- **Fix**: Download `meta-llama/Meta-Llama-3.1-8B-Instruct` files ahead of time and place them in the appropriate cache directory.
- **Source**: [https://huggingface.co/HiDream-ai/HiDream-I1-Full]

## Missing Flash Attention (I1 Series)
- **Symptom**: Inference fails or performance is suboptimal.
- **Cause**: Flash Attention is not installed.
- **Fix**: Install Flash Attention (`pip install -U flash-attn --no-build-isolation`).
- **Source**: [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md]

## Incorrect CUDA Version (I1 Series)
- **Symptom**: Installation or runtime issues.
- **Cause**: Using a CUDA version other than the recommended one for manual installation.
- **Fix**: Use CUDA version 12.4.
- **Source**: [https://huggingface.co/HiDream-ai/HiDream-I1-Full]

## Wrong Guidance Scale for Distilled Models (I1 Series)
- **Symptom**: Poor generation quality or unexpected behavior when using distilled models.
- **Cause**: Using the guidance scale intended for the full model (5.0) with distilled variants.
- **Fix**: Use `guidance_scale=0.0` for `HiDream-I1-Dev` and `HiDream-I1-Fast`.
- **Source**: [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md]

## Wrong Inference Steps for Distilled Models (I1 Series)
- **Symptom**: Inefficient inference or potential quality issues if steps are mismatched to the model variant.
- **Cause**: Using the step count for the full model (50) with distilled variants.
- **Fix**: Use 28 steps for `HiDream-I1-Dev` and 16 steps for `HiDream-I1-Fast`.
- **Source**: [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md]

## Editing Task Model Selection (O1 Series)
- **Symptom**: Suboptimal editing results.
- **Cause**: Using the Dev variant for editing tasks.
- **Fix**: Use the **full** model for editing tasks.
- **Source**: [https://huggingface.co/HiDream-ai/HiDream-O1-Image]

## VRAM Management for Large Models
- **Symptom**: Out-of-memory errors or slow performance.
- **Cause**: Loading multiple large models simultaneously (e.g., `hidream_e1_1_bf16.safetensors` is 34.21 GB).
- **Fix**: Careful memory management is required when loading multiple large models, even on a 96 GB VRAM card.
- **Source**: [MODEL.md]

## Missing Supporting Files for I1 Series
- **Symptom**: Pipeline fails to load required components.
- **Cause**: The HiDream-I1 series requires external VAEs (`FLUX.1 [schnell]`) and text encoders (`t5-v1_1-xxl`, `Llama-3.1-8B-Instruct`), which are not listed in the local HiDream folder scan.
- **Fix**: Ensure these specific supporting files are present in the model directory.
- **Source**: [MODEL.md]

## Unverified Torch Version Compatibility
- **Symptom**: Potential runtime errors or instability.
- **Cause**: It is not stated if the HiDream models have been tested with the specific `torch 2.16.0.dev20261027+cu134` version in the Parametric Studio venv.
- **Fix**: Not in sources: specific fix for untested torch versions.
- **Source**: [MODEL.md]

## Unknown Python Dependencies
- **Symptom**: Node packs fail to load or function.
- **Cause**: The specific Python dependencies required for the HiDream node packs are not listed in the material.
- **Fix**: Not in sources: specific dependency list.
- **Source**: [MODEL.md]

## Unclear API Graph Structure
- **Symptom**: Difficulty integrating HiDream nodes into API-format graphs.
- **Cause**: The exact API graph structure for HiDream nodes is not provided in the material.
- **Fix**: Not in sources: specific API graph structure.
- **Source**: [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
