# RECIPES - 08-Faces-identity-portrait-animation

| Model / Pipeline | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| LongCat-Video-Avatar 1.5 | 8 | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Efficient 8-step inference with balanced cost-effective serving and exceptional visual fidelity; accurate lip-synchronization, full-body temporal stability, and robust long-video generation with strict identity consistency. | [https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) |
| LongCat-Video-Avatar 1.5 (Distillation LoRA) | 8 | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Accelerates sampling via distillation for the avatar model. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| LivePortrait | Not in sources: Steps | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Generates animated portraits by extracting motion and appearance features from a source video and applying them to a target image. | [MODEL.md](MODEL.md) |
| MuseTalk | Not in sources: Steps | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Generates talking head video frames by conditioning a UNet on audio and face inputs. | [MODEL.md](MODEL.md) |
| InstantCharacter | Not in sources: Steps | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Injects character identity features from reference images into the diffusion process using an IP-Adapter. | [MODEL.md](MODEL.md) |
| Face Swapping (InsightFace InSwapper) | Not in sources: Steps | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Performs direct face replacement in images and videos. | [MODEL.md](MODEL.md) |
| Face Restoration (CodeFormer, GFPGAN, GPEN, PMRF) | Not in sources: Steps | Not in sources: CFG/guidance value | Not in sources: Sampler/Scheduler name | Not in sources: Resolution/Frames/FPS | Not in sources: Shift/Strength value | Restores and enhances face quality in images and videos. | [LOCAL_MODELS.tsv](LOCAL_MODELS.tsv) |

Not in sources: Specific CFG/guidance scale values for any model in this family.
Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++).
Not in sources: Specific resolution, frame count, or FPS settings for any model in this family.
Not in sources: Specific shift or strength values for any model in this family.
Not in sources: Concrete settings for MuseTalk, LivePortrait, or InstantCharacter beyond general input/output descriptions.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
