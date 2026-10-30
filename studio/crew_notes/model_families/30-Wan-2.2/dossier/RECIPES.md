# RECIPES - 30-Wan-2.2

| Setting | Value / Configuration | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| **Resolution** | `1280*720` | Generates 5s videos at 720P resolution for T2V-A14B and I2V-A14B. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Resolution** | `480P` | Supported resolution for T2V-A14B and I2V-A14B models. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Resolution** | `720P` | Supported resolution for TI2V-5B model. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Frame Rate** | `24fps` | Frame rate for TI2V-5B model generation. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Duration** | `5s` | Video duration for T2V-A14B generation. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Sampler/Scheduler** | `WASWan22MoESamplerCtx` | Node used for MoE sampling in ComfyUI workflows for T2V and I2V. | [WORKFLOW_PLAN.md] |
| **Sampler/Scheduler** | `KSamplerAdvanced` | Node used for sampling in ComfyUI workflow for Animate variant. | [WORKFLOW_PLAN.md] |
| **Steps** | Not in sources: Specific number of sampling steps (e.g., 30, 50) is not explicitly defined in the provided evidence, though `INT` inputs for steps are referenced in workflow plans. | [WORKFLOW_PLAN.md] |
| **CFG/Guidance** | Not in sources: Specific CFG or guidance scale values are not provided in the evidence. | [WORKFLOW_PLAN.md] |
| **Shift/Strength** | Not in sources: Specific shift or strength values are not provided in the evidence. | [WORKFLOW_PLAN.md] |
| **Offloading** | `--offload_model True` | Reduces GPU memory usage; allows running on GPU with at least 80GB VRAM. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Precision** | `--convert_model_dtype` | Reduces GPU memory usage. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Precision** | `--t5_cpu` | Reduces GPU memory usage by moving T5 to CPU. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Multi-GPU** | `--dit_fsdp --t5_fsdp --ulysses_size 8` | Accelerates inference using PyTorch FSDP and DeepSpeed Ulysses across 8 GPUs. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Prompt Extension** | `--use_prompt_extend --prompt_extend_method 'dashscope'` | Enriches prompt details to enhance video quality using Dashscope API. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Prompt Extension** | `--prompt_extend_model` | Parameter to modify the model used for prompt extension (e.g., `qwen-plus`). | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **VAE Compression** | `16×16×4` | Compression ratio of the Wan2.2-VAE used in TI2V-5B, enabling efficient 720P generation. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Hardware** | `80GB VRAM` | Minimum VRAM required for single-GPU inference of A14B models without offloading. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |
| **Hardware** | `4090` | Consumer-grade GPU capable of running TI2V-5B model. | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B/raw/main/README.md] |

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
