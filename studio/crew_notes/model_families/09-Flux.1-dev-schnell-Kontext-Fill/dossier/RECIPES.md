# RECIPES - 09-Flux.1-dev-schnell-Kontext-Fill

## Concrete Settings Table

| Setting | Value | Outcome | Source |
| :--- | :--- | :--- | :--- |
| Sampling steps | Not in sources | Not in sources | [MODEL.md] |
| Guidance scale (CFG) | Not in sources | Not in sources | [MODEL.md] |
| Sampler/Scheduler | `Sigmax.Flux1SchnellSigmaScheduler` (for schnell) | Generates `SIGMAS` for `SamplerCustomAdvanced` | [WORKFLOW_PLAN.md] |
| Sampler/Scheduler | `KSampler` (standard) | Performs sampling (inputs: `steps`, `cfg`, `sampler_name`, `scheduler`, `seed`, `denoise`) | [WORKFLOW_PLAN.md] |
| Sampler/Scheduler | `KSamplerAdvanced` | Performs sampling (inputs: `noise_seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `start_at_step`, `end_at_step`, `return_with_leftover_noise`) | [WORKFLOW_PLAN.md] |
| Sampler/Scheduler | `SamplerCustomAdvanced` | Performs sampling using `SIGMAS` from scheduler | [WORKFLOW_PLAN.md] |
| Resolution (Width/Height) | Not in sources | Not in sources | [WORKFLOW_PLAN.md] |
| Frames | Not in sources | Not in sources | [MODEL.md] |
| FPS | Not in sources | Not in sources | [MODEL.md] |
| Shift | Not in sources | Not in sources | [MODEL.md] |
| Strength (ControlNet) | Not in sources | Not in sources | [WORKFLOW_PLAN.md] |
| Start/End Percentage (ControlNet) | Not in sources | Not in sources | [WORKFLOW_PLAN.md] |
| Denoise | Not in sources | Not in sources | [WORKFLOW_PLAN.md] |
| Seed | Not in sources | Not in sources | [WORKFLOW_PLAN.md] |

## Notes on Missing Data
Not in sources: Specific default sampling steps for FLUX.1 [dev], FLUX.1 [schnell], FLUX.1 Fill [dev], or FLUX.1 Kontext [dev].
Not in sources: Specific default guidance scales for FLUX.1 [dev], FLUX.1 [schnell], FLUX.1 Fill [dev], or FLUX.1 Kontext [dev].
Not in sources: Specific resolution dimensions (width/height) for any variant.
Not in sources: Specific strength values for ControlNet or LoRA adapters.
Not in sources: Specific shift values for schedulers.
Not in sources: Specific denoise values for image-to-image or inpainting tasks.
Not in sources: Specific frame counts or FPS for video generation (family is primarily image-based).

## Workflow Context
The following workflows are documented in the sources but lack specific numeric settings for the parameters listed above:
- **Plan 1: Flux.1 Schnell Text-to-Image**: Uses `FluxLoader`, `Sigmax.Flux1SchnellSigmaScheduler`, `CLIPTextEncode`, `FluxGuidance`, `EmptyLatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`. [WORKFLOW_PLAN.md]
- **Plan 2: Flux.1 Dev with ControlNet Union Pro**: Uses `FluxLoader`, `ControlNetLoader`, `ControlNet Set Union Types (Flux) [Eclipse]`, `CLIPTextEncode`, `FluxGuidance`, `EmptyLatentImage`, `LoadImage`, `ControlNetApplyAdvanced`, `KSampler`, `VAEDecode`, and `SaveImage`. [WORKFLOW_PLAN.md]
- **Plan 3 (Alternative): Flux.1 Dev with IP-Adapter**: Uses `FluxLoader`, IP-Adapter models, `CLIPTextEncode`, `FluxGuidance`, `EmptyLatentImage`, and sampling nodes. [WORKFLOW_PLAN.md]

The sources explicitly state that "No specific settings for steps or guidance are stated in the material, so these must be determined by the user." [WORKFLOW_PLAN.md]

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
