# RECIPES - 31-Z-Image-Lumina2

| Model / Variant | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Z-Image` | `28~50` | `3.0 – 5.0` | Not in sources: specific sampler/scheduler name | `512×512` to `2048×2048` (total pixel area, any aspect ratio) | Not in sources: shift/strength values | High-quality generation, rich aesthetics, strong diversity, controllability; supports negative prompting | [https://huggingface.co/Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image) |
| `Z-Image-Turbo` | `8` | No CFG | Not in sources: specific sampler/scheduler name | Not in sources: specific resolution range | Not in sources: shift/strength values | Sub-second inference latency, photorealistic generation, bilingual text rendering | [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |
| `Z-Image-Omni-Base` | `50` | CFG enabled | Not in sources: specific sampler/scheduler name | Not in sources: specific resolution range | Not in sources: shift/strength values | Versatile foundation for generation and editing; raw starting point for fine-tuning | [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |
| `Z-Image-Edit` | `50` | CFG enabled | Not in sources: specific sampler/scheduler name | Not in sources: specific resolution range | Not in sources: shift/strength values | Image editing, creative image-to-image generation, instruction-following | [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |
| `Lumina-Image-2` | Not in sources: specific step count | Not in sources: specific CFG value | `Sigmax.Lumina2SigmaScheduler` (node) | Not in sources: specific resolution range | Not in sources: shift/strength values | Text-to-image generation using ComfyUI workflows | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |

### Specific Parameter Details from Evidence

**Z-Image (Foundation Model)**
*   **Recommended Parameters:**
    *   **Resolution:** `512×512` to `2048×2048` (total pixel area, any aspect ratio) [https://huggingface.co/Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image)
    *   **Guidance scale:** `3.0 – 5.0` [https://huggingface.co/Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image)
    *   **Inference steps:** `28 – 50` [https://huggingface.co/Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image)
*   **Usage Example Settings:**
    *   `height=1280`
    *   `width=720`
    *   `cfg_normalization=False`
    *   `num_inference_steps=50`
    *   `guidance_scale=4`
    *   `generator=torch.Generator("cuda").manual_seed(42)` [https://huggingface.co/Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image)

**Z-Image-Turbo**
*   **Steps:** `8` NFEs (Number of Function Evaluations) [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
*   **CFG:** No CFG [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
*   **Hardware Context:** Fits within `16G VRAM` consumer devices; sub-second latency on `H800` GPUs [https://huggingface.co/Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)

**Lumina-Image-2**
*   **Scheduler Node:** `Sigmax.Lumina2SigmaScheduler` (from pack `ComfyUI-Sigmax`) is used to generate the noise schedule [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md)
*   **Sampler Node:** `SamplerCustomAdvanced` (Standard ComfyUI node) is used to perform the diffusion [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md)
*   **Specific Settings:** Specific step and CFG settings are not stated in the provided material [MODEL.md](MODEL.md)

**Not in sources:**
*   Specific sampler/scheduler name for `Z-Image` and `Z-Image-Turbo` (only `diffusers` library usage is implied, but no specific ComfyUI node name or diffusers scheduler class is named in the evidence for these specific models).
*   Specific resolution ranges for `Z-Image-Turbo`, `Z-Image-Omni-Base`, `Z-Image-Edit`, and `Lumina-Image-2`.
*   Shift or strength values for any model in this family.
*   Frames or FPS (these are image models, not video models, so these parameters are not applicable or stated).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
