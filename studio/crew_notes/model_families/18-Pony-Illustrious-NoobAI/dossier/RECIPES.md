# RECIPES - 18-Pony-Illustrious-NoobAI

| Model | Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- | :--- |
| SDXL-Turbo | `num_inference_steps` | `1` | Generates high quality images in a single network evaluation. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo | `num_inference_steps` | `4` | Further improves performance compared to single step. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo | `guidance_scale` | `0.0` | Disables guidance scale; model does not make use of `guidance_scale`. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo | `negative_prompt` | Not used | Model does not make use of `negative_prompt`. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo | Resolution | `512x512` | Preferred size; higher sizes work as well. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| SDXL-Turbo | `strength` (img2img) | `0.5` | Used with `num_inference_steps=2`; pipeline runs for `int(num_inference_steps * strength)` steps. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| Pony Diffusion V6 XL | `clip skip` | `2` (or `-2`) | Required to avoid low-quality results ("low quality blobs"). | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| Pony Diffusion V6 XL | Sampler | `Euler a` | Recommended sampler. | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| Pony Diffusion V6 XL | Steps | `25` | Recommended step count. | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| Pony Diffusion V6 XL | Resolution | `1024px` | Recommended resolution; model can do most supported SDXL resolutions. | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| Pony Diffusion V6 XL | Negative Prompt | Not needed | Designed to not need negative prompts in most cases. | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| SDXL 1.0 Base | `num_inference_steps` | `40` | Used in ensemble of experts pipeline example. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Base | `denoising_end` | `0.8` | Percentage of steps run on base model in ensemble pipeline. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Refiner | `denoising_start` | `0.8` | Percentage of steps run on refiner model in ensemble pipeline. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Base | `num_inference_steps` | Not in sources: specific recommended step count for standalone use | The README provides code examples but does not explicitly state a single recommended step count for standalone base model usage outside of the ensemble example. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Base | Sampler | Not in sources: specific recommended sampler name | The README does not specify a recommended sampler for the base model. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Base | CFG / Guidance Scale | Not in sources: specific CFG value | The README does not specify a recommended `guidance_scale` value. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL 1.0 Base | Resolution | Not in sources: specific recommended resolution | The README mentions generating latents of "desired output size" but does not specify a fixed recommended resolution. | [https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0] |
| SDXL-Turbo | Sampler | Not in sources: specific sampler name | The README does not specify a recommended sampler. | [https://huggingface.co/stabilityai/sdxl-turbo] |
| Pony Diffusion V6 XL | CFG / Guidance Scale | Not in sources: specific CFG value | The README does not specify a recommended `guidance_scale` value. | [https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL] |
| All Models | Frames / FPS | Not in sources: video generation parameters | These models are text-to-image or image-to-image; no video frame or FPS settings are provided. | [MODEL.md] |
| All Models | Shift | Not in sources: shift values | No shift values are mentioned in the sources. | [MODEL.md] |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
