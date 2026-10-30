# PITFALLS - 27-VLM-captioning-tagging

## Florence-2-large Continued Pretraining Quality
- **Symptom**: Potential degradation in model performance or unexpected behavior due to insufficient training data for the continued pretraining phase.
- **Cause**: The `microsoft/Florence-2-large` model is a continued pretrained version where only `0.1B` samples were used for continue pretraining, which the source explicitly warns "might not be trained well".
- **Fix**: Be aware of this limitation when evaluating results; consider using the finetuned variants (`Florence-2-base-ft` or `Florence-2-large-ft`) if higher reliability on downstream tasks is required, as they are finetuned on a collection of downstream tasks.
- **Source**: [https://huggingface.co/microsoft/Florence-2-large]

## Florence-2-large OCR Output Format Change
- **Symptom**: OCR output may contain line separators that differ from previous versions or expectations, potentially breaking parsers that do not account for newlines.
- **Cause**: In the `microsoft/Florence-2-large` continued pretrained version, the OCR task has been updated with a line separator (`'\n'`).
- **Fix**: Update post-processing logic to handle `'\n'` characters in OCR outputs.
- **Source**: [https://huggingface.co/microsoft/Florence-2-large]

## Florence-2 Precision Mismatch (f32 vs fp16)
- **Symptom**: Increased VRAM usage or potential performance issues if the model is loaded with the wrong data type, or if the node does not support the required precision.
- **Cause**: The local `florence2/large-promptgen` variant is stored in `f32` precision (0.82B params), whereas the official `Florence-2` models are trained with `float16` (fp16). The `Florence2ModelLoader` node inputs are `BOOLEAN,COMBO,PEFTLORA`, and it is not stated if the `COMBO` input allows selecting `f32` vs `fp16` or if the node defaults to fp16.
- **Fix**: Verify the `Florence2ModelLoader` configuration to ensure it loads the `f32` weights correctly for `florence2/large-promptgen`. If the node forces fp16, this may cause a mismatch with the local file format.
- **Source**: [WORKFLOW_PLAN.md], [LOCAL_MODELS.tsv], [https://huggingface.co/microsoft/Florence-2-large]

## Cross-Model LoRA Incompatibility
- **Symptom**: Failure to load LoRA adapters or runtime errors when attempting to apply adapters from one model family to another.
- **Cause**: The workflow plan suggests using `VLM/microsoft__Phi-4-multimodal-instruct/vision-lora/adapter_model.safetensors` with `Qwen__Qwen2.5-VL-7B-Instruct`. The source explicitly states that using a Phi-4 LoRA with Qwen2.5-VL is "not stated in the material and may fail" and is "likely incompatible" because they are different model families.
- **Fix**: Do not apply `microsoft__Phi-4-multimodal-instruct` LoRA adapters to `Qwen__Qwen2.5-VL-7B-Instruct`. Use only LoRA adapters specifically trained for the target model architecture.
- **Source**: [WORKFLOW_PLAN.md]

## Qwen2.5-VL Sharded Model Loading
- **Symptom**: Loader failure or incomplete model loading if the loader does not handle multiple file shards.
- **Cause**: The local model files for `Qwen__Qwen2.5-VL-7B-Instruct` are split into shards (e.g., `model-00005-of-00005.safetensors`). The workflow notes that the loader "must handle the full model directory" and that other shards exist but are not listed in the provided file list.
- **Fix**: Ensure the `QwenVLModelLoader` is configured to load the entire directory containing all shard files, not just a single file.
- **Source**: [WORKFLOW_PLAN.md]

## Florence-2 Node Input Limitations
- **Symptom**: Inability to adjust critical inference parameters like `max_new_tokens` or `num_beams` via the ComfyUI node interface.
- **Cause**: The `Florence2Run` node inputs are listed as `BOOLEAN,COMBO,PEFTLORA` (for the loader) and `STRING` (for the prompt). The workflow notes that `max_new_tokens` and `num_beams` are not explicitly listed as node inputs and may have internal defaults that are not exposed.
- **Fix**: Check if the `Florence2Run` node has hidden settings or if a different node version is required to expose `max_new_tokens` and `num_beams`. If not exposed, rely on the node's internal defaults (which may differ from the README recommendations of `1024`/`4096` tokens and `3` beams).
- **Source**: [WORKFLOW_PLAN.md]

## Unknown Total Sizes for Large VLMs
- **Symptom**: Inability to accurately plan VRAM allocation for simultaneous loading of multiple large models.
- **Cause**: The exact total size of `OpenGVLab__InternVL3-14B-Instruct` and `Huihui-Step3-VL-10B-abliterated` is not stated in the sources; only the largest individual file sizes (`1.65 GB` and `1.63 GB` respectively) are provided.
- **Fix**: Manually calculate total sizes from the local file system or assume significant VRAM usage for 14B and 10B parameter models, as "14B params implies significant size".
- **Source**: [MODEL.md]

## Not in sources: Specific VRAM limits or OOM error thresholds for the 96 GB Blackwell card.
## Not in sources: Specific scheduler incompatibilities or version conflicts for `transformers` or `torch` beyond the general requirement that dependencies must not conflict with PS torch/CUDA pins.
## Not in sources: Specific quantization format incompatibilities (e.g., GGUF, AWQ) for the local models, as only fp16, bf16, and f32 are mentioned.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
