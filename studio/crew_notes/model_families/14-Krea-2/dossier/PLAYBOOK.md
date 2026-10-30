# PLAYBOOK.md: 14-Krea-2

## Prompt structure

## Words and phrasing that work

## Settings that worked

*   **Model File:** krea2/krea2_turbo_bf16.safetensors [earlier-studio/docs/processes/image-krea2-default.md].
*   **Precision:** Load with weight_dtype fp8_e4m3fn (W8A8). This was allowlisted after A/B testing showed same quality as bf16 but lower VRAM [earlier-studio/docs/processes/image-krea2-default.md].
*   **Text Encoder:** qwen3vl_4b (type krea2) [earlier-studio/docs/processes/image-krea2-default.md].
*   **VAE:** qwen_image_vae [earlier-studio/docs/processes/image-krea2-default.md].
*   **Steps:** 8 [earlier-studio/docs/processes/image-krea2-default.md].
*   **CFG:** 1 [earlier-studio/docs/processes/image-krea2-default.md].
*   **Sampler:** euler [earlier-studio/docs/processes/image-krea2-default.md].
*   **Scheduler:** simple [earlier-studio/docs/processes/image-krea2-default.md].
*   **Negative Prompt:** None (empty) [earlier-studio/docs/processes/image-krea2-default.md].
*   **Default Seed:** 710001 [earlier-studio/docs/processes/image-krea2-default.md].
*   **Resolution:** Approximately 1 MP on a 32 grid. Examples: 1:1 (1024x1024), 3:4 (896x1184), 9:16 (768x1344), 16:9 (1344x768) [earlier-studio/docs/processes/image-krea2-default.md].
*   **VRAM Usage:** ~22.0-22.7 GB peak at fp8 [earlier-studio/docs/processes/image-krea2-default.md].
*   **Speed:** ~2.3-2.4 seconds per image warm [earlier-studio/docs/processes/image-krea2-default.md].
*   **Not in notes:** Specific settings for "high" vs "fast" thinking modes (these are mentioned for Krea 3, not Krea 2).

## Processes built on it

## What to avoid
