# RECIPES - 13-Kandinsky-OmniGen-Ovis-HunyuanImage

| Model / Variant | Setting | Value | Outcome / Note | Source |
| :--- | :--- | :--- | :--- | :--- |
| Kandinsky 5.0 T2I Lite | `num_inference_steps` | 50 | Example setting for text-to-image generation | [MODEL.md] |
| Kandinsky 5.0 T2I Lite | `guidance_scale` | 3.5 | Example setting for text-to-image generation | [MODEL.md] |
| Kandinsky 5.0 T2I Lite | `height` | 1024 | Input dimension for generation | [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md] |
| Kandinsky 5.0 T2I Lite | `width` | 1024 | Input dimension for generation | [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md] |
| Kandinsky 5.0 T2I Lite | `negative_prompt` | "" | Empty string used in usage example | [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md] |
| Kandinsky 5.0 T2I Lite | `dtype` | `torch.bfloat16` | Precision for pipeline execution | [PUBLIC README https://huggingface.co/kandinskylab/Kandinsky-5.0-T2I-Lite-sft-Diffusers/raw/main/README.md] |
| Kandinsky 2.2 | `decoder_steps` | 50 | Example setting for text-to-image generation | [MODEL.md] |
| Kandinsky 2.2 | `guidance_scale` | 4 | Example setting for text-to-image generation | [MODEL.md] |
| Kandinsky 2.2 | `prior_cf_scale` | 4 | Example setting for prior conditioning | [MODEL.md] |
| Kandinsky 2.2 | `prior_steps` | 5 | Example setting for prior steps | [MODEL.md] |
| Kandinsky 2.2 | `sampler` | 'p_sampler' | Example sampler used | [MODEL.md] |
| Kandinsky 2.2 | `h` | 1024 | Height for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.2 | `w` | 768 | Width for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `num_steps` | 100 | Steps for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `guidance_scale` | 4 | Guidance scale for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `h` | 768 | Height for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `w` | 768 | Width for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `sampler` | 'p_sampler' | Sampler used for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_cf_scale` | 4 | Prior classifier-free scale | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_steps` | "5" | Prior steps for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `num_steps` | 150 | Steps for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `guidance_scale` | 5 | Guidance scale for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `h` | 768 | Height for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `w` | 768 | Width for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `sampler` | 'p_sampler' | Sampler used for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_cf_scale` | 4 | Prior classifier-free scale for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_steps` | "5" | Prior steps for image fusion | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `num_steps` | 150 | Steps for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `guidance_scale` | 5 | Guidance scale for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `h` | 768 | Height for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `w` | 768 | Width for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `sampler` | 'p_sampler' | Sampler used for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_cf_scale` | 4 | Prior classifier-free scale for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.1 | `prior_steps` | "5" | Prior steps for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `num_steps` | 75 | Steps for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `denoised_type` | 'dynamic_threshold' | Denoising type used | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `dynamic_threshold_v` | 99.5 | Dynamic threshold value | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `sampler` | 'ddim_sampler' | Sampler used for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `ddim_eta` | 0.05 | DDIM eta value | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `guidance_scale` | 10 | Guidance scale for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `h` | 512 | Height for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `w` | 512 | Width for text-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `num_steps` | 50 | Steps for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `denoised_type` | 'dynamic_threshold' | Denoising type used for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `dynamic_threshold_v` | 99.5 | Dynamic threshold value for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `sampler` | 'ddim_sampler' | Sampler used for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `ddim_eta` | 0.05 | DDIM eta value for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `guidance_scale` | 10 | Guidance scale for inpainting | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `strength` | 0.8 | Strength for image-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `num_steps` | 50 | Steps for image-to-image generation | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `denoised_type` | 'dynamic_threshold' | Denoising type used for image-to-image | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `dynamic_threshold_v` | 99.5 | Dynamic threshold value for image-to-image | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `sampler` | 'ddim_sampler' | Sampler used for image-to-image | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `ddim_eta` | 0.05 | DDIM eta value for image-to-image | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| Kandinsky 2.0 | `guidance_scale` | 10 | Guidance scale for image-to-image | [PUBLIC README https://raw.githubusercontent.com/ai-forever/Kandinsky-2/HEAD/README.md] |
| KVAE-Video 2.0 t4s16 | `seg_len` | 16 | Segment length for video encoding/decoding | [MODEL.md] |
| KVAE-Video 2.0 t4s16 | `seg_len` | 16 | Segment length for video encoding/decoding in inference example | [PUBLIC README https://huggingface.co/kandinskylab/KVAE-3D-2.0-t4s16/raw/main/README.md] |
| Kandinsky 5.0 Video Pro | `NFE` | 100 | Number of Function Evaluations for 5s and 10s HD/SD models | [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md] |
| Kandinsky 5.0 Video Pro | `video duration` | 5s | Duration for specific checkpoints | [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md] |
| Kandinsky 5.0 Video Pro | `video duration` | 10s | Duration for specific checkpoints | [PUBLIC README https://raw.githubusercontent.com/kandinskylab/kandinsky-5/HEAD/README.md] |

Not in sources: Specific sampler/scheduler names for Kandinsky 5.0 T2I Lite (only Flow Matching architecture mentioned).
Not in sources: Specific sampler/scheduler names for Ovis-Image.
Not in sources: Resolution/frames/fps for Ovis-Image.
Not in sources: Shift/strength values for Kandinsky 5.0 T2I Lite.
Not in sources: Specific local file paths for VAE and Text Encoder for Kandinsky 5.0 T2I Lite.
Not in sources: Specific local file path for VAE for Ovis-Image.
Not in sources: Concrete settings for Kandinsky 5.0 I2V or T2V Lite/Pro beyond NFE and duration in the Pro table.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
