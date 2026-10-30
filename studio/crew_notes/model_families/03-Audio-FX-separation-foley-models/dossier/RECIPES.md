# RECIPES - 03-Audio-FX-separation-foley-models

## Inference Settings

The sources explicitly state that specific inference settings (such as sampling steps, guidance scales, or batch sizes) are not provided for the primary generation models.

| Model / Task | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| HunyuanVideo-Foley | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | 48kHz high-fidelity audio | [MODEL.md] |
| ControlFoley | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Foley sounds | [MODEL.md] |
| MM-Audio | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Synchronized audio | [MODEL.md] |
| SAM-Audio | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Processed audio | [MODEL.md] |
| MossFormer2 (Enhancement) | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Enhanced speech | [MODEL.md] |
| MossFormer2 (Super-Resolution) | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Super-resolved speech | [MODEL.md] |
| MossFormer2 (Target Speaker Extraction) | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Extracted speech | [MODEL.md] |
| VoxLock (Separation) | Not in sources | Not in sources | Not in sources | Not in sources | Not in sources | Separated speakers | [MODEL.md] |
| ConvTasNet (Separation) | Not in sources | Not in sources | Not in sources | 8kHz sample rate | Not in sources | Separated source audio | [MODEL.md] |

## Training Configuration (ConvTasNet)

| Parameter | Value | Source |
| :--- | :--- | :--- |
| `n_src` | `2` | [SOURCES.md] |
| `sample_rate` | `8000` | [SOURCES.md] |
| `segment` | `3` | [SOURCES.md] |
| `task` | `sep_clean` | [SOURCES.md] |
| `kernel_size` | `16` | [SOURCES.md] |
| `n_filters` | `512` | [SOURCES.md] |
| `stride` | `8` | [SOURCES.md] |
| `bn_chan` | `128` | [SOURCES.md] |
| `hid_chan` | `512` | [SOURCES.md] |
| `mask_act` | `relu` | [SOURCES.md] |
| `n_blocks` | `8` | [SOURCES.md] |
| `n_repeats` | `3` | [SOURCES.md] |
| `skip_chan` | `128` | [SOURCES.md] |
| `lr` | `0.001` | [SOURCES.md] |
| `optimizer` | `adam` | [SOURCES.md] |
| `weight_decay` | `0.0` | [SOURCES.md] |
| `batch_size` | `24` | [SOURCES.md] |
| `epochs` | `200` | [SOURCES.md] |
| `num_workers` | `2` | [SOURCES.md] |

## Workflow Steps

The following steps describe the node connections and file usage for specific pipelines as documented in the workflow plans. No numerical inference parameters (steps, CFG, etc.) are specified in these steps.

### Plan 1: Video-to-Foley Generation with HunyuanVideo-Foley

| Step | Node / Action | Inputs | Outputs | Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `HunyuanVideoFoleyModelLoader` | COMBO | `FOLEY_MODEL`, `STRING` | Loads `foley/hunyuanvideo_foley_fp8_e4m3fn.safetensors` | [WORKFLOW_PLAN.md] |
| 2 | `HunyuanVideoFoleyDependenciesLoader` | `FOLEY_MODEL` | `FOLEY_DEPS`, `STRING` | Loads dependencies | [WORKFLOW_PLAN.md] |
| 3 | `HunyuanVideoFoleyTorchCompile` | `FOLEY_DEPS` | `FOLEY_COMPILED`, `STRING` | Optional compilation step | [WORKFLOW_PLAN.md] |
| 4 | `HunyuanVideoFoley` | `FOLEY_COMPILED` (or `FOLEY_DEPS`), `VIDEO`, `STRING` | `AUDIO`, `IMAGE`, `STRING` | Generates audio from video and prompt | [WORKFLOW_PLAN.md] |
| 5 | `SaveAudio` | `AUDIO` | Saved file | Saves the result | [WORKFLOW_PLAN.md] |

### Plan 2: Audio Separation and Enhancement Pipeline

| Step | Node / Action | Inputs | Outputs | Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `FL_ClearVoice_ModelLoader` | COMBO (`MossFormer2_SE_48K`) | `CLEARVOICE_MODEL` | Loads `speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/MossFormer2_SE_48K/last_best_checkpoint.pt` | [WORKFLOW_PLAN.md] |
| 2 | `FL_ClearVoice_Process` | `AUDIO`, `CLEARVOICE_MODEL` | `AUDIO`, `STRING` | Enhances speech quality | [WORKFLOW_PLAN.md] |
| 3 | `FL_ClearVoice_ModelLoader` | COMBO (`MossFormer2_SR_48K`) | `CLEARVOICE_MODEL` | Loads `speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/MossFormer2_SR_48K/last_best_checkpoint_g.pt` | [WORKFLOW_PLAN.md] |
| 4 | `FL_ClearVoice_Process` | `AUDIO`, `CLEARVOICE_MODEL` | `AUDIO`, `STRING` | Applies super-resolution | [WORKFLOW_PLAN.md] |
| 5 | `SaveAudio` | `AUDIO` | Saved file | Saves final enhanced audio | [WORKFLOW_PLAN.md] |

### Plan 3: Target Speaker Extraction from Video

| Step | Node / Action | Inputs | Outputs | Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `FL_ClearVoice_ModelLoader` | COMBO (`AV_MossFormer2_TSE_16K`) | `CLEARVOICE_MODEL` | Loads `speech_enhancement/ClearerVoice-Studio/clearvoice/checkpoints/AV_MossFormer2_TSE_16K/last_best_checkpoint.pt` | [WORKFLOW_PLAN.md] |
| 2 | `FL_ClearVoice_Process` | `AUDIO`, `CLEARVOICE_MODEL` | `AUDIO`, `STRING` | Extracts target speaker voice. Note: Node signature only accepts `AUDIO`, visual cues may not be utilized via this specific node. | [WORKFLOW_PLAN.md] |
| 3 | `SaveAudio` | `AUDIO` | Saved file | Saves extracted speaker audio | [WORKFLOW_PLAN.md] |

## Missing Information

Not in sources: Specific inference parameters (e.g., number of diffusion steps, guidance scale, sampling method) for HunyuanVideo-Foley, ControlFoley, MM-Audio, and SAM-Audio.
Not in sources: Specific settings for the `FL_ClearVoice_Process` node.
Not in sources: VRAM requirements for the FP8 HunyuanVideo-Foley model specifically.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
