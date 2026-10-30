# PITFALLS - 14-Krea-2

## 1. Turbo Model: Missing Timestep-Shift (`mu`) in Standard Samplers
*   **Symptom**: Suboptimal results compared to the CLI reference when using standard ComfyUI nodes for the Turbo model.
*   **Cause**: The Turbo model requires a specific timestep-shift `mu` value (recommended `1.15`), but standard ComfyUI `KSampler` nodes may not have a direct `mu` input.
*   **Fix**: Use a custom node like `Sigmax.Krea2SigmaScheduler` or `Krea2TurboReferenceSigmaSchedulerFromLatent` to properly set the timestep shift, or ensure the model loader supports Krea 2 specific settings.
*   **Source**: [WORKFLOW_PLAN.md]

## 2. Turbo Model: Incorrect Resolution Range
*   **Symptom**: Generation quality issues or out-of-distribution behavior.
*   **Cause**: The Turbo model is designed to generate images from 1k to 2k resolution. Using resolutions outside this range (e.g., below 1k or significantly above 2k) may not be supported or may degrade quality.
*   **Fix**: Set width and height between 1024 and 2048 pixels.
*   **Source**: [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md]

## 3. RAW Model: Incorrect Resolution Range
*   **Symptom**: Generation quality issues or out-of-distribution behavior.
*   **Cause**: The RAW model has been trained to generate up to 1k resolution.
*   **Fix**: Set width and height to 1024 pixels (or below).
*   **Source**: [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/krea-ai/krea-2/HEAD/README.md]

## 4. Editing Workflow: Missing Specific LoRA Weights
*   **Symptom**: `Krea2EditModelPatch` and `Krea2EditGroundedEncode` nodes may not function as intended for "Identity Edit" or "General Edit" tasks.
*   **Cause**: The specific LoRA weights (`krea2_identity_edit_v2.safetensors` and/or `krea2_general_edit_v2.safetensors`) are required for the dual-conditioning editing workflow but are not present in the local model files list.
*   **Fix**: Download and load the specific Krea 2 Identity Edit LoRAs.
*   **Source**: [WORKFLOW_PLAN.md], [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 5. Editing Workflow: Using Stock `CLIPTextEncode`
*   **Symptom**: Sharp drop in quality, especially for scene-referential instructions (e.g., "the man on the left").
*   **Cause**: With a stock `CLIPTextEncode`, the model never sees the image semantically.
*   **Fix**: Use `Krea2EditGroundedEncode` to ensure the text encoder sees the image while reading the instruction.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 6. Editing Workflow: Aspect Ratio Mismatch with Legacy Weights
*   **Symptom**: Degraded identity/preservation.
*   **Cause**: Mismatched source/output aspect ratios are out of distribution for `crop`/legacy weights.
*   **Fix**: Match the aspect ratio of the source and output images when using `crop`/legacy weights. For `fit_mode: fit` (v1.2), mismatched ARs are handled by resampling.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 7. Editing Workflow: Removal Edits on Turbo Model
*   **Symptom**: The subject is re-rendered instead of removed.
*   **Cause**: Distilled Turbo at CFG 1 usually re-renders the subject instead of removing it for "delete salient content" edits.
*   **Fix**: Use the **Raw** model at **CFG 3, ~20 steps** for removals and other "delete salient content" edits.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 8. Editing Workflow: High Resolution Generation (>2MP)
*   **Symptom**: Source content can bleed into the output or subjects duplicate.
*   **Cause**: Generating above the trained range (2MP).
*   **Fix**: Generate at ≤2MP.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 9. Editing Workflow: VRAM Spike Due to Missing `target_latent`
*   **Symptom**: The sampler streams weights from CPU on every step, causing significant slowdown.
*   **Cause**: Without `target_latent`, the node does not know the output resolution until sampling starts. The VAE encode runs on the first step when the diffusion model is already resident, causing ComfyUI to offload the sampler.
*   **Fix**: Wire `target_latent` to the same latent fed to `KSampler.latent_image` to move the encode to node-execution time.
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 10. Editing Workflow: Chaining Two-Input Edits
*   **Symptom**: Less reliable placement of two distinct people.
*   **Cause**: Adding references one at a time (chaining separate edits) is currently less reliable than simultaneous placement.
*   **Fix**: Place both references in a single pass (scene/subject A on the main inputs, subject B on the `_b` inputs).
*   **Source**: [PUBLIC README https://raw.githubusercontent.com/lbouaraba/comfyui-krea2edit/HEAD/README.md]

## 11. General: VRAM Constraints
*   **Symptom**: Out of memory errors or slow performance due to offloading.
*   **Cause**: The largest single file is the bf16 diffusion model at 26.28 GB. The text encoder is 8.27 GB. The VAE is 0.25 GB. These sizes must fit within the available memory of the shared 96 GB Blackwell card when combined with other active models and system overhead.
*   **Fix**: Monitor VRAM usage. Consider using quantized formats (e.g., `int8_convrot`, `fp8_scaled`) if available and supported, though specific VRAM requirements for the full pipeline with all node packs active simultaneously are not in sources.
*   **Source**: [MODEL.md]

## 13. General: Node Pack Compatibility
*   **Symptom**: Nodes may not load or function correctly.
*   **Cause**: It is unknown whether all 141 supporting node packs are currently installed and compatible with the PS venv.
*   **Fix**: Verify that the Python dependencies for the node packs are present in the Parametric Studio venv and that there are no conflicts with the PS torch/CUDA pins.
*   **Source**: [MODEL.md]

Not in sources: Specific VRAM requirements for running the full pipeline with all node packs active simultaneously.
Not in sources: Performance benchmarks for the Turbo vs RAW models on the specific sm_120 architecture.
Not in sources: The exact license terms beyond the "krea-2-community-license" designation.
> UNVERIFIED: name not in evidence: ), but standard ComfyUI 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 59070 chars.
