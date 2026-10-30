# PITFALLS - 12-HunyuanVideo-FramePack

## Vision Encoder Mismatch in Image-to-Video Workflows

*   **Symptom:** The `HunyuanVideoVisionLoader` node may fail to load the correct model or produce incorrect conditioning because the local file does not match the expected architecture.
*   **Cause:** The local environment contains `clip-vit-large-patch14.safetensors` (located in `_complete_pipelines/HY-Motion/clip_vision/text_encoders/`), but the official ComfyUI documentation for HunyuanVideo-1.5 specifies `sigclip_vision_patch14_384.safetensors` for the `clip_vision` folder. The workflow plan notes that the local file "may not be the exact match for the node's expected input."
*   **Fix:** Replace the local `clip-vit-large-patch14.safetensors` with `sigclip_vision_patch14_384.safetensors` and place it in the `ComfyUI/models/clip_vision/` directory as specified by the Comfy-Org repository.
*   **Source:** [WORKFLOW_PLAN.md], [PUBLIC README https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/raw/main/README.md]

## Text Encoder Discrepancy (Qwen vs. LLaVA)

*   **Symptom:** Potential confusion or failure in text encoding if the wrong text encoder is loaded, as the local file naming and description do not align with the official ComfyUI file list.
*   **Cause:** The local model `qwen2.5-vl-7b-bf16.safetensors` is described in `LOCAL_MODELS.tsv` as "HunyuanVideo LLaVA Llama3 text encoder, 8B params, fp8," which contradicts the filename (Qwen 2.5 VL 7B) and the precision (BF16 vs FP8). The Comfy-Org README lists `qwen_2.5_vl_7b.safetensors` and `qwen_2.5_vl_7b_fp8_scaled.safetensors` as valid text encoders, but does not list an LLaVA Llama3 encoder for HunyuanVideo-1.5.
*   **Fix:** Verify the actual architecture of the local `qwen2.5-vl-7b-bf16.safetensors` file. If it is indeed a Qwen 2.5 VL 7B model, ensure it is placed in `ComfyUI/models/text_encoders/`. If the workflow requires the specific LLaVA Llama3 encoder mentioned in the local metadata, confirm if that specific file is required for the 1.5 model or if it belongs to the original HunyuanVideo, as the Comfy-Org 1.5 list does not include it.
*   **Source:** [WORKFLOW_PLAN.md], [LOCAL_MODELS.tsv], [PUBLIC README https://huggingface.co/Comfy-Org/Hunyuan-Video-1.5/raw/main/README.md]

## Missing Super-Resolution Input Parameter

*   **Symptom:** The `HunyuanVideo15SuperResolution` node may fail to execute or produce errors due to an undefined input.
*   **Cause:** The workflow plan for Super Resolution (720p to 1080p) notes that the node requires a `FLOAT` input, but "The `FLOAT` input is not stated in the material."
*   **Fix:** Not in sources: Specific value or source for the `FLOAT` input required by `HunyuanVideo15SuperResolution`.
*   **Source:** [WORKFLOW_PLAN.md]

## Step-Distilled Model Activation

*   **Symptom:** The model may run at standard speed (e.g., 20+ steps) instead of the accelerated 4, 8, or 12 steps, or may fail if the wrong model file is used without the correct flag.
*   **Cause:** Using the step-distilled model files (e.g., `hunyuanvideo1.5_480p_i2v_step_distilled_fp16.safetensors`) requires specific activation in the source code. The README states: "To enable the step-distilled model, run `generate.py` with the `--enable_step_distill` parameter."
*   **Fix:** Ensure the `--enable_step_distill` parameter is passed when running `generate.py` if using step-distilled weights.
*   **Source:** [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md]

## Optimizer Requirement for Fine-Tuning

*   **Symptom:** Fine-tuning or LoRA training may produce suboptimal results or fail to converge if the wrong optimizer is used.
*   **Cause:** The HunyuanVideo-1.5 model was trained using the Muon optimizer. The README explicitly warns: "If you would like to continue training our model or fine-tune it with LoRA, please use the Muon optimizer."
*   **Fix:** Use the Muon optimizer for any fine-tuning or LoRA training tasks on HunyuanVideo-1.5.
*   **Source:** [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md]

## VRAM and Hardware Constraints

*   **Symptom:** Out-of-memory errors or slow inference on consumer-grade hardware.
*   **Cause:** While HunyuanVideo-1.5 is designed for consumer GPUs, the original HunyuanVideo (13B+) is significantly larger. The local setup includes a 25.64 GB `hunyuan_video_t2v_720p_bf16.safetensors` file. The hardware is a single 96 GB Blackwell GPU.
*   **Fix:** Use FP8 quantized weights (e.g., `hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.safetensors`) or the lighter HunyuanVideo-1.5 models (8.3B parameters) to reduce VRAM usage. For the original 13B model, consider FP8 weights or multi-GPU parallel inference via xDiT if available.
*   **Source:** [MODEL.md], [PUBLIC README https://huggingface.co/tencent/HunyuanVideo/raw/main/README.md]

## Not in sources:
*   Specific VRAM usage per inference step for the 13B model on the 96 GB card.
*   Specific configuration parameters for the "FramePack" technique in the ComfyUI graph format.
*   Whether the `HY-Motion` folder contains additional specific motion control models beyond the CLIP vision encoder listed.
*   Compatibility of `clip-vit-large-patch14.safetensors` with `HunyuanVideoVisionLoader` (only noted as a potential mismatch).
*   Specific settings (steps, CFG, etc.) for the provided workflow configurations.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
