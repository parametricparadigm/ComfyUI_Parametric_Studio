# PLAYBOOK.md: 29-Wan-2.1

## Prompt structure
Not in notes: The provided documents do not contain specific prompt text, syntax rules, or structural templates (e.g., negative prompts, tag ordering) for the Wan 2.1 model family. The notes focus on model weights, LoRA configurations, sampler settings, and hardware metrics rather than prompt engineering. [03_loras.md] [LORA_RETEST_2026-10-09_wannew.md] [BEST_OPTIONS_2026-10-10/wan.md] [LORA_RETEST_2026-10-09.md] [VIDEO_MODELS_AUDIT_2026-10-06.md]

## Words and phrasing that work
Not in notes: The provided documents do not list specific keywords, phrases, or semantic triggers that improve output quality for Wan 2.1. The notes reference "prompts" in the context of test runs (e.g., "all 3 prompts") but do not disclose the content of those prompts or any linguistic patterns that yield better results. [BEST_OPTIONS_2026-10-10/wan.md] [LORA_RETEST_2026-10-09_wannew.md]

## Processes built on it
*   **Model Availability:** The following Wan 2.1 base models are confirmed on disk and ready: `wan2.1_i2v_720p_14B_bf16`, `wan2.1_flf2v_720p_14B_fp16`, and `wan2.1_t2v_14B_bf16`. [VIDEO_MODELS_AUDIT_2026-10-06.md]
*   **LoRA Integration:** There are 4 LoRA files specifically for the Wan 2.1 family (including SCAIL/Animate), totaling 5.1 GB. These are currently marked as **UNTESTED** (0 judged, 0 loads-only). [03_loras.md]
*   **SCAIL-2 Integration:** SCAIL-2 (based on Wan2.1 14B) is complete with relight and DPO LoRAs landed in `loras/wan/2.1/`. It is used for pose V2V / animate tasks. [VIDEO_MODELS_AUDIT_2026-10-06.md]
*   **DreamID-V:** A video face swap model for Wan2.1 exists but is currently **ORPHAN** status because the wrapper is disabled and T5 is missing. [VIDEO_MODELS_AUDIT_2026-10-06.md]

## What to avoid
*   **No-Accelerator Runs:** Do not run Wan 2.1 without the lightx2v accelerator; it was stopped in previous tests as **too slow**. [BEST_OPTIONS_2026-10-10/wan.md]
*   **Three-Sampler Recipe:** Do not use the "three-sampler" recipe (2 base steps at cfg 3.5 + 2+2 lightx2v) for I2V tasks. It caused halo rings, over-exposure, and smears. While it works for T2V, it is softer than the standard 4-step stack. [BEST_OPTIONS_2026-10-10/wan.md]
*   **Missing Components:** Avoid relying on Wan 2.1 VACE, Fun, SteadyDancer, UniAnimate, Bernini base, or TI2V-5B (Comfy) as these are currently **ABSENT** from the disk. [VIDEO_MODELS_AUDIT_2026-10-06.md]
*   **DreamID-V:** Do not attempt to use DreamID-V for face swapping until the wrapper is enabled and T5 is installed, as it is currently broken/orphaned. [VIDEO_MODELS_AUDIT_2026-10-06.md]
