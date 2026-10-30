# RECIPES - 23-SD3-SD3.5

| Setting | Value / Configuration | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| Resolution (SD3.5 Medium) | `--width 1920 --height 1080` | Generates image at 2k resolution | [PUBLIC README https://raw.githubusercontent.com/Stability-AI/sd3.5/HEAD/README.md] |
| Sampling Steps (Example) | `--steps 100` | Used in example command with postfix `steps100` | [PUBLIC README https://raw.githubusercontent.com/Stability-AI/sd3.5/HEAD/README.md] |
| Sampling Steps (Default) | Not in sources: specific default step count for SD3/SD3.5 inference scripts | The reference implementation mentions "default settings" but does not list the numeric value in the provided text | [PUBLIC README https://raw.githubusercontent.com/Stability-AI/sd3.5/HEAD/README.md] |
| Skip Layer Guidance (SD3.5 Medium) | `--skip_layer_cfg True` | Potentially better structure and anatomy coherency | [PUBLIC README https://raw.githubusercontent.com/Stability-AI/sd3.5/HEAD/README.md] |
| ControlNet Strength | Not in sources: specific strength value | The workflow plan notes the strength is "not stated in README" | [WORKFLOW_PLAN.md] |
| Guidance Scale / CFG | Not in sources: specific guidance value | The workflow plan notes the guidance value is "not stated in README" | [WORKFLOW_PLAN.md] |
| Sampler / Scheduler | Not in sources: specific sampler or scheduler names | The workflow plan notes these are "not stated in README" | [WORKFLOW_PLAN.md] |
| IP-Adapter Weight | Not in sources: specific weight value | The workflow plan notes the weight is "not stated in README" | [WORKFLOW_PLAN.md] |
| Frames / FPS | Not in sources: frame count or fps for SD3/SD3.5 | The sources provided for SD3/SD3.5 do not specify video generation parameters; frame counts (e.g., 48 frames, 21 frames) appear only in unrelated SV4D/SV3D sections of the generative-models README | [PUBLIC README https://raw.githubusercontent.com/Stability-AI/generative-models/HEAD/README.md] |
| Shift Value | Not in sources: shift value | No shift parameter is mentioned in the provided evidence | [MODEL.md] |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 51855 chars.
