# RECIPES - 20-Qwen-Image-Qwen-Image-Edit

| Recipe / Variant | Steps | CFG / Guidance | Sampler / Scheduler | Resolution / Frames / FPS | Shift / Strength | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Standard Text-to-Image (Qwen-Image) | `50` | `true_cfg_scale` `4.0` | Not in sources: sampler/scheduler | `1328x1328` (1:1), `1664x928` (16:9), `928x1664` (9:16), `1472x1140` (4:3), `1140x1472` (3:4), `1584x1056` (3:2), `1056x1584` (2:3) | Not in sources: shift/strength | High-quality image generation with complex text rendering; uses `torch.bfloat16` on CUDA. | [MODEL.md], [PUBLIC README https://huggingface.co/Qwen/Qwen-Image/raw/main/README.md] |
| Standard Image Editing (Qwen-Image-Edit) | `50` | `true_cfg_scale` `4.0` | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions for edit pipeline in code snippet | Not in sources: shift/strength | Semantic and appearance editing (e.g., style transfer, object rotation, text editing); uses `torch.bfloat16` on CUDA. | [PUBLIC README https://huggingface.co/Qwen/Qwen-Image-Edit/raw/main/README.md] |
| Turbo Inference (LoRA 5 steps) | `5` | `cfg` `1` | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions | Not in sources: shift/strength | Faster inference using `p_q_image_2.1_5_steps_v0.1_comfyui_bf16.safetensors`. | [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md] |
| Turbo Inference (LoRA 6 steps) | `6` | `cfg` `1` | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions | Not in sources: shift/strength | Faster inference using `p_q_image_2.1_6_steps_v0.2_comfyui_bf16.safetensors` or `p_q_image_2.1_6_steps_upsampled_v0.2_comfyui_bf16.safetensors`. | [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md] |
| Turbo Inference (LoRA 8 steps) | `8` | `cfg` `1` | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions | Not in sources: shift/strength | Faster inference using `p_q_image_2.1_8_steps_v0.1_comfyui_bf16.safetensors` or `qwen_image_2.1_turbo_lora_avg_rank_178_bf16.safetensors`. | [PUBLIC README https://huggingface.co/Comfy-Org/Qwen-Image-2.1/raw/main/README.md] |
| Turbo Inference (Full Model) | Not in sources: specific step count for full Turbo model | `1.0` (implied by Turbo LoRA settings) | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions | Not in sources: shift/strength | Faster inference using `qwen_image_2.1_turbo_bf16.safetensors`. | [MODEL.md], [WORKFLOW_PLAN.md] |
| ControlNet Inpainting/Union | Not in sources: specific step count | Not in sources: specific CFG value | Not in sources: sampler/scheduler | Not in sources: specific resolution dimensions | Not in sources: specific ControlNet strength | Spatial conditioning for inpainting or union control using `Qwen-Image-InstantX-ControlNet-Inpainting.safetensors` or `Qwen-Image-InstantX-ControlNet-Union.safetensors`. | [MODEL.md], [WORKFLOW_PLAN.md] |

Not in sources: specific sampler or scheduler names (e.g., Euler, DPM++).
Not in sources: specific shift values.
Not in sources: specific ControlNet strength values.
Not in sources: frames or fps (model is for static image generation/editing, not video).

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
