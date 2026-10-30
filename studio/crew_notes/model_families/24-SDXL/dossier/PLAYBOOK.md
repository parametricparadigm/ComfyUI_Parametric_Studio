# PLAYBOOK.md: 24-SDXL

## Prompt structure

## Words and phrasing that work

*   **Standard Portrait Tags:** Use the PORTRAIT_TAGS defined in the codebase for consistent character generation. [CHARACTER_BUILDER_MODELS.md]
*   **Head Framing Wording:** For head and expression shots, name only the garments above the waist and include HEAD_FRAMING wording. [CHARACTER_BUILDER_MODELS.md]
*   **Identity Edit Wording:** When performing edits, use IDENTITY_EDIT wording and avoid re-describing the person. [CHARACTER_BUILDER_MODELS.md]
*   **Not in notes:** Specific positive trigger words unique to the "24-SDXL" model file are not listed in the provided audit or character builder notes.

## Settings that worked

*   **Resolution:** Use a size whose shape is closest to 3:4 aspect ratio. For SDXL, this is usually **832x1216** (portrait). [CHARACTER_BUILDER_MODELS.md]
*   **Hires Fix:** If using SD 1.5 (for comparison), a 2x hires fix is used, but for SDXL, the 832x1216 size is the tested standard. [CHARACTER_BUILDER_MODELS.md]
*   **Sampling Parameters:** Use the model's tested values for steps, CFG, sampler, scheduler, shift, and hires. These are sourced from the capability-run models.json main arm or finetunes.job_settings. [CHARACTER_BUILDER_MODELS.md]
*   **Candidates:** The default number of candidates for anchor generation is **2** (selectable 1, 3, or 4). [CHARACTER_BUILDER_MODELS.md]
*   **Not in notes:** Specific numerical values for Steps, CFG Scale, Sampler Name, or Scheduler for the "24-SDXL" model are not explicitly listed in the provided text; the notes state these are read from models.json or finetunes.job_settings at runtime.

## Processes built on it

## What to avoid
