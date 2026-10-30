# RECIPES - 19-Prism-LongCat-VOID-JoyAI-Video

## LongCat-Video-Avatar-1.5

| Setting | Value / Configuration | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Inference Steps | 8 NFE (Number of Function Evaluations) | Accelerates inference via DMD2-based step distillation, balancing cost-effective serving with exceptional visual fidelity. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Audio CFG | 3–5 | Works optimally for lip synchronization accuracy; increasing the value improves synchronization. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Resolution | 480P or 720P | Controlled via `--resolution`; model is compatible with both. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Reference Image Index | `--ref_img_index` (default 10) | Setting between 0 and 24 ensures better consistency; setting to 30 helps reduce repeated actions. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Mask Frame Range | `--mask_frame_range` (default 3) | Increasing the value helps mitigate repeated actions, but excessively large values may introduce artifacts. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Audio Type (Merge) | `audio_type` set to `para` | Requires two audio clips of equal length; resulting audio is obtained by summing the two clips. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Audio Type (Concatenation) | `audio_type` set to `add` | Does not require equal-length inputs; resulting audio is formed by sequentially concatenating the two clips with silence padding for gaps (person1 speaks first, then person2). | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| Attention Mechanism | FlashAttention-2 (default) | Enabled in model config by default; can be changed to FlashAttention-3 or xformers. | [meituan-longcat/LongCat-Video-Avatar-1.5 README](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |

## LongCat-Video-Avatar (v1.0)

| Setting | Value / Configuration | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Guidance | Disentangled unconditional guidance | Decouples speech signals from motion dynamics for natural behavior. | [vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF README](https://huggingface.co/vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF) |
| Attention | Reference skip attention | Preserves identity while preventing excessive conditional image leakage. | [vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF README](https://huggingface.co/vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF) |
| VAE Handling | Cross-Chunk Latent Stitching | Eliminates redundant VAE decode-encode cycles to reduce pixel degradation in long sequences. | [vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF README](https://huggingface.co/vantagewithai/LongCat-Video-Avatar-ComfyUI-GGUF) |

## Prism-Alpha

| Setting | Value / Configuration | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Sampling Options | `PrismSparseOptions` | Specific settings are not stated in the material; incorrect settings may lead to poor quality or failure. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| Sampler Inputs | `BOOLEAN`, `FLOAT`, `INT`, `IMAGE` | Required for `PrismNativeSampler`; specific values are not stated in the material. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |

## JoyAI-Video-Edit

| Setting | Value / Configuration | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Runtime Configuration | `COMBO` and `INT` in `JoyAIRuntimeLoader` | Specific configuration is not stated in the material. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| Sampler Inputs | `BOOLEAN`, `COMBO`, `FLOAT`, `INT`, `STRING` | Required for `JoyAI_Echo_SM_KSampler`; specific values are not stated in the material. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |

## Not in sources

*   Not in sources: Specific CFG/guidance values for LongCat-Video-Avatar v1.0, Prism-Alpha, or JoyAI-Video-Edit.
*   Not in sources: Specific sampler/scheduler names (e.g., Euler, DPM++) for any model in the family.
*   Not in sources: Specific frame counts or FPS values for any model in the family.
*   Not in sources: Specific shift or strength values for any model in the family.
*   Not in sources: Concrete resolution or frame settings for Prism-Alpha or JoyAI-Video-Edit.
*   Not in sources: Specific inference step counts for LongCat-Video-Avatar v1.0, Prism-Alpha, or JoyAI-Video-Edit.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
