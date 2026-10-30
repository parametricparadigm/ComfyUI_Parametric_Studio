# RECIPES - 14-Krea-2

| Recipe / Task | Model | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength / Other Values | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Text-to-Image (Base) | `oss_raw` | `52` | `3.5` | Full sampler with classifier-free guidance | Up to 1k resolution | N/A | Diverse and highly malleable images; suitable for fine-tuning, post-training, and LoRA training | [krea-ai/krea-2] |
| Text-to-Image (Fast) | `oss_turbo` | `8` | `0.0` | Distilled sampling process | 1k to 2k resolution (e.g., `2048`x`2048`) | `mu` `1.15` | Fast, high-quality text-to-image generation | [krea-ai/krea-2] |
| Image Editing (Removals) | `oss_raw` | `~20` | `3` | N/A | N/A | N/A | Recommended for removals and "delete salient content" edits; distilled Turbo at CFG 1 usually re-renders the subject instead of removing it | [lbouaraba/comfyui-krea2edit] |
| Image Editing (General) | `oss_turbo` | `8` | `1` | N/A | ≤2MP | `grounding_px` default `768` (range `384`–`768` for v1.2, `512`–`1536` for v1) | Fast path (~1 min at 2MP) for recolor, add/insert, attribute changes, restyles, scene translation | [lbouaraba/comfyui-krea2edit] |
| Style LoRA Application | N/A | N/A | N/A | N/A | N/A | Strength `1.0` | Applies specific styles (e.g., `krea2_darkbrush`, `krea2_retroanime`) | [Comfy-Org/Krea-2] |

Not in sources: Specific sampler names (e.g., Euler, DPM++).
Not in sources: FPS or frame counts (model is for static images).
Not in sources: Specific node names for setting `mu` in ComfyUI standard nodes.
> UNVERIFIED: name not in evidence:  | Distilled sampling process | 1k to 2k resolution (e.g., ; name not in evidence:  | N/A | ≤2MP | 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 59070 chars.
