# PLAYBOOK.md: 09-Flux.1-dev-schnell-Kontext-Fill

## Prompt structure

*   **Natural Language:** Use natural language descriptions rather than tag-based prompts, as this model family falls under the LLM-encoder category (FLUX). [CHARACTER_BUILDER_MODELS.md]
*   **SFW Prefix:** Always include the model's SFW prefix in the prompt. [CHARACTER_BUILDER_MODELS.md]
*   **Trigger Words:** Include the model's specific rules-page trigger words. [CHARACTER_BUILDER_MODELS.md]
*   **Inpainting Specifics:** When using the Fill/Inpaint mode, describe **only the new content** to be generated within the masked area. [image-dfserve-modes.md]
*   **Head Framing (Character Builder):** For head and expression shots, name only the garments above the waist. [CHARACTER_BUILDER_MODELS.md]
*   **Body Framing (Character Builder):** For body shots, keep the full outfit description. [CHARACTER_BUILDER_MODELS.md]

## Words and phrasing that work

*   **"Clean, front-facing, evenly lit head-and-shoulders portrait":** This is the standard shot description for anchor generation. [CHARACTER_BUILDER_MODELS.md]
*   **"Plain light grey background":** Use this specific background description for anchor shots. [CHARACTER_BUILDER_MODELS.md]
*   **"Neutral expression":** Use this for anchor shots to ensure a consistent baseline. [CHARACTER_BUILDER_MODELS.md]
*   **IDENTITY_EDIT wording:** When performing reference edits (e.g., in the character builder process), use `IDENTITY_EDIT` wording and avoid re-describing the person. [CHARACTER_BUILDER_MODELS.md]
*   **Stronger clothing:** If an image check fails, a retry with "stronger clothing" phrasing is the documented recovery step. [CHARACTER_BUILDER_MODELS.md]

## Settings that worked

*   **FluxGuidance:** 30 [image-dfserve-modes.md]
*   **Steps:** 28 [image-dfserve-modes.md]
*   **Sampler:** euler [image-dfserve-modes.md]
*   **Scheduler:** normal [image-dfserve-modes.md]
*   **CFG:** 1 [image-dfserve-modes.md]
*   **DifferentialDiffusion:** Enabled [image-dfserve-modes.md]
*   **InpaintModelConditioning:** `noise_mask` off [image-dfserve-modes.md]
*   **SetLatentNoiseMask:** Enabled [image-dfserve-modes.md]
*   **Resolution:** ~1 MP in the input's shape (do not square to 1024²). [image-dfserve-modes.md]
*   **Character Builder Candidates:** Default is 2 (selectable 1, 3, 4). [CHARACTER_BUILDER_MODELS.md]
*   **Character Builder Edits:** Qwen-Image 2.1 bf16, 40 steps, CFG 1, resolution 0 (follows anchor). [CHARACTER_BUILDER_MODELS.md]
*   **Head Framing Thresholds:** `HEAD_MIN` 0.25, `HEAD_TARGET` 0.36. [CHARACTER_BUILDER_MODELS.md]

## Processes built on it

*   **Character Builder Anchor:** This model can serve as an anchor for character sheets. The process involves generating front headshots on a locked seed, running text guards, and rendering through the Image tab tool or `ckpt_generate`. [CHARACTER_BUILDER_MODELS.md]
*   **Inpainting/Fill:** Routed via `tools/image_fill_tools.py` on ComfyUI. The entry `df:flux_fill:inpaint` maps to this engine. [image-dfserve-modes.md]
*   **Text-to-Image (SVDQuant variant):** The `df:flux_svdquant:t2i` entry routes to `ckpt:flux1_svdq_fp4_r32` using Nunchaku `NunchakuFluxDiTLoader`. Note: This is a specific quantized variant of FLUX.1-dev, not necessarily the "schnell" variant, but shares the FLUX.1-dev base architecture mentioned in the file names. [image-dfserve-modes.md]
*   **Chat Generation:** Available via `df_generate` in the chatbox Mode dropdown (listed as `flux_svdquant` or `flux_fill` depending on the specific routed entry). [image-dfserve-modes.md]

## What to avoid

**Not in notes:** Specific prompt examples for non-character, non-inpainting general text-to-image generation.
**Not in notes:** Specific VRAM requirements for the "schnell" variant specifically (only general "big-model lock over 20 GB" for capability-run builders is mentioned).
**Not in notes:** Whether the "schnell" transformer weights are currently available on disk (the notes state `df:flux_schnell:t2i` is **unavailable** because the transformer was never downloaded, only text encoders + VAE are in the HF cache). [image-dfserve-modes.md]
