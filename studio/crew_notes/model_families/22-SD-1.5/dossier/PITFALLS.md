# PITFALLS - 22-SD-1.5

## VRAM and Precision Limits

### Symptom: High VRAM consumption during inference
**Cause:** Loading the `v1-5-pruned.safetensors` checkpoint, which contains both EMA and non-EMA weights.
**Fix:** Use `v1-5-pruned-emaonly.safetensors` for inference, as it uses less VRAM. [SOURCES.md]

### Symptom: Model fails to run on low-end GPUs
**Cause:** The model requires a GPU with at least 10GB VRAM.
**Fix:** Ensure the hardware meets the minimum 10GB VRAM requirement. [MODEL.md]

### Symptom: Potential precision issues or compatibility errors
**Cause:** Mixing full precision and FP16 components without ensuring consistency, or using the deprecated RunwayML GitHub repository.
**Fix:** Use the `v1-5-pruned-emaonly-fp16.safetensors` for FP16 workflows or ensure all Diffusers components (UNet, Text Encoder, VAE) match the desired precision (FP16 or full). Avoid the deprecated `runwayml/stable-diffusion` repository. [SOURCES.md]

## Incompatibilities and Version Issues

### Symptom: Workflow fails due to missing node definitions
**Cause:** The `IPAdapterApply` node is not present in the supported node list for this environment, despite IP-Adapter models being available locally.
**Fix:** Do not attempt to build IP-Adapter workflows using `IPAdapterApply`. The sources indicate this node is not in the pool. [WORKFLOW_PLAN.md]

### Symptom: Workflow fails due to unknown node ID
**Cause:** The node `ADE_PerBlock...` is flagged as not a known node ID or local file.
**Fix:** Verify node IDs against the supported list; `ADE_PerBlock...` is not a valid node in this context. [WORKFLOW_PLAN.md]

### Symptom: Incompatibility with specific software versions
**Cause:** Uncertainty regarding the compatibility of all node packs with the specific version of ComfyUI (v0.43.0) and torch (2.16.0.dev20261027+cu134) in the Parametric Studio environment.
**Fix:** Not in sources: Specific compatibility verification steps for ComfyUI v0.43.0 and torch 2.16.0.dev20261027+cu134. [MODEL.md]

### Symptom: Model files may not be compatible with SD 1.5 architecture
**Cause:** It is unknown whether all model files in the `checkpoints` folder are compatible with the SD 1.5 architecture.
**Fix:** Not in sources: Method to verify compatibility of all files in the `checkpoints` folder. [MODEL.md]

## Model Limitations and Quality Issues

### Symptom: Generated images do not render legible text
**Cause:** The model cannot render legible text natively.
**Fix:** Use the `Anytext` node pack (`zmwv823__ComfyUI_Anytext`) to render legible text in images. [MODEL.md]

### Symptom: Poor generation of faces and people
**Cause:** Faces and people in general may not be generated properly by the base model.
**Fix:** Use face restoration tools like GFPGAN or CodeFormer, or specific IP-Adapters like `ip-adapter-faceid_sd15.bin` if a compatible node exists (though `IPAdapterApply` is missing, other face-related nodes like `FaceSEGSRouter` are listed). [MODEL.md]

### Symptom: Images lack photorealism or fail complex compositional prompts
**Cause:** The model does not achieve perfect photorealism and does not perform well on difficult compositional tasks (e.g., "A red cube on top of a blue sphere").
**Fix:** Not in sources: Specific prompt engineering techniques to mitigate compositional failures. [MODEL.md]

### Symptom: Bias in generated content
**Cause:** The model was trained on LAION-5B, which contains adult material and is biased towards English and Western cultures.
**Fix:** Use the Safety Checker (`diffusers/safety_checker/model.safetensors`) to filter outputs, though it is unknown if it is enabled by default. [MODEL.md]

### Symptom: Memorization of training data
**Cause:** No additional measures were used to deduplicate the dataset, leading to memorization of duplicated images.
**Fix:** Search training data at `https://rom1504.github.io/clip-retrieval/` to detect memorized images. [MODEL.md]

## Configuration and Usage Errors

### Symptom: Resolution errors or artifacts
**Cause:** Image dimensions are not a multiple of 8.
**Fix:** Ensure generated image dimensions are a multiple of 8. [MODEL.md]

### Symptom: Suboptimal sampling results
**Cause:** Using incorrect guidance scale or sampling steps.
**Fix:** Adjust `Guidance Scale` and `Sampling Steps`. The reference script uses a guidance scale of `7.5` and 50 PLMS steps. [SOURCES.md]

### Symptom: Inability to use IP-Adapter models
**Cause:** The specific CLIP Vision model file required for IP-Adapter is not listed in the local model files, and the `IPAdapterApply` node is missing.
**Fix:** Not in sources: How to obtain the missing CLIP Vision model or alternative nodes for IP-Adapter application. [WORKFLOW_PLAN.md]

### Symptom: Unclear usage of IP-Adapter models
**Cause:** Specific usage instructions for the IP-Adapter models are not provided in the sources.
**Fix:** Not in sources: Specific usage instructions for IP-Adapter models. [MODEL.md]

### Symptom: Safety checker status unknown
**Cause:** It is unknown whether the safety checker is enabled by default in the local setup.
**Fix:** Not in sources: How to verify or enable the safety checker by default. [MODEL.md]

## Hardware and Local Setup

### Symptom: Insufficient local storage or VRAM for specific files
**Cause:** The largest file, `DreamShaper_8_pruned.safetensors`, is 2.13 GB, and the total SD15 folder size is 19 GB.
**Fix:** Ensure sufficient disk space (19 GB) and VRAM (at least 10 GB) are available. [MODEL.md]

### Symptom: Performance benchmarks unknown
**Cause:** Specific performance benchmarks for SD 1.5 on the local hardware are not provided.
**Fix:** Not in sources: Performance benchmarks for SD 1.5 on local hardware. [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
