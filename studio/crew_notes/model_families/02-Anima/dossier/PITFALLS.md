# PITFALLS - 02-Anima

## Realism and Photographic Content
**Symptom:** Generated images lack realism or fail to produce photorealistic results.
**Cause:** The model is designed specifically for anime concepts, characters, styles, and non-photorealistic artistic content. It is not trained for realism.
**Fix:** Use the model only for anime and illustration tasks. Do not attempt to generate realistic or photographic images.
**Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Anima-Turbo Diversity and Style
**Symptom:** Outputs lack diversity and adhere strongly to a single default style.
**Cause:** The distillation process used to create Anima-Turbo increases stability and enforces a strong default style, which reduces diversity compared to Base or Aesthetic versions.
**Fix:** Use Anima-Base or Anima-Aesthetic if maximum flexibility, diversity, or style adherence is required. Use Anima-Turbo only when speed and stability are prioritized over variety.
**Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Anima-Turbo Sampling Settings
**Symptom:** Poor generation quality or instability when using Anima-Turbo with standard settings.
**Cause:** Anima-Turbo is a distilled model optimized for specific low-step, low-CFG conditions. Using standard settings (e.g., 30-50 steps, CFG 4-5) is incorrect for this variant.
**Fix:** Set CFG to 1 and steps to 8-12 when using Anima-Turbo.
**Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Anima-Aesthetic Score Tags
**Symptom:** Images push into "slop territory" or appear overly processed.
**Cause:** Anima-Aesthetic is fine-tuned on high-quality images with quality tags stripped from captions. Using `score_*` tags in both positive and negative prompts can push the model too hard.
**Fix:** Do not use `score_*` tags in both the positive and negative prompts for Anima-Aesthetic. It is safe to leave "masterpiece, best quality, " in the positive prompt, but avoid score tags.
**Source:** [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Artist Tag Formatting
**Symptom:** Artist style influence is very weak or absent.
**Cause:** Artist tags must be prefixed with the "@" symbol. Omitting this prefix results in a weak effect.
**Fix:** Always prefix artist names with "@" (e.g., "@big chungus").
**Source:** [MODEL.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Prompt Weighting
**Symptom:** Prompt weighting has less effect than expected compared to other models like SDXL.
**Cause:** Anima requires higher weight values than typically used for SDXL to achieve the same effect.
**Fix:** Use higher weights for prompt weighting (e.g., "(chibi:2)").
**Source:** [MODEL.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Short or Vague Prompts
**Symptom:** Generation of undesired content or unexpected results.
**Cause:** The model may generate undesired content if the prompt is short or lacking details. Extremely short natural language prompts can give unexpected results.
**Fix:** Write sufficiently detailed prompts. For natural language, aim for at least 2 sentences. Use appropriate safety tags in positive and negative prompts.
**Source:** [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Text Rendering
**Symptom:** Lengthy text in images is rendered poorly or incorrectly.
**Cause:** The model is not great at text rendering. It can generally handle single words and sometimes short phrases, but lengthy text rendering will not work well.
**Fix:** Avoid relying on the model to render lengthy text. Limit text requests to single words or short phrases.
**Source:** [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Anima-Base Default Style
**Symptom:** Default style appears very plain and neutral.
**Cause:** Anima-Base is a true base model that has not been aesthetic tuned on a curated dataset.
**Fix:** Use Anima-Aesthetic or Anima-Turbo for a higher quality default art style. Use Anima-Base only when maximum flexibility and diversity are needed, or for training LoRAs.
**Source:** [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## Sampler-Specific Artifacts
**Symptom:** Images tend towards a 2.5D look or become "too wild" and creative.
**Cause:** Specific samplers have distinct behavioral tendencies. `euler_a` can tend towards a 2.5D look. `dpmpp_2m_sde_gpu` can produce more variety but may get too wild depending on the prompt.
**Fix:** Choose the sampler based on desired style. Use `er_sde` for a neutral, flat-color, sharp-line default. Use `euler_a` if a softer, thinner line look is desired (accepting the 2.5D tendency). Use `dpmpp_2m_sde_gpu` cautiously if creative variety is needed.
**Source:** [MODEL.md], [SOURCES.md], [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md]

## ControlNet Strength Settings
**Symptom:** Uncertainty regarding optimal ControlNet strength values.
**Cause:** The README does not specify specific ControlNet strength settings for Anima.
**Fix:** Default or experimental values may be required.
**Source:** [WORKFLOW_PLAN.md]

## VRAM and Hardware Limits
Not in sources: Specific VRAM requirements, minimum GPU memory, or hardware performance benchmarks for Anima.

## Quantization Formats
Not in sources: Supported quantization formats (e.g., FP8, INT8) for Anima model files.

## Scheduler Incompatibilities
Not in sources: Specific scheduler incompatibilities, though the `beta57` scheduler from the ComfyUI RES4LYF custom node pack is noted as usable for a more realistic/painterly look.

## Version Incompatibilities
Not in sources: Specific version incompatibilities between Anima and ComfyUI or other software components.

## Python Dependencies
Not in sources: Specific Python dependencies required for Anima node packs.

## API Graph Structure
Not in sources: Exact API-format graph structure for Anima.

## Torch/CUDA Compatibility
Not in sources: Specific torch/CUDA compatibility details for Anima node packs.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 56837 chars.
