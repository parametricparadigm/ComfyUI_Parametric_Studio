# PLAYBOOK.md for 23-SD3-SD3.5

## Prompt structure
Not in notes: The provided documents do not contain specific instructions on prompt structure, syntax, or formatting for the SD3/SD3.5 model family.

## Words and phrasing that work
Not in notes: The provided documents do not list specific keywords, phrases, or stylistic modifiers that have been tested or confirmed to work well for the SD3/SD3.5 model family.

## What to avoid
*   **Assuming Cloud-Bound Availability:** Do not assume that community merges or finetunes associated with the broader SD ecosystem are available, as many are "CLOUD-BOUND" and being moved to Google Drive, which may cause them to stop loading in ComfyUI until manually pulled back [MODELS_WEIGHTS_HANDOFF_2026-10-27.md].
*   **Using Quantized Weights for Merging:** If performing any model merging operations involving SD3/SD3.5 weights, avoid feeding scaled-FP8/NVFP4 weights to stock merge nodes; merges must use unquantized bf16/fp16 weights only [COMFY_BIBLE.md].
*   **Blind Git Pulls:** Avoid blind `git pull` commands on ComfyUI core, as local patches required for specific subsystems (like VAE decode) may be dropped, causing failures [COMFY_BIBLE.md].
