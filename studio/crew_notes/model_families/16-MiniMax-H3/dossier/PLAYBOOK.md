# PLAYBOOK.md: 16-MiniMax-H3

## Prompt structure

*   **Six-Section Prompt:** For Ref2VA (identity from image refs), use a six-section prompt structure. [MINIMAX_H3_CAPABILITIES.md]
*   **Picture Tags:** Use `<Picture i>` tags to reference specific image inputs in the prompt. [MINIMAX_H3_CAPABILITIES.md]
*   **Video Tags:** Use `<Video k>` tags to reference specific video inputs. [MINIMAX_H3_CAPABILITIES.md]
*   **Audio Tags:** Use `<Audio j>` tags to reference specific audio inputs. [MINIMAX_H3_CAPABILITIES.md]
*   **Audio Retention Syntax:** For reference audio, use the syntax `retention: <Audio 1>: reference - timbre and delivery only` or `fully_copy`. [MINIMAX_H3_CAPABILITIES.md]
*   **Official Bakery Prompt:** For T2VA (text-to-video-audio), the "official bakery prompt" is a proven structure that supports timed cuts and sound/music lanes. [MINIMAX_H3_CAPABILITIES.md]
*   **Base Prompt Function:** For I2VA and L2VA, use the helper function `pp.h3prompts.base_prompt("i2va")` or `pp.h3prompts.base_prompt("l2va")`. [MINIMAX_H3_CAPABILITIES.md]
*   **Meridian Frozen Prompt:** When using the Viggle/Meridian re-camera LoRA, use the "Meridian Frozen Prompt" node. [H3_FINETUNES_SURVEY_2026-10-09.md]
*   **Not in notes:** Specific text content for the "six-section prompt" or the "official bakery prompt" is not provided in the source documents.

## Words and phrasing that work

*   **Identity Priority:** Prompt styling outranks reference images in determining the final output. [MINIMAX_H3_CAPABILITIES.md]
*   **Location First:** When using multiple reference images, place the location still as the first image (`Picture 1`) because H3 opens on Picture 1. [MINIMAX_H3_CAPABILITIES.md]
*   **Action Description:** For L2VA (last frame), describing a "walk-in-and-sit" action was proven to work effectively. [MINIMAX_H3_CAPABILITIES.md]
*   **Not in notes:** Specific positive or negative prompt keywords (e.g., "high quality," "4k," "no blur") are not listed in the provided notes.

## Settings that worked

*   **Ref2VA (Identity):**
    *   **Steps:** 8 steps (Turbo). [MINIMAX_H3_CAPABILITIES.md]
    *   **Sampler:** sage3. [MINIMAX_H3_CAPABILITIES.md]
    *   **Resolution:** 576x1024. [MINIMAX_H3_CAPABILITIES.md]
    *   **Frames:** 124, 294, or 362 frames. [MINIMAX_H3_CAPABILITIES.md]
    *   **Checkpoint:** Ref2VA checkpoint (nvfp4 or int8). [MINIMAX_H3_CAPABILITIES.md]
*   **I2VA (First Frame):**
    *   **Model:** `MiniMax_H3_FL2VA_pruned_nvfp4`. [MINIMAX_H3_CAPABILITIES.md]
    *   **Sampler:** Turbo v4 + TurboSampler. [MINIMAX_H3_CAPABILITIES.md]
    *   **Steps:** 4 steps. [MINIMAX_H3_CAPABILITIES.md]
    *   **Resolution:** 1344x768. [MINIMAX_H3_CAPABILITIES.md]
    *   **Frames:** 124 frames. [MINIMAX_H3_CAPABILITIES.md]
*   **L2VA (Last Frame):**
    *   **Model:** Same graph as I2VA. [MINIMAX_H3_CAPABILITIES.md]
    *   **Frames:** 124 frames (implied by "Clip ends on the still... 43 s"). [MINIMAX_H3_CAPABILITIES.md]
*   **FL2VA (First + Last Frame):**
    *   **Model:** `MiniMax_H3_FL2VA_pruned_nvfp4`. [MINIMAX_H3_CAPABILITIES.md]
    *   **Frames:** 192 frames. [MINIMAX_H3_CAPABILITIES.md]
*   **Viggle/Meridian (Re-camera):**
    *   **Sampler:** euler/simple. [H3_FINETUNES_SURVEY_2026-10-09.md]
    *   **CFG:** 1. [H3_FINETUNES_SURVEY_2026-10-09.md]
    *   **Sigma Shift:** 3.0 (using `MiniMaxH3SigmaShift`). [H3_FINETUNES_SURVEY_2026-10-09.md]
    *   **Steps:** 3 steps (Turbo). [H3_FINETUNES_SURVEY_2026-10-09.md]
    *   **LoRA Loading:** Load both teacher and turbo LoRAs at 1.0 strength; teacher first, then turbo. [H3_FINETUNES_SURVEY_2026-10-09.md]
