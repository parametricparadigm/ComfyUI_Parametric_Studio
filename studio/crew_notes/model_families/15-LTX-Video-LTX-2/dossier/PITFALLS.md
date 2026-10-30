# PITFALLS - 15-LTX-Video-LTX-2

## Missing Transformer Model in Local Environment
- **Symptom**: The `LTXVBaseSampler` node cannot function, and video generation workflows fail to execute because the main diffusion transformer model is absent from the local file system.
- **Cause**: The local installation under `_complete_pipelines/LTX-2.5` only contains the text encoder (`text_encoder_gemma4-12b.safetensors`) and VAEs (`video_vae_conv.safetensors`, `audio_vae.safetensors`). The required transformer file `ltx-2.5-22b-distilled-transformer-bf16.safetensors` is listed in the README download instructions but is not present in the local model folders.
- **Fix**: Download the missing transformer model using the Hugging Face CLI or manual download as specified in the LTX-2 quick start guide.
- **Source**: [WORKFLOW_PLAN.md], [MODEL.md]

## VRAM Exhaustion During VAE Decoding
- **Symptom**: Out-of-Memory (OOM) errors occur during the VAE decoding stage of the pipeline.
- **Cause**: The VAE decoding process requires significant memory, particularly when handling high-resolution or long-duration latents without optimization.
- **Fix**: Enable VAE tiling by calling `pipe.vae.enable_tiling()` in the Diffusers pipeline configuration.
- **Source**: [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

## GPU Memory Constraints for Full Model Set
- **Symptom**: The full LTX-2.5 model set (approximately 66 GiB) may not fit on a single GPU if all components are loaded simultaneously, leading to memory pressure or failure.
- **Cause**: The total size of the full download set exceeds the available VRAM on standard single-GPU setups (e.g., the local 96 GB Blackwell card) when combined with other system overheads.
- **Fix**: Use quantization and offloading flags such as `--quantization fp8-cast` and `--offload {cpu, disk}` to manage GPU memory constraints.
- **Source**: [MODEL.md]

## Incorrect Resolution or Frame Count Dimensions
- **Symptom**: Generation fails or produces artifacts due to invalid input dimensions.
- **Cause**: Width and height settings are not divisible by 32, or the frame count is not divisible by 8 + 1.
- **Fix**: Ensure width and height are divisible by 32 and frame count is divisible by 8 + 1. If not, pad the input with -1 and then crop to the desired resolution and number of frames.
- **Source**: [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

## Platform-Specific Backend Limitations for `natten`
- **Symptom**: The `natten` extra, which provides the fastest backend for the diffusion video VAE, is not available or skipped on Windows and macOS.
- **Cause**: The `natten` library is Linux + CUDA only. On unsupported platforms, the installation is skipped automatically.
- **Fix**: On Windows and macOS, decoding falls back to a Triton or eager implementation. No specific fix is required as the fallback is automatic, but performance may be lower than on Linux + CUDA.
- **Source**: [SOURCES.md]

## Audio Quality Degradation Without Speech
- **Symptom**: Generated audio may be of lower quality when the prompt does not include speech.
- **Cause**: The model's audio generation capabilities are optimized for scenarios involving speech; non-speech audio generation is a known limitation.
- **Fix**: Not explicitly provided in sources; users should be aware of this limitation when generating ambient or musical audio without dialogue.
- **Source**: [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

## Scheduler Configuration for Distilled Stage 2
- **Symptom**: Incorrect sampling behavior or quality issues when using the distilled LoRA for Stage 2 inference.
- **Cause**: The default scheduler settings may not align with the specific sigma values required for the distilled model.
- **Fix**: Change the scheduler to `FlowMatchEulerDiscreteScheduler` with `use_dynamic_shifting=False` and `shift_terminal=None`, and use `STAGE_2_DISTILLED_SIGMA_VALUES` for the `sigmas` parameter.
- **Source**: [PUBLIC README https://huggingface.co/Lightricks/LTX-2/raw/main/README.md]

## Not in sources: Specific error messages or crash logs for VRAM failures.
## Not in sources: Compatibility issues between specific ComfyUI node versions and LTX-2.5.
## Not in sources: Detailed troubleshooting for audio-video synchronization drift.
## Not in sources: Specific VRAM requirements for the `ltx-2-19b-dev` model in bf16 vs fp8.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
