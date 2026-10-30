# RECIPES - 29-Wan-2.1

| Setting | Value | Context / Outcome | Source |
| :--- | :--- | :--- | :--- |
| `num_inference_steps` | `10` | Basic inference for T2V-14B | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--size` | `1280*720` | T2V-14B single-GPU inference | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--size` | `832*480` | T2V-1.3B single-GPU inference | [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B] |
| `--sample_shift` | `8` | Recommended for T2V-1.3B; adjustable within range of `8` to `12` | [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B] |
| `--sample_guide_scale` | `6` | Recommended for T2V-1.3B | [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B] |
| `--offload_model` | `True` | Reduces GPU memory usage; used with T2V-1.3B on RTX 4090 | [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B] |
| `--t5_cpu` | (flag) | Runs T5 on CPU to reduce GPU memory usage | [https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B] |
| `--ulysses_size` | `8` | Multi-GPU inference using FSDP + xDiT USP | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--dit_fsdp` | (flag) | Multi-GPU inference using FSDP + xDiT USP | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--t5_fsdp` | (flag) | Multi-GPU inference using FSDP + xDiT USP | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--nproc_per_node` | `8` | Multi-GPU inference using FSDP + xDiT USP | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--size` | `1280*720` | I2V-14B single-GPU inference; aspect ratio follows original input image | [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P] |
| `--prompt_extend_model` | `Qwen/Qwen2.5-VL-7B-Instruct` | Local prompt extension for I2V-14B | [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P] |
| `--prompt_extend_method` | `dashscope` | Remote prompt extension for I2V-14B | [https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P] |
| `--prompt_extend_model` | `qwen-plus` | Prompt extension for text-to-video tasks | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `--prompt_extend_model` | `qwen-vl-max` | Prompt extension for image-to-video tasks | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |
| `DASH_API_URL` | `https://dashscope-intl.aliyuncs.com/api/v1` | Environment variable for Alibaba Cloud international site | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B] |

Not in sources: Sampler/scheduler name (e.g., Euler, DPM++).
Not in sources: Specific frame count or FPS values for generation.
Not in sources: CFG/guidance scale values for 14B models.
Not in sources: Sample shift values for 14B models.
Not in sources: Specific node settings for ComfyUI sampler nodes (e.g., `WanVideoSampler_F2`).
> UNVERIFIED: name not in evidence:  | Recommended for T2V-1.3B; adjustable within range of 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
