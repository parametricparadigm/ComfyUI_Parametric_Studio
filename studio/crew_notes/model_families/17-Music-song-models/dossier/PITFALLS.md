# PITFALLS - 17-Music-song-models

## ACE-Step 1.5

### Text Encoder Architectural Lock
*   **Symptom:** Incompatibility or failure when attempting to use a text encoder other than the 0.6B Qwen3 variant with the DiT.
*   **Cause:** The DiT was trained end-to-end with the `Qwen3-Embedding-0.6B` model. Its `CondEncoder` projection weights (1024 to 2048) are baked into every DiT checkpoint, making the Text-Enc architecturally locked to 0.6B.
*   **Fix:** Use only the `Qwen3-Embedding-0.6B` (or `qwen_0.6b_ace15.safetensors`) for the text encoding stage.
*   **Source:** [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF]

### LM Quantization Limitation
*   **Symptom:** Broken audio code generation when using specific quantized LM files.
*   **Cause:** The 4B LM does not have a `Q4_K_M` variant because this quantization level breaks audio code generation. Additionally, small LMs (0.6B/1.7B) only have `BF16` and `Q8_0` because they are too small for aggressive quantization.
*   **Fix:** For the 4B LM, use `BF16`, `Q8_0`, `Q6_K`, or `Q5_K_M`. For 0.6B/1.7B LMs, use only `BF16` or `Q8_0`.
*   **Source:** [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF]

### VRAM Expectation Mismatch (Local vs. Consumer Claims)
*   **Symptom:** Potential confusion regarding hardware requirements; local files are significantly larger than the "consumer hardware" claim suggests.
*   **Cause:** The source material states ACE-Step 1.5 runs on less than 4GB VRAM for consumer hardware, but the local installation contains XL BF16 variants (e.g., `acestep_v1.5_xl_base_bf16.safetensors` at 9.97 GB) which are significantly larger.
*   **Fix:** Ensure the GPU has sufficient VRAM for the specific local variant being used (e.g., 96 GB Blackwell card is required for the local XL BF16 files, whereas the 4GB claim applies to other quantizations or smaller variants not present locally).
*   **Source:** [MODEL.md]

### Backend URL Misconfiguration
*   **Symptom:** Backend submission failures or requests sent to the wrong server instance.
*   **Cause:** `COMFY_BASE_URL` points at the wrong ComfyUI server.
*   **Fix:** Set `COMFY_BASE_URL` to the address of your running ComfyUI.
*   **Source:** [MODEL.md]

### Missing Python Dependencies
*   **Symptom:** Nodes may not be placeable in API-format graphs or may fail to execute.
*   **Cause:** The Python dependencies for the model nodes must be in the PS venv, and they must not conflict with the PS torch/CUDA pins.
*   **Fix:** Verify that all required Python dependencies are installed in the PS venv and compatible with the current torch/CUDA pins.
*   **Source:** [MODEL.md]

### Lyric Editing Limitation
*   **Symptom:** Distortion when attempting to modify large segments of lyrics at once.
*   **Cause:** The flow-edit technology for lyric editing can only modify small segments of lyrics at once to avoid distortion.
*   **Fix:** Apply multiple edits sequentially rather than modifying large segments in a single pass.
*   **Source:** [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md]

### Language Performance Variance
*   **Symptom:** Underperformance in less common languages.
*   **Cause:** Data imbalance in the training dataset.
*   **Fix:** Be aware that less common languages may underperform compared to the top 10 well-performing languages (English, Chinese, Russian, Spanish, Japanese, German, French, Portuguese, Italian, Korean).
*   **Source:** [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md]

### Windows Triton Dependency
*   **Symptom:** Failure to run with memory optimization flags on Windows.
*   **Cause:** The recommended launch options for memory optimization (`--torch_compile true --cpu_offload true --overlapped_decode true`) require `triton` on Windows.
*   **Fix:** Install `triton-windows` via `pip install triton-windows`.
*   **Source:** [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md]

## Mini-Max Music 3

### Missing Inference Parameters
*   **Symptom:** Uncertainty in workflow configuration; inability to set optimal sampling parameters.
*   **Cause:** The specific sampling steps and CFG scale for MiniMax Music 3 are not stated in the provided README excerpts or local material.
*   **Fix:** Not in sources: Specific recommended steps and CFG scale values for MiniMax Music 3.
*   **Source:** [WORKFLOW_PLAN.md]

### Missing Python Dependencies
*   **Symptom:** Nodes may not be placeable in API-format graphs or may fail to execute.
*   **Cause:** The specific Python dependencies required for the Mini-Max Music 3 node packs are not stated.
*   **Fix:** Not in sources: Specific Python dependencies for Mini-Max Music 3.
*   **Source:** [MODEL.md]

### Missing API Graph Structure
*   **Symptom:** Inability to construct valid API-format graphs for backend submission.
*   **Cause:** The exact API graph structure for Mini-Max Music 3 is not provided in the material, only the model file locations.
*   **Fix:** Not in sources: Exact API graph structure for Mini-Max Music 3.
*   **Source:** [MODEL.md]

### Large Text Encoder Size
*   **Symptom:** High VRAM consumption dominated by the text encoder component.
*   **Cause:** The local text encoder `minimax_music3_text_encoder_pruned_bf16.safetensors` is 16.71 GB, which is the dominant component of the pipeline.
*   **Fix:** Ensure the GPU has sufficient VRAM to accommodate the 16.71 GB text encoder (the 96 GB GPU can accommodate this).
*   **Source:** [MODEL.md]

## General / Cross-Family

### Unrelated Software Confusion
*   **Symptom:** Incorrect identification of model sources or repositories.
*   **Cause:** Candidate repos such as `lyswhut/lx-music-desktop` and `team-spotube/spotube` are unrelated software (music players/streaming apps), not generative AI models. Similarly, `Serveurperso/MiniMax-Music3-GGUF` and `audio-cpp/MiniMax-Music3-GGUF` are flagged as unrelated model families or different from ACE-Step.
*   **Fix:** Use only the verified sources: `Serveurperso/ACE-Step-1.5-GGUF`, `Comfy-Org/ACE-Step-1.5`, `ACE-Step/Ace-Step1.5`, `Comfy-Org/MiniMax-Music-3`, and `ace-step/ACE-Step`.
*   **Source:** [MODEL.md]

### Local File Availability vs. Ecosystem
*   **Symptom:** Attempting to use quantizations or variants that are not present locally.
*   **Cause:** The local installation only confirms specific files (e.g., XL BF16 for ACE-Step, FP16 for Mini-Max DiT). Other quantizations (Q8_0, Q6_K, etc.) and variants (FP32, INT8 ConvRot) exist in the broader ecosystem but are not confirmed in the local largest files list.
*   **Fix:** Verify local file existence before configuring workflows; do not assume availability of non-local quantizations.
*   **Source:** [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
