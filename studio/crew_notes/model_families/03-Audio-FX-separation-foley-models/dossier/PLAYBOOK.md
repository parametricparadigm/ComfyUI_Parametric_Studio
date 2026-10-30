# PLAYBOOK.md: 03-Audio-FX-separation-foley-models

## Prompt structure

Not in notes: The provided documents do not contain specific prompt templates, text-to-audio prompt syntax, or input field definitions for the 03-Audio-FX-separation-foley-models family. The notes focus on file locations, disk usage, and loading parameters for specific audio models (e.g., ControlFoley, YuE2, Stable Audio), but do not define a general "prompt structure" for this specific family identifier.

## Words and phrasing that work

Not in notes: The provided documents do not list specific keywords, tags, or phrasing strategies that improve output quality for this model family. While the notes mention specific model capabilities (e.g., "video/text/reference-audio -> 44.1 kHz foley" for ControlFoley [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]), they do not provide guidance on effective prompt wording.

## Settings that worked

*   **YuE2 3B (Music/Audio):**
    *   **Weight Dtype:** bf16 [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
    *   **Loader:** CheckpointLoaderSimple (core yue2) [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
    *   **Slot Mapping:** CLIP slot = AR planner, MODEL slot = NAR acoustic decoder, VAE = YuE2-Vae (in checkpoint) [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]

## Processes built on it

*   **ControlFoley Generation:**
    *   Uses video, text, or reference audio to generate 44.1 kHz foley audio. [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
    *   Requires the comfyui-controlfoley-official custom node. [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
    *   Non-commercial license applies. [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]

## What to avoid

*   **Ignoring License Restrictions:**
    *   ControlFoley is non-commercial; avoid using it in commercial pipelines. [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
    *   Some voice datasets (e.g., kyutai_tts_voices) have specific licenses (CC-BY-NC-4.0, CC0, CC-BY-4.0); avoid mixing them incorrectly. [MNT_FAST_STALE_30D_2026-10-27.md]

*   **Using Unverified Duplicates:**
    *   Avoid assuming files with the same size are duplicates; most "same size" pairs are different weights (e.g., Wan HIGH/LOW halves). Verify with sha256 before deleting. [mnt-fast-cleanup-plan-2026-10-19.md]

*   **Overlooking Disk Space Impact:**
    *   Audio models contribute significantly to disk usage (628.2 GB). Be mindful of storage limits when adding new audio models or generating large outputs. [MODEL_WEIGHTS_TAXONOMY_2026-10-28.md]
