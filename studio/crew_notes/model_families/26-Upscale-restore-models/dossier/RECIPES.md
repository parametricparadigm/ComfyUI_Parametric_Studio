# RECIPES - 26-Upscale-restore-models

## Concrete Settings Table

| Model / Node | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Tile Size | Precision | Outcome | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SeedVR2` (7B) | Not in sources: specific steps for SeedVR2 | Not in sources: specific guidance scale for SeedVR2 | Not in sources: specific sampler/scheduler for SeedVR2 | Not in sources: specific resolution/fps for SeedVR2 | Not in sources: specific shift/strength for SeedVR2 | Not in sources: specific tile size value for SeedVR2 | `fp8_e4m3fn` (DiT), `fp16` (VAE) | Upscaled video frames (IMAGE) | [WORKFLOW_PLAN.md] |
| `AuraSR` | Not in sources: specific steps for AuraSR | Not in sources: specific guidance scale for AuraSR | Not in sources: specific sampler/scheduler for AuraSR | Not in sources: specific resolution for AuraSR | Not in sources: specific shift/strength for AuraSR | Not in sources: specific tile size value for AuraSR | Not in sources: specific precision for AuraSR | Restored/Upscaled image (IMAGE) | [WORKFLOW_PLAN.md] |
| `RealESRGANNode` (with `4x-UltraSharp.safetensors`) | Not in sources: specific steps for RealESRGAN | Not in sources: specific guidance scale for RealESRGAN | Not in sources: specific sampler/scheduler for RealESRGAN | 4x input resolution | Not in sources: specific shift/strength for RealESRGAN | Not in sources: specific tile size value for RealESRGAN | Not in sources: specific precision for RealESRGAN | Upscaled image (IMAGE) | [WORKFLOW_PLAN.md] |
| `SDXL-Turbo` (Text-to-image) | `1` | `0.0` | Not in sources: specific sampler/scheduler name | `512x512` (preferred) | Not in sources: specific shift/strength for T2I | Not in sources: specific tile size value | `fp16` | High quality images | [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md] |
| `SDXL-Turbo` (Image-to-image) | `2` | `0.0` | Not in sources: specific sampler/scheduler name | `512x512` (input resized) | `0.5` | Not in sources: specific tile size value | `fp16` | Image-to-image generation | [PUBLIC README https://huggingface.co/stabilityai/sdxl-turbo/raw/main/README.md] |
| `SDXL 1.0-base` (Base + Refiner) | `40` | Not in sources: specific guidance scale value | Not in sources: specific sampler/scheduler name | Not in sources: specific resolution value | `0.8` (`high_noise_frac`) | Not in sources: specific tile size value | `fp16` | Image with refinement | [PUBLIC README https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md] |
| `Waifu2x-Extension-GUI` (General) | Not in sources: specific steps | Not in sources: specific guidance scale | Not in sources: specific sampler/scheduler | Not in sources: specific resolution/fps values | Not in sources: specific shift/strength | Not in sources: specific tile size value | Not in sources: specific precision | Super-Resolution and Video frame interpolation | [PUBLIC README https://raw.githubusercontent.com/AaronFeng753/Waifu2x-Extension-GUI/HEAD/README.md] |
| `OptiScaler` (General) | Not in sources: specific steps | Not in sources: specific guidance scale | Not in sources: specific sampler/scheduler | Not in sources: specific resolution/fps values | Not in sources: specific shift/strength | Not in sources: specific tile size value | Not in sources: specific precision | Replaces native upscalers, enables frame generation | [PUBLIC README https://raw.githubusercontent.com/optiscaler/OptiScaler/HEAD/README.md] |

## Notes on Missing Data

*   **SeedVR2**: The sources state that "No specific settings for scale factor or steps are stated in the provided material for this node combination." [WORKFLOW_PLAN.md]
*   **AuraSR**: The sources state that "No specific settings for scale factor are stated in the material for `RunAuraSR`." [WORKFLOW_PLAN.md]
*   **RealESRGAN**: The sources state that "No specific settings for the post-processing step are stated in the material." [WORKFLOW_PLAN.md]
*   **General Models**: The `MODEL.md` file lists "Denoise Strength", "Tile Size", and "Guidance Scale" as settings that *can* be adjusted, but explicitly states under "Unknowns" that "The exact configuration parameters for each model (e.g., tile size, denoise strength) are not stated in the provided material." [MODEL.md]
*   **Waifu2x-Extension-GUI**: The README mentions "Settings Presets" and "customizable settings" but does not provide specific numerical values for steps, CFG, or resolution in the text provided. [PUBLIC README https://raw.githubusercontent.com/AaronFeng753/Waifu2x-Extension-GUI/HEAD/README.md]
*   **OptiScaler**: The README mentions "fine-tune their upscaling experience" and "DLSS Presets" but does not provide specific numerical recipe values for steps or CFG in the text provided. [PUBLIC README https://raw.githubusercontent.com/optiscaler/OptiScaler/HEAD/README.md]
> UNVERIFIED: name not in evidence:  | Not in sources: specific tile size value | ; name not in evidence:  | Not in sources: specific sampler/scheduler name | 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
