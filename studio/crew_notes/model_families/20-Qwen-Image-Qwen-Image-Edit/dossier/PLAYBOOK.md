# PLAYBOOK.md: 20-Qwen-Image-Qwen-Image-Edit

## Prompt structure

*   **Natural Language Instructions:** For `qwen21:edit`, prompts should be written as natural language instructions describing the desired change (e.g., "make it night", "remove the sign") rather than tag-based lists [earlier-studio/docs/processes/image-qwen21.md].
*   **Identity Preservation Wording:** When used for character consistency or pose changes, the prompt should focus on the specific edit instruction without re-describing the person's identity, as the model relies on the reference image for identity [earlier-studio/docs/processes/pose-set-2026-10-17.md].
*   **Enhancement:** In the studio UI, prompts for `qwen21:edit` are enhanced by default (indicated by the ✨ icon), which applies camera-real rules if the Realism chip is active, though the Realism chip is currently opt-in and off by default for t2i, with edit prompts generally going through the standard enhancement path [earlier-studio/docs/processes/image-qwen21.md].
*   **Multi-Reference Capability:** The model supports up to 10 reference images to preserve identity for people and products, though the standard edit entry typically uses a single `image` slot for the source [earlier-studio/docs/processes/pose-set-2026-10-17.md].
*   **Not in notes:** Specific prompt templates or "magic words" for complex multi-object edits are not provided; the notes emphasize that the model "keeps the INPUT's composition," so prompts must be precise about what *changes* rather than what stays the same [earlier-studio/docs/processes/pose-set-2026-10-17.md].

## Words and phrasing that work

*   **Instructional Phrasing:** Phrases like "make it night" or "remove the sign" are cited as effective examples of "say the change" edits [earlier-studio/docs/processes/image-qwen21.md].
*   **Pose/Angle Changes:** While the model card does not explicitly claim pose control, using it for pose and angle edits has been measured to maintain identity (ArcFace mean 0.751), suggesting that direct instructions to change pose or angle are effective when paired with a strong reference [earlier-studio/docs/processes/pose-set-2026-10-17.md].
*   **Outfit Swaps:** For `qwen21:outfit` (which uses the same underlying engine capabilities), the prompt can be empty or raw because the "proven instruction is used" internally, but for general edits, clear descriptive language is preferred [earlier-studio/docs/processes/image-qwen21.md].
*   **Not in notes:** There is no list of specific "trigger words" or "positive/negative prompt keywords" unique to Qwen-Image-Edit in the provided documents; the notes focus on the model's behavior with natural language instructions [earlier-studio/docs/processes/image-qwen21.md].

## Settings that worked

## Processes built on it

*   **Character Builder (Identity Edits):** Qwen-Image 2.1 edit is the primary engine for the character sheet process. It performs 9 reference edits (headshots, full-body, expressions) of an anchor image. It achieved a mean ArcFace consistency score of 0.751 with 0 weak shots in testing [earlier-studio/docs/processes/pose-set-2026-10-17.md].
*   **Pose Generation:** It is the primary engine for generating 10 different poses of the same person from a single source image, maintaining outfit, lighting, and camera look [earlier-studio/docs/processes/pose-set-2026-10-17.md].
*   **Outfit Swap:** The `qwen21:outfit` task dresses a person in Image 1 with the outfit from Image 2. This uses a specific stack: a task LoRA (outfit-swap) at 1.0, followed by a Turbo LoRA at 1.0, with 8 steps and CFG 1 [earlier-studio/docs/processes/image-qwen21.md].
*   **Fusion/Blending:** The `qwen21:fusion` task blends a pasted object into a photo. It is noted as the only working blend on the box (Klein Fusion fails). Inputs should be pre-scaled to 1.8 MP [earlier-studio/docs/processes/image-qwen21.md].
*   **Fallback Strategy:** If Qwen-Image 2.1 is unavailable or fails, FLUX.3 Klein 9B edit is the designated fallback, though it has lower consistency (ArcFace 0.714) and is slower [earlier-studio/docs/processes/pose-set-2026-10-17.md].

## What to avoid
