# RECIPES - 04-Chroma

| Setting | Value | Outcome / Notes | Source |
| :--- | :--- | :--- | :--- |
| `num_inference_steps` | `40` | Standard denoising steps for text-to-image generation. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `guidance_scale` | `3.0` | Classifier-free guidance scale. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `torch_dtype` | `bfloat16` | Data type for computation in the standard `diffusers` example. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `torch_dtype` | `float16` | Data type for computation in the gemlite quantized inference example. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `generator` | `torch.Generator("cpu").manual_seed(433)` | Seed for reproducibility. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `num_images_per_prompt` | `1` | Number of images generated per prompt. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `negative_prompt` | "low quality, ugly, unfinished, out of focus, deformed, disfigure, blurry, smudged, restricted palette, flat colors" | Text description of elements to avoid. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `processor` | `gemlite.helper.A8W8_int8_dynamic` | Quantization processor for gemlite inference. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `processor` | `gemlite.helper.A8W8_fp8_dynamic` | Alternative quantization processor for gemlite inference (commented out in example). | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `processor` | `gemlite.helper.A16W4_MXFP` | Alternative quantization processor for gemlite inference (commented out in example). | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `device` | `cuda:0` | Target device for gemlite quantized inference. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `torch.compile` | `fullgraph=True` | Compilation mode for transformer and VAE forward passes in gemlite example. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `enable_model_cpu_offload` | Enabled | Offloads model to CPU to manage memory in standard `diffusers` example. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `UNETLoader` | `Chroma1-HD.safetensors` or `Chroma1-HD-fp8mixed.safetensors` | Loads the diffusion model in ComfyUI workflows. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `CLIPLoader` | `t5xxl_fp16.safetensors` | Loads the T5 XXL text encoder in ComfyUI workflows. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `VAEDecode` | `ae.safetensors` | Decodes latent representations into images using FLUX VAE. | [lodestones/Chroma1-HD README](https://huggingface.co/lodestones/Chroma1-HD) |
| `FluxGuidance` | `3.0` | Sets guidance scale in ComfyUI workflow. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `BasicScheduler` | `40` | Sets number of steps in ComfyUI workflow. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `EmptyLatentImage` | Not specified | Creates the latent space for sampling. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `KSampler` | Not specified | Performs the sampling process. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `ChromaRadianceOptions` | Not specified | Configures radiance options; specific BOOLEAN, FLOAT, and INT values are not stated. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |
| `EmptyChromaRadianceLatentImage` | Not specified | Creates latent space for radiance-specific workflows. | [WORKFLOW_PLAN.md](WORKFLOW_PLAN.md) |

Not in sources: Resolution (width/height)
Not in sources: Frames
Not in sources: FPS
Not in sources: Shift values
Not in sources: Strength values
Not in sources: Specific sampler name (e.g., Euler, DPM++); `KSampler` is the node, but the internal sampler algorithm is not specified in the provided text.
Not in sources: Specific scheduler name (e.g., Linear, Karras); `BasicScheduler` is the node, but the internal scheduler algorithm is not specified in the provided text.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 49716 chars.
