# PITFALLS - 10-Flux.2-Klein

## VRAM and Hardware Limits

### Symptom: Out of memory or failure to run FLUX.2 [dev] on consumer hardware
**Cause:** The `FLUX.2 [dev]` model is a 32B parameter model that requires significant VRAM (H100-equivalent) for full precision.
**Fix:** Use quantized versions (e.g., `nvfp4`, `fp8`) or run on H100-equivalent hardware. For consumer GPUs like RTX 4090, use quantized versions with a remote text encoder.
**Source:** [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux2/HEAD/README.md]

### Symptom: VRAM usage higher than expected for Klein 4B
**Cause:** The `FLUX.2 [klein] 4B` model fits in ~8GB VRAM according to the local model documentation, but the official Hugging Face README states it fits in ~13GB VRAM.
**Fix:** Verify the specific variant and precision being used. The local documentation suggests ~8GB, while the public README suggests ~13GB. Ensure sufficient VRAM is allocated based on the specific implementation.
**Source:** [MODEL.md], [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md]

### Symptom: Inference slower than expected on consumer GPUs
**Cause:** Using the Base models (4B or 9B) which require 50-step inference for maximum flexibility and fine-tuning, rather than the distilled models which use 4-step inference.
**Fix:** Use the distilled models (`FLUX.2 [klein] 4B`, `9B`, or `9B KV`) for production apps and real-time generation to achieve sub-second inference.
**Source:** [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux2/HEAD/README.md]

## Precision and Quantization

### Symptom: Quality degradation or unexpected behavior with quantized models
**Cause:** Quantized models (e.g., `nvfp4`, `fp8`) may have different quality characteristics compared to full precision (`bf16`).
**Fix:** No specific benchmarks are provided in the material to quantify the difference. Test and compare outputs between quantized and full-precision models to determine acceptable quality levels.
**Source:** [WORKFLOW_PLAN.md]

### Symptom: Incompatibility with specific quantization formats
**Cause:** The local installation includes `bf16`, `fp8`, and `nvfp4` variants. The `Comfy-Org/Flux-2-Klein-4B` repackaging specifies `qwen_3_4b.safetensors` and `qwen_3_4b_fp4_flux2.safetensors` as text encoders, but the local workflow plans use `qwen_3_4b.safetensors`.
**Fix:** Ensure the text encoder matches the expected format for the specific pipeline. The `Comfy-Org` README lists `qwen_3_4b_fp4_flux2.safetensors` as an option, but the local workflow uses `qwen_3_4b.safetensors`. Verify compatibility with the specific node pack being used.
**Source:** [MODEL.md], [WORKFLOW_PLAN.md], [PUBLIC README https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/raw/main/README.md]

## Incompatibilities and Version Issues

### Symptom: Confusion between FLUX.2 and FLUX.3-Klein
**Cause:** The local installation includes assets for both `FLUX.2 [dev]` and `FLUX.3-Klein`. The material does not explicitly define "FLUX.3" as a distinct public release separate from the FLUX.2 Klein family, but the local files indicate a specific "Klein" implementation present on the box.
**Fix:** Clarify the relationship between `FLUX.3-Klein` and `FLUX.2 [klein]`. The local files suggest a close variant, but the exact relationship is not stated. Verify which model files are intended for use in specific workflows.
**Source:** [MODEL.md]

### Symptom: ControlNet compatibility issues
**Cause:** The `FLUX.2-dev-Fun-Controlnet-Union.safetensors` ControlNet is listed under the `Flux.2` folder but is being applied to the `Flux.3-Klein` diffusion model in the workflow plan. The material does not explicitly state compatibility between `Flux.2` ControlNets and `Flux.3-Klein` models.
**Fix:** Verify compatibility between `Flux.2` ControlNets and `Flux.3-Klein` models. Test the workflow to ensure the ControlNet functions correctly with the specific diffusion model.
**Source:** [WORKFLOW_PLAN.md]

### Symptom: Backend connection failures
**Cause:** `COMFY_BASE_URL` points at the wrong ComfyUI server.
**Fix:** Set `COMFY_BASE_URL` to the address of your running ComfyUI.
**Source:** [MODEL.md]

### Symptom: Dependency conflicts
**Cause:** The PS venv uses Python 3.12.3, torch 2.16.0.dev20261027+cu134, and CUDA/nvcc 13.4. Node packs must have their Python dependencies installed in this venv and must not conflict with these torch/CUDA pins.
**Fix:** Ensure all node pack dependencies are compatible with the specified Python, torch, and CUDA versions. Check for conflicts before installing new packs.
**Source:** [MODEL.md]

## Model-Specific Limitations

### Symptom: Inaccurate or distorted text rendering
**Cause:** The model may output text that is inaccurate or subject to distortion.
**Fix:** Do not rely on the model for factual information or accurate text rendering. Use post-processing or alternative methods for critical text generation.
**Source:** [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md]

### Symptom: Failure to generate output matching prompts
**Cause:** The model may fail to generate output that matches the prompts, and prompt following is heavily influenced by the prompting style.
**Fix:** Experiment with different prompting styles to improve prompt adherence. Use prompt upsampling for `FLUX.2 [dev]` to improve quality.
**Source:** [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md], [MODEL.md]

## Not in sources:
- Specific performance benchmarks (Elo scores, latency numbers) are referenced in images but the numerical values are not provided in the text.
- The exact role of the `pid_*.pth` files in `_complete_pipelines/Flux.2/extra/` is not stated in the provided material.
- The status of the `ComfyUI-FLUX2-JSON.disabled` pack (why it is disabled) is not stated.
- Specific settings (steps, cfg) for the node combination in the workflow plans are not stated in the provided material, so standard defaults apply.
- The `Flux2FunControlApply` node has a `FLOAT` input for strength, which is not specified in the material, so a default value should be used.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 58888 chars.
