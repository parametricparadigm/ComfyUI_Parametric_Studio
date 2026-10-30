# PITFALLS - 04-Chroma

## Version Confusion: Chroma1-HD vs. Old Chroma-v.50
*   **Symptom:** Users may expect the behavior or weights of the older "Chroma-v.50" model when using the current `Chroma1-HD` checkpoint.
*   **Cause:** The current `Chroma1-HD` model is not the old `Chroma-v.50`; it has been retrained from `v.48`.
*   **Fix:** Ensure workflows and expectations are aligned with the `Chroma1-HD` architecture (8.9B parameters, based on `FLUX.1-schnell`) rather than legacy versions.
*   **Source:** [https://huggingface.co/lodestones/Chroma1-HD/raw/main/README.md]

## Missing Local Model Files
*   **Symptom:** The specialist agent or local environment reports 0 model files and 0 GB of storage used for the Chroma family, preventing local inference or finetuning.
*   **Cause:** No local model files for the Chroma family (diffusion models, T5 XXL encoder, FLUX VAE) are currently present in the local model directories.
*   **Fix:** Download and place the required model files (`Chroma1-HD.safetensors`, `t5xxl_fp16.safetensors`, `ae.safetensors`) into the appropriate subfolders (e.g., `diffusion_models`, `clip`, `vae`) within the PS model structure.
*   **Source:** [MODEL.md]

## Gemlite Quantization Not Supported in Standard ComfyUI Nodes
*   **Symptom:** Attempts to use gemlite quantization (`A8W8_int8_dynamic`, `A8W8_fp8_dynamic`, `A16W4_MXFP`) within a standard ComfyUI workflow fail or are not representable.
*   **Cause:** The gemlite quantization process described in the README involves patching linear layers via external Python code. This is not directly supported by the standard ComfyUI nodes listed in the available node packs.
*   **Fix:** Implement the gemlite patching via external Python code or use a custom node not listed in the standard packs. Alternatively, use standard ComfyUI nodes without gemlite quantization.
*   **Source:** [WORKFLOW_PLAN.md]

## Unknown Radiance Options Configuration
*   **Symptom:** When using the `ChromaRadianceOptions` node, the specific impact on output image characteristics is unclear, and correct values for BOOLEAN, FLOAT, and INT inputs are not documented.
*   **Cause:** The specific settings for `ChromaRadianceOptions` are not stated in the README or provided material.
*   **Fix:** Not in sources: Specific recommended values or documentation for `ChromaRadianceOptions` inputs.
*   **Source:** [WORKFLOW_PLAN.md]

## VRAM Requirements Not Explicitly Stated
*   **Symptom:** Uncertainty regarding whether the available hardware (e.g., 96 GB Blackwell card) is sufficient for full-precision or quantized inference.
*   **Cause:** The material states that the 8.9B parameter model requires significant VRAM, but specific memory usage per instance is not stated.
*   **Fix:** Not in sources: Specific VRAM usage figures per instance.
*   **Source:** [MODEL.md]

## Technical Report Unavailable
*   **Symptom:** Lack of detailed information regarding architectural modifications and the training process.
*   **Cause:** The comprehensive technical paper detailing these aspects is noted as "forthcoming" and is not available in the current material.
*   **Fix:** Not in sources: The technical report.
*   **Source:** [MODEL.md]

## Chroma1-Flash Configuration Undetailed
*   **Symptom:** Users seeking to use the "fast CFG 'baked' version" (`Chroma1-Flash`) lack technical details on its configuration.
*   **Cause:** The specific configuration of the "Chroma1-Flash" variant is not detailed in the material.
*   **Fix:** Not in sources: Technical details for `Chroma1-Flash`.
*   **Source:** [MODEL.md]

## GGUF File Sizes Unknown
*   **Symptom:** Inability to plan storage or download times accurately for specific GGUF quantization levels (BF16, Q8_0, etc.).
*   **Cause:** The exact file sizes of the Chroma model variants are not stated in the material.
*   **Fix:** Not in sources: Exact file sizes for GGUF variants.
*   **Source:** [MODEL.md]

## Performance Benchmarks Missing
*   **Symptom:** Inability to predict inference time per image on local hardware.
*   **Cause:** Specific performance benchmarks for Chroma on the local hardware are not stated in the material.
*   **Fix:** Not in sources: Inference time benchmarks.
*   **Source:** [MODEL.md]

## GGUF Quantization Levels Not Fully Listed in Primary Repo
*   **Symptom:** Users looking for `Q8_M` or `Q4_K_S` quantizations in the `silveroxides/Chroma-GGUF` repository may not find them.
*   **Cause:** The `silveroxides/Chroma-GGUF` repository lists BF16, Q8_0, Q6_K, Q5_1, Q5_0, Q5_K_S, Q4_1, Q4_K_M, Q4_0, and Q3_K_L. `Q8_M` and `Q4_K_S` are explicitly noted to be found at `Clybius/Chroma-GGUF`.
*   **Fix:** Use the `Clybius/Chroma-GGUF` repository for `Q8_M` and `Q4_K_S` quantizations.
*   **Source:** [https://huggingface.co/silveroxides/Chroma-GGUF/raw/main/README.md]

## Distillation Layers Not Quantized in GGUF
*   **Symptom:** Potential performance or memory expectations mismatch when using GGUF models, assuming all layers are quantized.
*   **Cause:** The GGUF quantization process (using modified llama.cpp & city96's ComfyUI-GGUF/tools) does not quantize distillation layers.
*   **Fix:** Account for the fact that distillation layers remain unquantized when estimating memory usage or performance.
*   **Source:** [https://huggingface.co/Clybius/Chroma-GGUF/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 49716 chars.
