# RECIPES - 10-Flux.2-Klein

| Setting | Value | Outcome / Context | Source |
| :--- | :--- | :--- | :--- |
| `num_inference_steps` | `4` | Used for distilled Klein models (e.g., FLUX.2 [klein] 4B) for production apps and real-time generation. | [MODEL.md], [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| `num_inference_steps` | `50` | Used for Base models (e.g., FLUX.2 [klein] 4B Base) for fine-tuning, LoRA training, and maximum flexibility. | [MODEL.md], [PUBLIC README https://raw.githubusercontent.com/black-forest-labs/flux2/HEAD/README.md] |
| `guidance_scale` | `1.0` | Used in the reference Diffusers implementation for FLUX.2 [klein] 4B. | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| `height` | `1024` | Used in the reference Diffusers implementation for FLUX.2 [klein] 4B. | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| `width` | `1024` | Used in the reference Diffusers implementation for FLUX.2 [klein] 4B. | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| `dtype` | `torch.bfloat16` | Used in the reference Diffusers implementation for FLUX.2 [klein] 4B. | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| `generator` | `torch.Generator(device=device).manual_seed(0)` | Used in the reference Diffusers implementation for FLUX.2 [klein] 4B. | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| VRAM Requirement | `~8GB` | FLUX.2 [klein] 4B fits in this amount of VRAM. | [MODEL.md] |
| VRAM Requirement | `~13GB` | FLUX.2 [klein] 4B fits in this amount of VRAM (alternative figure from model card). | [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| Sampler/Scheduler | Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++). | The sources mention "flow matching transformer" and "rectified flow transformer" but do not specify a ComfyUI or Diffusers scheduler class name. | [MODEL.md], [PUBLIC README https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/raw/main/README.md] |
| Shift/Strength | Not in sources: Specific shift or strength values. | The sources mention "Control Strength" as an input for ControlNet workflows but do not provide a specific numerical value. | [WORKFLOW_PLAN.md] |
| Frames/FPS | Not in sources: Frames or FPS values. | The sources describe image generation and editing, not video generation with specific frame rates. | [MODEL.md] |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 58888 chars.
