# RECIPES - 12-HunyuanVideo-FramePack

## Concrete Settings

| Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Inference Steps (Standard) | Not in sources: specific standard step count for non-distilled models | Standard steps are mentioned as an option, but no specific number is provided in the evidence. | [MODEL.md] |
| Inference Steps (Distilled) | `4`, `8`, `12` | Reduced steps for distilled models for faster generation. | [MODEL.md] |
| Inference Steps (480p I2V Step-Distilled) | `8` or `12` | Generates videos in 8 or 12 steps. | [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md] |
| Inference Steps (480p I2V Step-Distilled, Fast) | `4` | Faster speed with slightly reduced quality. | [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md] |
| CFG / Guidance | Not in sources: specific CFG or guidance scale values | CFG-distilled models are available, but no specific guidance values are listed. | [MODEL.md] |
| Sampler / Scheduler | Not in sources: specific sampler or scheduler names | The workflow uses `HyVideoSampler`, but the underlying algorithm (e.g., Euler, DPM++ etc.) is not specified. | [WORKFLOW_PLAN.md] |
| Resolution | `480p`, `720p`, `1080p` | Supported resolutions for HunyuanVideo-1.5. | [MODEL.md] |
| Frames / FPS | Not in sources: specific frame count or FPS values | The model operates in a spatial-temporally compressed latent space, but specific output frame rates or counts are not defined in the settings. | [MODEL.md] |
| Shift / Strength | Not in sources: specific shift or strength values | No shift or strength parameters are mentioned in the provided evidence. | [MODEL.md] |
| Precision | `FP16`, `BF16`, `FP8` | Available precision formats for models. | [MODEL.md] |
| Acceleration | `xDiT`, `DeepCache`, `TeaCache`, `TaylorCache`, `MagCache` | Support for parallel inference and cache-based acceleration techniques. | [MODEL.md] |
| Generation Time (RTX 4090) | `75 seconds` | End-to-end generation time for 480p I2V step-distilled model on RTX 4090. | [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md] |
| Speedup (MagCache) | `1.7x` | Speedup achieved with 20 inference steps using MagCache. | [PUBLIC README https://huggingface.co/tencent/HunyuanVideo-1.5/raw/main/README.md] |

## Workflow Specifics

### HunyuanVideo 1.5 Text-to-Video (720p)
*   **Models:** `hunyuanvideo1.5_720p_t2v_fp16.safetensors`, `qwen2.5-vl-7b-bf16.safetensors`, `hunyuan_video_vae_bf16.safetensors`
*   **Nodes:** `DownloadAndLoadHyVideoTextEncoder`, `HyVideoModelLoader`, `HyVideoVAELoader`, `HyVideoTextEncode`, `HunyuanVideoEmptyLatent`, `HyVideoSampler`, `HyVideoDecode`
*   **Settings:** Not in sources: specific steps, CFG, etc. for this specific workflow configuration.
*   **Source:** [WORKFLOW_PLAN.md]

### HunyuanVideo 1.5 Image-to-Video (720p)
*   **Models:** `hunyuanvideo1.5_720p_i2v_fp16.safetensors`, `qwen2.5-vl-7b-bf16.safetensors`, `hunyuan_video_vae_bf16.safetensors`, `clip-vit-large-patch14.safetensors`
*   **Nodes:** `DownloadAndLoadHyVideoTextEncoder`, `HyVideoModelLoader`, `HyVideoVAELoader`, `HunyuanVideoVisionLoader`, `HyVideoI2VEncode`, `HunyuanVideoEmptyLatent`, `HyVideoSampler`, `HyVideoDecode`
*   **Settings:** Not in sources: specific settings for this workflow.
*   **Source:** [WORKFLOW_PLAN.md]

### HunyuanVideo 1.5 Super Resolution (720p to 1080p)
*   **Models:** `hunyuanvideo1.5_1080p_sr_distilled_fp8_scaled.safetensors`, `hunyuan_video_vae_bf16.safetensors`
*   **Nodes:** `HyVideoVAELoader`, `HunyuanVideoVisionLoader`, `HunyuanVideo15SuperResolution`, `HyVideoDecode`
*   **Settings:** Not in sources: specific settings for this workflow.
*   **Source:** [WORKFLOW_PLAN.md]

## FramePack Specifics
*   **Description:** A method for packing input frame context in next-frame prediction models, associated with the HunyuanVideo ecosystem.
*   **Settings:** Not in sources: specific configuration parameters for the "FramePack" technique in the ComfyUI graph format.
*   **Source:** [MODEL.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
