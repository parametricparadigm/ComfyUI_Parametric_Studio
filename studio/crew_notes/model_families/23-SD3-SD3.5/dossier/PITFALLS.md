# PITFALLS - 23-SD3-SD3.5

## Missing Text Encoders
- **Symptom**: The workflow fails to execute or produces errors because required conditioning embeddings cannot be generated. The local file list only contains `clip_g.safetensors`, but the architecture requires three distinct text encoders. [MODEL.md]
- **Cause**: The reference implementation and architecture require OpenAI CLIP-L/14, OpenCLIP bigG, and Google T5-XXL. While `clip_g.safetensors` is present locally, the specific files for CLIP-L and T5-XXL are not explicitly confirmed in the local file inventory, despite being required by the model. [MODEL.md] [WORKFLOW_PLAN.md]
- **Fix**: Download the missing text encoders (`clip_l.safetensors` and `t5xxl_fp16.safetensors`) from the HuggingFace repository `stabilityai/stable-diffusion-3.5-large` into the `text_encoders` directory. [SOURCES.md]

## VRAM Pressure with Large Model and ControlNets
- **Symptom**: Potential out-of-memory errors or performance degradation when loading the SD3.5 Large model alongside multiple auxiliary models. [MODEL.md]
- **Cause**: The SD3.5 Large diffusion model is 16.46 GB, and each SD3.5 Large ControlNet is 8.65 GB. Simultaneous loading of the Large model and multiple ControlNets/IP-Adapters may exceed safe memory thresholds on the shared 96 GB GPU, requiring careful memory management. [MODEL.md]
- **Fix**: Not in sources: Specific memory management strategies or offloading techniques for this specific combination are not detailed in the provided evidence.

## Incomplete Local Inventory for Turbo Variant
- **Symptom**: The SD3.5 Large Turbo variant is referenced in documentation but cannot be found in the local file inventory. [MODEL.md]
- **Cause**: The local environment inventory lists `sd3.5_large.safetensors`, `sd3.5_medium.safetensors`, and `sd3_medium.safetensors`, but does not list a file for the SD3.5 Large Turbo variant, even though the reference implementation supports it. [MODEL.md] [SOURCES.md]
- **Fix**: Download `sd3.5_large_turbo.safetensors` from the HuggingFace repository `stabilityai/stable-diffusion-3.5-large-turbo` if the Turbo variant is required. [SOURCES.md]

## Backend URL Misconfiguration
- **Symptom**: The contest studio backend fails to communicate with the correct ComfyUI instance. [MODEL.md]
- **Cause**: The backend's `COMFY_BASE_URL` currently points to an old instance instead of the Parametric Studio (PS) server on port 8200. [MODEL.md]
- **Fix**: Repoint `COMFY_BASE_URL` to the PS server on port 8200. [MODEL.md]

## Missing CLIP Vision Model for IP-Adapter
- **Symptom**: The IP-Adapter workflow fails because the `CLIPVisionLoader` node cannot find the required model file. [WORKFLOW_PLAN.md]
- **Cause**: The local file list does not state the specific file for the CLIP Vision model, which is required for the `CLIPVisionLoader` node in the IP-Adapter pipeline. [WORKFLOW_PLAN.md]
- **Fix**: Not in sources: The specific filename or download source for the required CLIP Vision model is not provided in the evidence.

## Undefined Sampling Parameters
- **Symptom**: Workflows may fail or produce suboptimal results if critical sampling parameters are left unset or guessed incorrectly. [WORKFLOW_PLAN.md]
- **Cause**: The reference documentation and local plans do not state specific values for guidance scale, steps, sampler, scheduler, or resolution for the SD3.5 models, marking them as "not stated in README" in the workflow plans. [WORKFLOW_PLAN.md]
- **Fix**: Not in sources: Specific recommended values for guidance scale, steps, sampler, or scheduler for SD3/SD3.5 are not provided in the evidence, though the reference implementation mentions default steps of 20 or 50 and an example of 100. [MODEL.md]

## ControlNet Preprocessing Requirements
- **Symptom**: ControlNet conditioning may not work as expected if input images are not preprocessed correctly. [MODEL.md]
- **Cause**: Specific preprocessing is required for each ControlNet type (blur, canny, depth), but the exact preprocessing steps are not detailed in the local model documentation. [MODEL.md]
- **Fix**: Review the model card for `stabilityai/stable-diffusion-3.5-controlnets` for details on preprocessing for each ControlNet type. [SOURCES.md]

## Precision Mismatch in IP-Adapters
- **Symptom**: Potential compatibility issues or performance inconsistencies when loading IP-Adapter models. [MODEL.md]
- **Cause**: The IP-Adapter models (`ip-adapter_sd35_large.bin` and `ip-adapter-instruct-sd3.bin`) are stored in mixed precision, whereas the ControlNets are in F32 and the text encoder `clip_g.safetensors` is in F16. [MODEL.md] [LOCAL_MODELS.tsv]
- **Fix**: Not in sources: Specific instructions on handling mixed precision for these IP-Adapter files are not provided in the evidence.

## Missing Dependencies for Model-Bound Packs
- **Symptom**: Node packs specific to this model family may fail to load or function. [MODEL.md]
- **Cause**: The specific Python dependencies required for the "model-bound only" packs (`ComfyUI-FluxTrainer`, `ComfyUI-SD3-Powerlab`, `ComfyUI_SD3_Flowedit`) are not stated in the documentation. [MODEL.md]
- **Fix**: Not in sources: The specific Python dependencies for these packs are not listed in the evidence.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 51855 chars.
