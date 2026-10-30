# RECIPES - 11-HiDream

| Model / Variant | Steps | Guidance / CFG | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HiDream-I1-Full` | `50` | `5.0` | Not in sources: sampler/scheduler name | `1024` x `1024` (example) | Not in sources: shift/strength values | Standard generation; uses `inference.py` with `--model_type full` [MODEL.md] [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md] |
| `HiDream-I1-Dev` | `28` | `0.0` | Not in sources: sampler/scheduler name | Not in sources: resolution | Not in sources: shift/strength values | Distilled variant; uses `inference.py` with `--model_type dev` [MODEL.md] [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md] |
| `HiDream-I1-Fast` | `16` | `0.0` | Not in sources: sampler/scheduler name | Not in sources: resolution | Not in sources: shift/strength values | Distilled variant; uses `inference.py` with `--model_type fast` [MODEL.md] [https://raw.githubusercontent.com/HiDream-ai/HiDream-I1/HEAD/README.md] |
| `HiDream-O1-Image` | `50` | Not in sources: guidance scale | Not in sources: sampler/scheduler name | Up to `2,048` x `2,048` | Not in sources: shift/strength values | Primary undistilled variant; supports text-to-image, editing, personalization [MODEL.md] [https://huggingface.co/HiDream-ai/HiDream-O1-Image] |
| `HiDream-O1-Image-Dev` | `28` | Not in sources: guidance scale | Not in sources: sampler/scheduler name | Up to `2,048` x `2,048` | Not in sources: shift/strength values | Distilled variant; optimized for faster inference [MODEL.md] [https://huggingface.co/HiDream-ai/HiDream-O1-Image] |
| `HiDream-O1-Image-Dev-2604` | `28` | Not in sources: guidance scale | Not in sources: sampler/scheduler name | Up to `2,048` x `2,048` | Not in sources: shift/strength values | Tailored for text-to-image generation; debuts at #8 in Artificial Analysis Text to Image Arena [https://huggingface.co/HiDream-ai/HiDream-O1-Image] |
| `HiDream-E1.1` | Not in sources: steps | Not in sources: guidance scale | Not in sources: sampler/scheduler name | Not in sources: resolution | Not in sources: shift/strength values | Instruction-based image editing model; updated version of HiDream-E1 series [MODEL.md] [https://huggingface.co/HiDream-ai/HiDream-I1-Full] |

Not in sources: specific sampler or scheduler names for any HiDream model.
Not in sources: shift or strength values for any HiDream model.
Not in sources: frames or fps values (models are static image generators).
Not in sources: guidance scale for `HiDream-O1-Image` variants.
Not in sources: specific resolution settings for `HiDream-I1-Dev` and `HiDream-I1-Fast` (only `HiDream-I1-Full` example shows `1024` x `1024`).
> UNVERIFIED: name not in evidence:  | Not in sources: sampler/scheduler name | 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
