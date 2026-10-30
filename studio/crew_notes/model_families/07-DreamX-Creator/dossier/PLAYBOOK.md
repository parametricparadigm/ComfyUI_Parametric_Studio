# PLAYBOOK.md: 07-DreamX-Creator

## Prompt structure

*   **Not in notes:** The provided documents do not contain specific prompt structure guidelines, syntax rules, or template examples for the 07-DreamX-Creator model family.
*   The only prompt structure details provided in the source text are for **LTX-2.5** (a different model family), which recommends a "one flowing present-tense paragraph" containing six elements: shot, scene, action, characters, camera, and audio [LTX25_DREAMX_GUIDE.md].
*   The 07-DreamX-Creator is described as an "I2V + joint audio, 2K refiner" model [VIDEO_MODELS_AUDIT_2026-10-06.md], but no specific prompting instructions are associated with it in the notes.

## Words and phrasing that work

*   **Not in notes:** There are no specific keywords, positive/negative prompt examples, or phrasing strategies documented for 07-DreamX-Creator.
*   The notes provide phrasing advice only for **LTX-2.5**, such as using "objective description" (e.g., "eyebrows angle downward" instead of "sad") and avoiding phrases like "The scene opens" [LTX25_DREAMX_GUIDE.md].
*   For 07-DreamX-Creator, the only related textual context is that it is part of the "DreamX-Creator 1.0" family which is "READY / PROVEN (smoke 10-06)" [VIDEO_MODELS_AUDIT_2026-10-06.md].

## Settings that worked

*   **Not in notes:** No specific inference settings (such as step counts, CFG scales, samplers, or resolution constraints) are documented for 07-DreamX-Creator.
*   The notes confirm the model is **READY / PROVEN** based on a smoke test on 2026-10-06 [VIDEO_MODELS_AUDIT_2026-10-06.md].
*   The model size is listed as **50.5 G** with precisions of **fp32 / bf16 / .pt** [VIDEO_MODELS_AUDIT_2026-10-06.md].
*   Specific settings provided in the notes (e.g., euler_ancestral, specific sigma schedules, LTXVDualCFGGuider) apply exclusively to **LTX-2.5** [LTX25_DREAMX_GUIDE.md] and are not stated to apply to DreamX-Creator.

## Processes built on it

## What to avoid

*   **Not in notes:** There are no specific warnings, failure modes, or "do not use" instructions for 07-DreamX-Creator.
*   The notes do not list any specific technical limitations or artifacts for this model, unlike **LTX-2.5**, which has documented weaknesses such as "face drift on a talking person, push-in instead of orbit, slight glass warping" [LTX25_DREAMX_GUIDE.md].
*   The model is not listed in the "What it lacks" section of the subscription creator notes, which lists missing features like "batch 'set' jobs" or "PPV preview/blur maker" generally for the studio, not specifically for this model [04_SUBSCRIPTION_CREATORS.md].
