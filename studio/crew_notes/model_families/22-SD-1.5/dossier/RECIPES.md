# RECIPES - 22-SD-1.5

## Concrete Settings and Outcomes

The following table lists the specific settings, parameters, and values found in the sources.

| Setting / Parameter | Value / Option | Outcome / Context | Source |
| :--- | :--- | :--- | :--- |
| `--scale` (Guidance Scale) | `7.5` | Default guidance scale used by the reference sampling script. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| `--plms` (Sampler) | PLMS | Katherine Crowson's implementation of the PLMS sampler used by default in the reference script. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| `--ddim_steps` (Sampling Steps) | `50` | Number of denoising steps used by default in the reference script. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| Resolution | `512x512` | Image size rendered by the reference script; model was fine-tuned at this resolution. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| Resolution Constraint | Multiple of `8` | Generated image dimensions must be a multiple of 8. | [https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/HEAD/README.md] |
| `--ddim_eta` (Sampler Eta) | `0.0` | Corresponds to deterministic sampling. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| Classifier-free guidance scales | `1.5`, `2.0`, `3.0`, `4.0`, `5.0`, `6.0`, `7.0`, `8.0` | Scales evaluated with `50` PLMS sampling steps to show relative improvements of checkpoints. | [https://raw.githubusercontent.com/CompVis/stable-diffusion/HEAD/README.md] |
| Text-conditioning dropping | `10%` | Used during fine-tuning to improve classifier-free guidance sampling. | [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5] |
| Fine-tuning steps | `595k` | Number of steps for fine-tuning the v1-5 checkpoint. | [https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5] |
| Precision | `FP16` | Model converted to FP16 with a metadata header added; suitable for inference with less VRAM. | [https://huggingface.co/Comfy-Org/stable-diffusion-1.5] |
| Precision | Full precision | Available for UNet, VAE, Text Encoder, and Safety Checker. | [MODEL.md] |
| ControlNet Strength | Adjustable | Adjustable for control conditioning. | [MODEL.md] |
| IP-Adapter Weight | Adjustable | Adjustable for reference conditioning. | [MODEL.md] |
| Sampler Options | `PLMS`, `Euler` | Various sampling methods that can be used. | [MODEL.md] |
| Attention Syntax | `(tuxedo:1.21)` | Alternative syntax to specify parts of text the model should pay more attention to. | [https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/HEAD/README.md] |
| Attention Syntax | `((tuxedo))` | Syntax to pay more attention to specific text. | [https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/HEAD/README.md] |
| Prompt Weights | `:1.2`, `:2.2` | Weights for prompts in Composable-Diffusion (e.g., `a cat :1.2 AND a dog`). | [https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/HEAD/README.md] |

## Not in Sources

Not in sources: Specific recommended CFG/guidance scale values for the `DreamShaper_8_pruned.safetensors` checkpoint.
Not in sources: Specific recommended sampling steps for the `DreamShaper_8_pruned.safetensors` checkpoint.
Not in sources: Specific recommended sampler/scheduler for the `DreamShaper_8_pruned.safetensors` checkpoint.
Not in sources: Specific recommended ControlNet strength values for `control_v11p_sd15_canny_fp16.safetensors` or `control_v11p_sd15_openpose_fp16.safetensors`.
Not in sources: Specific recommended IP-Adapter weight values for `ip-adapter-plus_sd15.safetensors`.
Not in sources: Frame rates (fps) or frame counts for animation generation.
Not in sources: Specific shift or strength values for img2img denoising.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
