# RECIPES - 02-Anima

| Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Resolution | `512^2` to `1536^2` pixels | Supported generation range | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Steps (Base/Aesthetic) | `30-50` | Standard generation setting | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| CFG (Base/Aesthetic) | `4-5` | Standard generation setting | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Steps (Turbo) | `8-12` | Distilled version for fast generations | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| CFG (Turbo) | `1` | Distilled version for fast generations | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Sampler: `er_sde` | Neutral style, flat colors, sharp lines | Reasonable default | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Sampler: `euler_a` | Softer, thinner lines | Can tend towards a 2.5D look; CFG can be pushed a bit higher without burning the image | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Sampler: `dpmpp_2m_sde_gpu` | More variety/creative | Similar style to `er_sde`; can get too wild depending on prompt | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Sampler: `euler` | Basic, slightly more creative | Good with Turbo and Aesthetic versions | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Scheduler: `beta57` | Emphasizes low-noise timesteps | More realistic or painterly look; better textures | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Prompt Weighting | Higher than typically used for SDXL | Example: `(chibi:2)` | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Positive Prefix | `masterpiece, best quality, score_7, safe, ` | Recommended | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Negative Prompt | `worst quality, low quality, score_1, score_2, score_3, artist name, blurry, jpeg artifacts, chromatic aberration` | Recommended | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Artist Tag Format | Prefixed with `@` | Example: `@big chungus` | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |
| Dataset Tags | `ye-pop`, `deviantart` | Used at beginning of prompt followed by newline for non-anime styles | [MODEL.md] [PUBLIC README https://huggingface.co/circlestone-labs/Anima/raw/main/README.md] |

Not in sources: Specific ControlNet strength values
Not in sources: Frames or FPS settings (Anima is a text-to-image model)
Not in sources: Specific shift values
> UNVERIFIED: name not in evidence:  | Example: 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 56837 chars.
