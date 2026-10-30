# RECIPES - 05-CogVideoX-Mochi-Cosmos-SVD-AnimateDiff-older-video

## Concrete Settings Table

| Model | Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- | :--- |
| Mochi 1 | `height` | `480` | Part of the 480p resolution example. | [SOURCES.md] |
| Mochi 1 | `width` | `848` | Part of the 480p resolution example. | [SOURCES.md] |
| Mochi 1 | `num_frames` | `31` | Example frame count for the API pipeline. | [SOURCES.md] |
| Mochi 1 | `num_frames` | `84` | Example frame count for Diffusers pipeline. | [SOURCES.md] |
| Mochi 1 | `num_inference_steps` | `64` | Inference steps for the API example. | [SOURCES.md] |
| Mochi 1 | `sigma_schedule` | `linear_quadratic_schedule(64, 0.025)` | Sigma schedule used in the API example. | [SOURCES.md] |
| Mochi 1 | `cfg_schedule` | `[4.5] * 64` | CFG schedule used in the API example. | [SOURCES.md] |
| Mochi 1 | `cfg_schedule` | `[6.0] * 64` | Alternative CFG schedule mentioned in settings. | [MODEL.md] |
| Mochi 1 | `seed` | `12345` | Seed used for reproducibility in the API example. | [SOURCES.md] |
| Mochi 1 | `fps` | `30` | Frames per second used in `export_to_video`. | [SOURCES.md] |
| Mochi 1 | `model_dtype` | `bf16` | Data type for the DiT model in the API example. | [SOURCES.md] |
| Mochi 1 | `decode_type` | `tiled_full` | Decode type used in the API pipeline. | [SOURCES.md] |
| Mochi 1 | `cpu_offload` | `True` | CPU offloading enabled in the API pipeline. | [SOURCES.md] |
| Mochi 1 | `batch_cfg` | `False` | Batch CFG setting in the API example. | [SOURCES.md] |
| Mochi 1 | VRAM (Diffusers) | `42GB` | VRAM required for the standard Diffusers example. | [SOURCES.md] |
| Mochi 1 | VRAM (bf16 variant) | `22GB` | VRAM required for the lower precision `bfloat16` variant. | [SOURCES.md] |
| Mochi 1 | VRAM (Single GPU Native) | `60GB` | Approximate VRAM required for single-GPU operation in the native repository. | [MODEL.md] |
| Mochi 1 | VRAM (ComfyUI) | `less than 20GB` | Optimized VRAM requirement when using ComfyUI. | [MODEL.md] |
| SVD-XT | Frames | `25` | Number of frames generated. | [SOURCES.md] |
| SVD-XT | Resolution | `576x1024` | Trained resolution for generation. | [SOURCES.md] |
| SVD-XT | Inference Time | `~180s` | Generation time on an A100 80GB card. | [SOURCES.md] |
| SVD (14 frames) | Frames | `14` | Number of frames for the base SVD model. | [MODEL.md] |
| SVD | Inference Time | `~100s` | Generation time on an A100 80GB card. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `BF16` | Recommended inference precision. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `FP16` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `FP16` | Recommended inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `BF16` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `FP32` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `FP8` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `INT8` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-2B | Inference Precision | `INT4` | Not supported. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `FP16` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `FP32` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `FP8` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `INT8` | Supported inference precision. | [SOURCES.md] |
| CogVideoX-5B | Inference Precision | `INT4` | Not supported. | [SOURCES.md] |
| CogVideoX1.5-5B | Video Duration | `10-second` | Supported video length. | [SOURCES.md] |
| CogVideoX1.5-5B-I2V | Resolution | `any resolution` | Supports video generation at any resolution. | [SOURCES.md] |

## Not in sources
*   Specific `steps`, `CFG/guidance`, `sampler/scheduler`, `resolution/frames/fps`, `shift/strength` values for CogVideoX-5B, CogVideoX-2B, CogVideoX1.5-5B, SVD, AnimateDiff, and Cosmos.
*   Specific `steps`, `CFG/guidance`, `sampler/scheduler`, `shift/strength` values for Mochi 1 (only `num_inference_steps`, `cfg_schedule`, and `sigma_schedule` are provided).
*   Specific `steps`, `CFG/guidance`, `sampler/scheduler`, `resolution/frames/fps`, `shift/strength` values for AnimateDiff.
*   Specific `steps`, `CFG/guidance`, `sampler/scheduler`, `resolution/frames/fps`, `shift/strength` values for Cosmos.
*   Specific `shift` or `strength` values for any model in this family.
*   Specific `sampler` or `scheduler` names for any model in this family (e.g., `KSampler`, `Euler`, `DDIM` are mentioned in workflow plans as generic nodes or features, but not as specific recipe settings for these models).
*   Specific `fps` for CogVideoX, SVD, or AnimateDiff.
*   Specific `resolution` for CogVideoX-5B, CogVideoX-2B, or AnimateDiff.
*   Specific `frames` for CogVideoX-5B, CogVideoX-2B, or AnimateDiff.
> UNVERIFIED: name not in evidence: sampler/scheduler; name not in evidence:  | Frames per second used in ; name not in evidence: scheduler; name not in evidence: strength; name not in evidence: shift/strength; name not in evidence: shift

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
