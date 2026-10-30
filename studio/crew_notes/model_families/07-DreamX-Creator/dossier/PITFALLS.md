# PITFALLS - 07-DreamX-Creator

## 1. GPU Memory Exhaustion When Running Creator and Refiner Simultaneously
*   **Symptom:** Out-of-memory errors or system instability when attempting to run the full pipeline in a single ComfyUI graph without offloading.
*   **Cause:** The Creator (7B joint generator) and Refiner (SR-DiT 5B) are both large models. If loaded simultaneously, they exceed available VRAM.
*   **Fix:** Run the Creator and Refiner as separate ComfyUI workflow phases. This ensures both large models do not remain resident on the GPU at the same time. [MODEL.md] [SOURCES.md] [PUBLIC README https://huggingface.co/t8star/DreamX-Creator-Comfy/raw/main/README.md]

## 2. WDDM Shared-Memory Spill on 24 GB Windows Systems
*   **Symptom:** Performance degradation or memory errors on Windows systems with 24 GB VRAM when using the Refiner.
*   **Cause:** The default Refiner configuration may use too much shared memory, causing WDDM (Windows Display Driver Model) to spill memory to system RAM.
*   **Fix:** The Refiner loader defaults to `window_chunk=1` and three latent KV-history frames on 24 GB Windows systems to limit WDDM shared-memory spill. On higher-memory systems, the original nine-frame history remains selectable. [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 3. Inability to Recover Collapsed Low-Resolution Base Samples
*   **Symptom:** The 2K Refiner produces poor quality output or fails to improve the video if the initial generation is bad.
*   **Cause:** The Refiner is a super-resolution tool that preserves content and motion; it does not correct fundamental generation failures (collapses) in the base low-resolution sample.
*   **Fix:** Check the Creator output before optional 2× refinement. If the base sample is collapsed, re-run the Creator phase with a different seed or settings. [WORKFLOW_PLAN.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 4. CPU-Only Runtime Limitations and Experimental Status
*   **Symptom:** The `rust-model-inference` runtime does not support GPU acceleration for DreamX-Creator, and results may not match CUDA/Python Oracle outputs.
*   **Cause:** The native CPU runtime is currently marked as **Experimental**. CUDA/Python Oracle numerical parity has not been completed, and the refiner shifted scheduler has not been compared checkpoint by checkpoint.
*   **Fix:** Use the runtime only for CPU inference. Do not expect bit-exact parity with CUDA implementations. Review the runtime's current support status before production use. [SOURCES.md] [PUBLIC README https://huggingface.co/EvoAwaken-Workshop/DreamX-Creator-gguf/raw/main/README.md] [PUBLIC README https://raw.githubusercontent.com/Liyulingyue/rust-model-inference/HEAD/README.md]

## 5. GGUF Model Pair Mismatch
*   **Symptom:** Inference fails to start or throws a validation error in the `rust-model-inference` runtime.
*   **Cause:** The `DreamX-Creator-Q8_0.gguf` and `mmproj-DreamX-Creator-BF16.gguf` files must be used together. The runtime verifies their shared pair ID before inference.
*   **Fix:** Ensure both files are downloaded from the same source and version. Use `--dry-run` to validate the model pair and inspect the memory estimate without running generation. [SOURCES.md] [PUBLIC README https://huggingface.co/EvoAwaken-Workshop/DreamX-Creator-gguf/raw/main/README.md]

## 6. Duration Frame Count Mismatch
*   **Symptom:** The generated video duration is shorter than requested, or the Refiner fails to process the video.
*   **Cause:** The Creator truncates duration down to a Wan-compatible `4N+1` frame count. For example, 5 seconds at 24 FPS becomes 117 frames. The Refiner exposes only its exact-length IMAGE sequence instead of a padded generic LATENT.
*   **Fix:** Account for the `4N+1` frame snap when calculating expected output duration. Ensure the input to the Refiner matches the exact length of the Creator output. [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 7. Stochastic Nature of Native Speech
*   **Symptom:** The generated audio transcript does not exactly match the text prompt, even if the prompt requests specific wording.
*   **Cause:** Native speech generation is stochastic. The prompt can request exact wording but cannot guarantee its transcript.
*   **Fix:** Accept that audio transcription may vary. Use the prompt to guide the general content and tone, but do not rely on it for verbatim text-to-speech accuracy. [WORKFLOW_PLAN.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 8. Long-Video cuDNN Failures in Refiner
*   **Symptom:** Crashes or errors during the Refiner phase when processing long videos.
*   **Cause:** Standard VAE encode/decode operations can fail with long sequences due to cuDNN limitations.
*   **Fix:** The Refiner tiles its Wan VAE encode/decode internally to avoid long-video cuDNN failures. Ensure the node pack version includes this tiling feature. [WORKFLOW_PLAN.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 9. Mixed CPU/CUDA Weights Under ComfyUI Partial Offload
*   **Symptom:** Errors or incorrect results when using ComfyUI's generic partial-offload path.
*   **Cause:** The Creator and Refiner load their vendored torch layers coherently on the GPU. Using generic partial offload can lead to mixed CPU/CUDA weights.
*   **Fix:** Use the native ComfyUI V3 nodes from the `T8mars/Comfyui-DreamX-Creator-T8` pack, which handle model offloading correctly. [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 10. Missing Model Files in Local Directory
*   **Symptom:** The node pack fails to load models or reports missing files.
*   **Cause:** The local folder `_complete_pipelines/DreamX-Creator` currently has 0 model files. The complete ComfyUI-ready model bundle is approximately 54.25 GB (50.53 GiB) and must be downloaded separately.
*   **Fix:** Download the model weights from `t8star/DreamX-Creator-Comfy` to `ComfyUI/models/dreamx_creator` or the node-local `checkpoints/` directory. Validate the download using `verify_models.py`. [MODEL.md] [SOURCES.md] [PUBLIC README https://huggingface.co/t8star/DreamX-Creator-Comfy/raw/main/README.md]

## 11. Incorrect Model Root Path
*   **Symptom:** The loader cannot find the model files.
*   **Cause:** The `model_root=auto` setting searches the custom-node repository's `checkpoints/` directory first, then `ComfyUI/models/dreamx_creator/`. If the files are not in one of these locations, the loader will fail.
*   **Fix:** Place the model files in `ComfyUI/models/dreamx_creator` or `ComfyUI/custom_nodes/Comfyui-DreamX-Creator-T8/checkpoints`. [SOURCES.md] [PUBLIC README https://huggingface.co/t8star/DreamX-Creator-Comfy/raw/main/README.md]

## 12. Audio VAE Precision Mismatch
*   **Symptom:** Audio quality issues or decoding errors.
*   **Cause:** The bundled Audio VAE stays in float32, matching the released decoder path. If the VAE is cast to a different precision, it may not match the expected behavior.
*   **Fix:** Ensure the Audio VAE is loaded in float32. [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 13. Scheduler and Sampler Mismatch
*   **Symptom:** Generation quality differs from expected results or fails to converge.
*   **Cause:** The Creator example uses ComfyUI's `normal` scheduler with Euler at 20 steps, matching the released Diffusers FlowMatch timestep sequence. Using a different scheduler or sampler may not produce the same results.
*   **Fix:** Use the `normal` scheduler with Euler at 20 steps for the Creator phase. [MODEL.md] [PUBLIC README https://raw.githubusercontent.com/T8mars/Comfyui-DreamX-Creator-T8/HEAD/README.md]

## 14. Memory Overcommit in Rust Runtime
*   **Symptom:** The `rust-model-inference` runtime fails to start or crashes due to insufficient memory.
*   **Cause:** The memory estimate for the inference process exceeds physical memory.
*   **Fix:** Use `--dry-run` to inspect the memory estimate. If the estimate exceeds physical memory, explicitly pass `--allow-memory-overcommit` to allow the runtime to proceed, though this may lead to system instability. [PUBLIC README https://raw.githubusercontent.com/Liyulingyue/rust-model-inference/HEAD/README.md]

## 15. Unsupported Quantization Formats in Rust Runtime
*   **Symptom:** The `rust-model-inference` runtime fails to load the model.
*   **Cause:** The runtime currently supports `Q8_0` for the main model and `BF16/F32` for the mmproj. Other quantization formats are not supported.
*   **Fix:** Use the `Q8_0` and `BF16/F32` GGUF files provided in the `EvoAwaken-Workshop/DreamX-Creator-gguf` repository. [SOURCES.md] [PUBLIC README https://huggingface.co/EvoAwaken-Workshop/DreamX-Creator-gguf/raw/main/README.md]

## 16. Missing Dependencies in PS Venv
*   **Symptom:** The ComfyUI node pack fails to load or throws import errors.
*   **Cause:** The node pack's Python dependencies are not installed in the Parametric Studio (PS) venv.
*   **Fix:** Install the node pack's Python dependencies in the PS venv. [MODEL.md]

## 17. Conflict with PS Torch/CUDA Pins
*   **Symptom:** The ComfyUI node pack fails to load or throws version conflict errors.
*   **Cause:** The node pack's requirements conflict with the PS torch/CUDA pins.
*   **Fix:** Ensure the node pack's requirements do not conflict with the PS torch/CUDA pins. [MODEL.md]

## 18. Incorrect COMFY_BASE_URL
*   **Symptom:** The contest studio backend fails to submit API-format graphs to the ComfyUI server.
*   **Cause:** `COMFY_BASE_URL` points at the wrong ComfyUI server.
*   **Fix:** Set `COMFY_BASE_URL` to the address of your running ComfyUI.

## 20. Reduced Validation Run Does Not Establish Official 2K Quality
*   **Symptom:** The output quality from the `rust-model-inference` runtime does not match the official 2K quality.
*   **Cause:** The reduced validation run (64x64, one-frame, one-step) does not establish official 2K output quality.
*   **Fix:** Use the official CUDA/Python implementation for production-quality 2K output. [SOURCES.md] [PUBLIC README https://huggingface.co/EvoAwaken-Workshop/DreamX-Creator-gguf/raw/main/README.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