*   **General VRAM Gate:** Gate on ~38 GiB free VRAM before queueing jobs. [MINIMAX_H3_CAPABILITIES.md]
*   **Not in notes:** Specific CFG scale values for standard Ref2VA, I2VA, or L2VA runs (other than Meridian) are not explicitly stated in the provided notes.

## Processes built on it

*   **Ref2VA Pipeline:** Use `MiniMaxH3ReferenceToVideo` node with `ref_images` (autogrow ref_image_1..9), `vae`, and `audio_vae`. [MINIMAX_H3_CAPABILITIES.md]
*   **T2VA Pipeline:** Use `MiniMaxH3ImageToVideo` node with `first_frame` and `last_frame` inputs left empty. [MINIMAX_H3_CAPABILITIES.md]
*   **I2VA/L2VA Pipeline:** Use `MiniMaxH3ImageToVideo` node, populating `first_frame` for I2VA or `last_frame` for L2VA. [MINIMAX_H3_CAPABILITIES.md]
*   **Bare Latent Generation:** Use `EmptyMiniMaxH3LatentAV` node for bare joint AV latent generation. [MINIMAX_H3_CAPABILITIES.md]
*   **Meridian Re-camera Process:**
    1.  Use `MiniMaxH3ReferenceToVideo` with two ref videos: the source clip and the geometric render. [H3_FINETUNES_SURVEY_2026-10-09.md]
    2.  Use the 480-class condition canvas. [H3_FINETUNES_SURVEY_2026-10-09.md]
    3.  Apply `MiniMaxH3SigmaShift` (3.0). [H3_FINETUNES_SURVEY_2026-10-09.md]
    4.  Load Meridian Teacher LoRA, then Meridian Turbo LoRA. [H3_FINETUNES_SURVEY_2026-10-09.md]
*   **LoRA Loading:** Use `LoraLoaderModelOnly` for attention/MLP LoRAs on pruned int8 bases. [H3_FINETUNES_SURVEY_2026-10-09.md]
*   **Not in notes:** Specific workflow JSON files or node graph connections for standard T2VA/I2VA are not detailed in the provided notes.

## What to avoid

*   **Do Not Mix Nodes:** Do not mix MiniMax H3 nodes with MiniMax Music 3 nodes; they are separate trees and share only the `CLIPLoader` type string. [MINIMAX_MUSIC3.md]
*   **Do Not Load Rewriter LoRA into H3:** The Rewriter LoRA on disk targets Qwen3.6-27B, not the H3 DiT. [MINIMAX_H3_CAPABILITIES.md]
*   **Do Not Use Diffusers Keys on Pruned Bases:** LoRAs with diffusers keys (e.g., `MiniMax-H3-FL2VA-Acc-8Step`, `MiniMax-H3-Ref2VA-Acc-8Step`) are BLOCKED and unusable on pruned bases as-is; they require PDD convert + full unpruned base. [03_loras.md]
*   **Do Not Load Time-Conditioning LoRAs on Pruned Bases:** LoRAs that touch time-conditioning (adaln) do not load on pruned/curve bases (e.g., hyperflow). [H3_FINETUNES_SURVEY_2026-10-09.md]
*   **Do Not Apply Sparse Attention After ControlNet:** Apply core `BlockSparseAttention` **before** any H3 Fun ControlNet node. Applying it after silently erases the control. [nodes_tools_papers.md]
*   **Do Not Use `max` Ref Image Size Unnecessarily:** While `max` provides best identity, it is "several times slower" because tokens ride every step. Use `match` (down-only) unless identity is critical. [MINIMAX_H3_CAPABILITIES.md]
*   **Do Not Exceed Mixed-Ref Cap:** Keep mixed references <=9. [MINIMAX_H3_CAPABILITIES.md]
*   **Do Not Use 2K Output Locally:** H3-Regenerate-2K is hosted API only; local output is 768p base. [MINIMAX_H3_CAPABILITIES.md]
*   **Do Not Assume Frame Roles Mix:** Frame roles (first/last) cannot mix with Ref2VA refs in one request (community claim, not tested). [MINIMAX_H3_CAPABILITIES.md]
*   **Not in notes:** Specific negative prompts or "bad" words to avoid in the text prompt are not listed in the provided notes.
