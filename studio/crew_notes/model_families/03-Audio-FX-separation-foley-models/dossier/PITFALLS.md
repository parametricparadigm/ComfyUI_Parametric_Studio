# PITFALLS - 03-Audio-FX-separation-foley-models

## 1. HunyuanVideo-Foley VRAM and Precision Constraints

**Symptom:** High VRAM consumption or failure to load the model on standard GPUs; potential incompatibility with hardware that does not support specific quantization formats.
**Cause:** The local variant of HunyuanVideo-Foley is an `fp8` (`e4m3fn`) version with `5.13B` parameters. The README notes that the `XL-sized model` requires `offload inference support` to significantly reduce VRAM requirements, implying high resource usage for larger variants. The workflow plan notes that the `FP8` model may require specific hardware support.
**Fix:** Use the `HunyuanVideo-Foley-XL` model which supports `offload inference`. Ensure the hardware (e.g., the local `96 GB Blackwell card`) supports `FP8` quantization. Use the `if-ai__ComfyUI_HunyuanVideoFoley` pack which explicitly supports `cpu offloading` and `FP8 quantization`.
**Source:** [MODEL.md], [WORKFLOW_PLAN.md], [PUBLIC README https://raw.githubusercontent.com/Tencent-Hunyuan/HunyuanVideo-Foley/HEAD/README.md]

## 2. Node Input Mismatch: Video vs. Image

**Symptom:** Workflow failure or incorrect input connection when trying to feed video into the HunyuanVideo-Foley generation node.
**Cause:** Different ComfyUI packs implement the model with different input signatures. The `if-ai__ComfyUI_HunyuanVideoFoley` pack's `HunyuanVideoFoley` node accepts a `VIDEO` input directly. In contrast, other packs like `ComfyUI-HunyuanVideo-Foley` use an `IMAGE` input for the sampler.
**Fix:** Verify the specific pack being used. If using `if-ai__ComfyUI_HunyuanVideoFoley`, connect the `VIDEO` output from a loader to the `VIDEO` input. If using `ComfyUI-HunyuanVideo-Foley`, ensure an `IMAGE` input is provided.
**Source:** [WORKFLOW_PLAN.md]

## 3. Target Speaker Extraction (TSE) Visual Input Limitation

**Symptom:** The visual component of the Target Speaker Extraction model may not be utilized, potentially reducing extraction accuracy for audio-visual alignment.
**Cause:** The `AV_MossFormer2_TSE_16K` model is designed for "audio-visual speaker extraction" and relies on face detection (`sfd_face.pth`). However, the `FL_ClearVoice_Process` node in the `ComfyUI_FL-ClearVoice` pack only accepts `AUDIO` and `CLEARVOICE_MODEL` inputs; it does not explicitly list a `VIDEO` input.
**Fix:** Pre-extract the audio from the video before feeding it into the `FL_ClearVoice_Process` node. Alternatively, seek a different node or pack that explicitly supports video input for the TSE pipeline to ensure visual cues are processed.
**Source:** [WORKFLOW_PLAN.md], [MODEL.md]

## 4. ConvTasNet Sample Rate Restriction

**Symptom:** Poor separation quality or model failure when processing audio at sample rates other than `8kHz`.
**Cause:** The `ConvTasNet` model (`Awais/Audio_Source_Separation`) was trained specifically on the `Libri2Mix` dataset with a `sample_rate` of `8000` Hz. It is a `2-source` separation model.
**Fix:** Resample input audio to `8kHz` before processing with the ConvTasNet model. Do not use this model for high-fidelity separation or for more than 2 sources.
**Source:** [SOURCES.md], [PUBLIC README https://huggingface.co/Awais/Audio_Source_Separation/raw/main/README.md]

## 5. Missing Inference Parameters

**Symptom:** Inability to optimize generation quality or speed due to lack of documented settings.
**Cause:** Specific inference parameters such as `sampling steps`, `guidance scales`, `batch sizes`, `diffusion steps`, and `sampling method` for `HunyuanVideo-Foley`, `ControlFoley`, `MM-Audio`, and `SAM-Audio` are not stated in the provided sources.
**Fix:** Not in sources: Specific inference parameters for HunyuanVideo-Foley, ControlFoley, MM-Audio, and SAM-Audio. Users must rely on default node settings or external documentation not present in this dossier.
**Source:** [MODEL.md]

## 6. License and Regional Restrictions

**Symptom:** Potential legal or compliance issues when distributing or using the models in certain regions.
**Cause:** The `HunyuanVideo-Foley` model is under the `tencent-hunyuan-community` license and is marked as `extra_gated_eu_disallowed: true`. The `ConvTasNet` model is under `CC BY-SA 4.0` (with a derivative license notice mentioning `Attribution-ShareAlike 3.0 Unported`).
**Fix:** Review the `tencent-hunyuan-community` license terms carefully. Avoid using the HunyuanVideo-Foley model in the EU if the `extra_gated_eu_disallowed` flag indicates a restriction. Ensure attribution is provided for the ConvTasNet model as per `CC BY-SA 4.0`.
**Source:** [SOURCES.md], [PUBLIC README https://huggingface.co/AEmotionStudio/hunyuanvideo-foley-models/raw/main/README.md]

## 7. Dependency and Environment Conflicts

**Symptom:** Backend integration failures or node incompatibility.
**Cause:** The models require specific Python dependencies in the `Parametric Studio` virtual environment. There may be conflicts with existing `torch`/`CUDA` pins. The exact Python dependencies for each node pack are not listed in the sources.
**Fix:** Ensure the corresponding Python dependencies are installed in the virtual environment. Check for conflicts with existing `torch`/`CUDA` versions. Verify that nodes are compatible with API-format graphs.
**Source:** [MODEL.md]

## 8. Unverified Candidate Repositories

**Symptom:** Potential use of low-quality or unrelated software if incorrect repositories are selected.
**Cause:** Several candidate repositories were checked and flagged as problematic: `melmass/audio-separation` and `shiromiya/audio-separation-models` are flagged as "Tiny repo" with low downloads/likes and "no clear official status". `LedFx/LedFx` and `ahodges9/LedFx` are flagged as "Unrelated software (LED effect engine), not an AI model".
**Fix:** Use only the verified sources: `AEmotionStudio/hunyuanvideo-foley-models` and `Awais/Audio_Source_Separation`. Avoid the flagged repositories.
**Source:** [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
