# RECIPES - 15-LTX-Video-LTX-2

## LTX-2 Diffusers Two-Stage Pipeline

The following settings are extracted from the `Lightricks/LTX-2` README example for production quality generation using the Diffusers library.

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| `width` | `768` | Input resolution width. Must be divisible by 32. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `height` | `512` | Input resolution height. Must be divisible by 32. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `num_frames` | `121` | Number of frames. Must be divisible by 8 + 1. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `frame_rate` | `24.0` | Frame rate for Stage 1 generation. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `num_inference_steps` (Stage 1) | `40` | Steps for the default non-distilled inference. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `guidance_scale` (Stage 1) | `4.0` | Guidance scale for Stage 1. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `sigmas` (Stage 1) | `None` | Uses default scheduler sigmas. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `num_inference_steps` (Stage 2) | `3` | Steps for the Stage 2 distilled LoRA inference. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `guidance_scale` (Stage 2) | `1.0` | Guidance scale for Stage 2. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `sigmas` (Stage 2) | `STAGE_2_DISTILLED_SIGMA_VALUES` | Specific sigma values for the distilled stage. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `noise_scale` (Stage 2) | `STAGE_2_DISTILLED_SIGMA_VALUES[0]` | Renoise with the first sigma value. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `use_dynamic_shifting` | `False` | Scheduler configuration for Stage 2. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `shift_terminal` | `None` | Scheduler configuration for Stage 2. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `torch_dtype` | `torch.bfloat16` | Data type for model loading. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `weight_name` (LoRA) | `ltx-2-19b-distilled-lora-384.safetensors` | LoRA weights loaded for Stage 2. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `set_adapters` weight | `1.0` | Adapter weight for the distilled LoRA. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |

## LTX-2 Checkpoint Specifications

| Model Name | Steps | CFG/Guidance | Notes | Source |
| :--- | :--- | :--- | :--- | :--- |
| `ltx-2-19b-distilled` | `8` | `1` | Distilled version of the full model. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `ltx-2-19b-dev` | Not in sources | Not in sources | Full model, flexible and trainable in `bf16`. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `ltx-2-19b-dev-fp8` | Not in sources | Not in sources | Full model in `fp8` quantization. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| `ltx-2-19b-dev-fp4` | Not in sources | Not in sources | Full model in `nvfp4` quantization. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |

## LTX-Video (LTXV) Checkpoint Specifications

| Model Name | Steps | CFG/Guidance | Notes | Source |
| :--- | :--- | :--- | :--- | :--- |
| `ltxv-2b-0.9.6-distilled` | Not in sources | Not in sources | 15× faster, real-time capable, fewer steps needed, no STG/CFG required. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |
| `ltxv-13b-0.9.7-distilled` | `8` (recommended) | Not in sources | Does not require classifier-free guidance and spatio-temporal guidance. Supports sampling with 8 (recommended), or less diffusion steps. | [https://raw.githubusercontent.com/Lightricks/LTX-Video/HEAD/README.md] |
| `ltxv-13b-0.9.8-distilled` | Not in sources | Not in sources | Faster, less VRAM usage, slight quality reduction compared to 13b. Ideal for rapid iterations. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |
| `ltxv-2b-0.9.8-distilled` | Not in sources | Not in sources | Smaller model, slight quality reduction compared to 13b distilled. Ideal for light VRAM usage. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |
| `ltxv-13b-0.9.8-dev` | Not in sources | Not in sources | Highest quality, requires more VRAM. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |

## General Constraints and Settings

| Setting | Value | Notes | Source |
| :--- | :--- | :--- | :--- |
| Resolution Divisibility | `32` | Width & height settings must be divisible by 32. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| Frame Count Divisibility | `8 + 1` | Frame count must be divisible by 8 + 1. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| Padding Strategy | `-1` | If resolution/frames are not divisible, input should be padded with -1 and then cropped. | [https://huggingface.co/Lightricks/LTX-2/raw/main/README.md] |
| Max FPS (LTX-Video) | `50` | LTX-Video can generate up to 50 FPS videos. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |
| Max Resolution (LTX-Video) | `4K` | LTX-Video supports native 4K resolution. | [https://huggingface.co/Lightricks/LTX-Video/raw/main/README.md] |
| Max Duration (LTX-Video v0.9.8) | `60` seconds | LTX-Video v0.9.8 supports up to 60 seconds of video. | [https://raw.githubusercontent.com/Lightricks/LTX-Video/HEAD/README.md] |
| Max Duration (LTX-2) | `10` seconds | LTX-2 supports longer, continuous clips with synchronized audio up to 10 seconds. | [https://raw.githubusercontent.com/Lightricks/LTX-Video/HEAD/README.md] |
| Quantization Option | `fp8-cast` | Suggested for GPU memory constraints. | [MODEL.md] |
| Offloading Options | `cpu`, `disk` | Suggested for memory management. | [MODEL.md] |

Not in sources: Specific sampler/scheduler names for LTX-Video (LTXV) workflows other than the general "Diffusion-based" description.
Not in sources: Specific CFG values for LTX-Video (LTXV) non-distilled models.
Not in sources: Specific step counts for LTX-Video (LTXV) non-distilled models.
Not in sources: Specific resolution/frames/fps settings for LTX-Video (LTXV) workflows in the provided text (only max capabilities are listed).
Not in sources: Specific shift/strength values for LTX-Video (LTXV) workflows.
Not in sources: Specific node settings for `LTXVBaseSampler` or `LTXVExtendSampler` beyond their existence in the workflow plan.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
