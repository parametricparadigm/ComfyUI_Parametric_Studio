# RECIPES - 28-Wan-version-not-stated

| Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- |
| `num_inference_steps` | `10` | Default parameter for Wan2.1-T2V-14B inference | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--sample_guide_scale` | `6` | Recommended for `T2V-1.3B` model | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--sample_shift` | `8` | Used in example command for `T2V-1.3B`; adjustable within range of `8` to `12` based on performance | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--size` | `1280*720` | Defines video resolution for 720P generation | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--size` | `832*480` | Defines video resolution for 480P generation | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--offload_model` | `True` | Reduces GPU memory usage by offloading model weights | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--t5_cpu` | (flag) | Moves the T5 text encoder to CPU to save VRAM | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--convert_model_dtype` | (flag) | Converts model data types to reduce memory footprint | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) |
| Resolution | `480P` | Supported by Wan2.1 T2V-14B, I2V-14B-480P, Wan2.2 T2V-A14B, I2V-A14B | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| Resolution | `720P` | Supported by Wan2.1 T2V-14B, I2V-14B-720P, Wan2.2 T2V-A14B, I2V-A14B, TI2V-5B | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| FPS | `24fps` | Supported by Wan2.2-TI2V-5B at 720P | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) |
| Duration | `5 seconds` | Typical output duration for Wan2.1 T2V-14B and Wan2.2 T2V-A14B | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| VAE Compression | `16×16×4` | Compression ratio for Wan2.2-VAE used in TI2V-5B | [https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) |
| `--ulysses_size` | `8` | Parameter for multi-GPU inference using FSDP + xDiT USP or DeepSpeed Ulysses | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |
| `--nproc_per_node` | `8` | Number of processes for multi-GPU inference | [https://huggingface.co/Wan-AI/Wan2.1-T2V-14B](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B) |

Not in sources: Specific sampler or scheduler names (e.g., Euler, DPM++).
Not in sources: Specific CFG/guidance scale values for Wan2.2 models.
Not in sources: Specific inference steps for Wan2.2 models.
Not in sources: Specific FPS for Wan2.1 models.
Not in sources: Specific duration for Wan2.2 TI2V-5B.
> UNVERIFIED: name not in evidence: ; adjustable within range of ; name not in evidence:  | Used in example command for ; name not in evidence:  | Recommended for 

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
