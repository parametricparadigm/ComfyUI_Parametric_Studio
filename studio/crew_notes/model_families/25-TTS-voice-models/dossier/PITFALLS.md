# PITFALLS - 25-TTS-voice-models

## FireRedTTS

### Reference Audio Duration and Quality
- **Symptom**: Unstable or unnatural synthesized audio.
- **Cause**: Reference audio (`prompt_wav`) is too long, too short, or contains long silences.
- **Fix**: Use reference audio with a duration of 3 to 10 seconds. Ensure the audio is smooth and natural. If long silences (>1s) are present in the middle of `prompt_wav`, remove them using `tools/process_prompts.py` or manual editing.
- **Source**: [SOURCES.md - FireRedTeam/FireRedTTS], [PUBLIC README https://huggingface.co/FireRedTeam/FireRedTTS/raw/main/README.md]

### Branch Confusion
- **Symptom**: Incorrect model version loaded or missing features.
- **Cause**: The repository has separate branches for different versions. The current default branch is `FireRedtts-1s`, but `FireRedtts-1` is on a separate branch.
- **Fix**: Explicitly switch to the `FireRedtts-1` branch if using the older version, or ensure you are on `FireRedtts-1s` for the upgraded streamable system.
- **Source**: [SOURCES.md - FireRedTeam/FireRedTTS]

### Text Normalization for Evaluation
- **Symptom**: Potential instability or suboptimal results in specific evaluation scenarios (test-hard).
- **Cause**: Text normalization is not enabled for specific evaluation sets.
- **Fix**: Enable `use_tn=True` in the `synthesize` call for test-hard evaluation.
- **Source**: [SOURCES.md - FireRedTeam/FireRedTTS]

### Environment Dependencies
- **Symptom**: Installation failures or runtime errors due to mismatched PyTorch/CUDA versions.
- **Cause**: PyTorch version does not match the machine's CUDA version.
- **Fix**: Install PyTorch 2.3.1 with the corresponding CUDA version (11.8 or 12.1) as specified in the installation guide.
- **Source**: [SOURCES.md - FireRedTeam/FireRedTTS], [PUBLIC README https://huggingface.co/FireRedTeam/FireRedTTS/raw/main/README.md]

## Chatterbox

### Language Mismatch in Voice Cloning
- **Symptom**: Language transfer outputs inherit the accent of the reference clip's language instead of the target language.
- **Cause**: The reference audio clip does not match the specified language tag.
- **Fix**: Ensure the reference clip matches the specified language tag. To mitigate accent inheritance, set the CFG weight to 0.
- **Source**: [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md]

### Pacing and Expressiveness Issues
- **Symptom**: Speech pacing is too fast for fast-speaking reference styles, or speech lacks dramatic/expressive quality.
- **Cause**: Default settings (`exaggeration=0.5`, `cfg=0.5`) may not suit specific speaker styles or desired output intensity.
- **Fix**: For fast speakers, lower `cfg` to around `0.3`. For expressive/dramatic speech, use lower `cfg` (e.g., `~0.3`) and increase `exaggeration` to `0.7` or higher. Note that higher `exaggeration` tends to speed up speech, so reducing `cfg` helps compensate.
- **Source**: [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md], [MODEL.md]

### Hallucinations in Multilingual Models
- **Symptom**: Unwanted continuation, repetition, or off-prompt speech.
- **Cause**: Using earlier multilingual models (V2) which were less stable.
- **Fix**: Use Chatterbox Multilingual V3, which is optimized to reduce hallucinations.
- **Source**: [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md], [SOURCES.md - ResembleAI/chatterbox]

## Qwen3-TTS

### Node Type Mismatch in ComfyUI
- **Symptom**: Inability to connect engine node to generation node in ComfyUI workflows.
- **Cause**: `Qwen3TTSEngineNode` outputs `TTS_ENGINE`, but `Qwen3CustomVoice` expects `QWEN3_MODEL`.
- **Fix**: Use `AILab_Qwen3TTSCustomVoice` which may handle loading internally, or verify if an adapter node is required (not stated in sources).
- **Source**: [WORKFLOW_PLAN.md]

### Model Loading in Restricted Environments
- **Symptom**: Failure to load model weights during execution.
- **Cause**: Runtime environment is not conducive to downloading weights during execution.
- **Fix**: Manually download model weights to a local directory using `modelscope` or `huggingface-cli` before running the model.
- **Source**: [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md]

## General / System

### Backend URL Mismatch
- **Symptom**: API requests fail or go to the wrong server.
- **Cause**: `COMFY_BASE_URL` points at the wrong ComfyUI server.
- **Fix**: Set `COMFY_BASE_URL` to the address of your running ComfyUI.
- **Source**: [MODEL.md]

### Hardware Compatibility
- **Symptom**: Potential performance issues or incompatibility.
- **Cause**: Models are running on a shared 96 GB Blackwell GPU (sm_120) with specific software stack (ComfyUI v0.43.0, Python 3.12.3, torch 2.16.0.dev20261027+cu134, CUDA/nvcc 13.4).
- **Fix**: Ensure software stack matches the specified versions. Not in sources: Specific VRAM limits per model or precision requirements beyond BF16 for Chatterbox.
- **Source**: [MODEL.md]

### License Compliance
- **Symptom**: Legal risk in commercial use.
- **Cause**: Kyutai TTS voices are licensed under CC-BY-NC-4.0 (non-commercial).
- **Fix**: Ensure use of Kyutai TTS voices is restricted to non-commercial contexts.
- **Source**: [MODEL.md]

### Missing Information
- Not in sources: Specific VRAM usage per model.
- Not in sources: Quantization format compatibility (only BF16 mentioned for Chatterbox, F32 for Kyutai references).
- Not in sources: Scheduler incompatibilities.
- Not in sources: Specific error messages for node type mismatches.
- Not in sources: Performance benchmarks (RTF, latency) on the local Blackwell GPU.
- Not in sources: Specific settings or configurations for Maya1-TTS.
- Not in sources: Whether Kyutai TTS models are compatible with the listed node packs.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
