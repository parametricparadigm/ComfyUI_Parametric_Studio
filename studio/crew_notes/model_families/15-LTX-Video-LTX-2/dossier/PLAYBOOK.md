# PLAYBOOK.md: 15-LTX-Video-LTX-2

## Prompt structure

*   **Format:** Use one flowing present-tense paragraph. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Camera:** Include exactly one camera move in the prompt. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Style:** Write in a "style prose" manner. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Audio:** Include audio descriptions in the prompt (e.g., "soft crunch of snow and distant traffic"). [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Negative Prompt (Distilled):** The negative prompt is inert at CFG 1.0, but the template `'pc game, console game, video game, cartoon, childish, ugly'` is noted. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Negative Prompt (Dev):** Use a real negative prompt when CFG > 1 (e.g., `'blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, excessive noise, grainy texture'`). [ltx-2.5-22b-dev-transformer-bf16.md]
*   **I2V Specifics:** For Image-to-Video, the first frame locks the viewpoint; extreme angles should be established in the first frame, not just the prompt, as the prompt is weak for controlling viewpoint under I2V. [LTX25_ANGLES_AND_CONTROL.md]
*   **Motion Specifics:** If using a static camera, do not put motion words in the prompt, or the camera will drift. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]

## Words and phrasing that work

*   **Present Tense:** Use present-tense verbs for actions (e.g., "walks," "switch on"). [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Specific Motion:** Use longer, specific motion prompts to avoid static or zoom-only results in I2V. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Camera Vocabulary:** Phrases like "slow tracking shot from the side" and "ending on her face" are effective for defining the single camera move. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Audio Cues:** Describing ambient sounds (e.g., "distant traffic") helps generate synchronized audio. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
*   **Camera LoRA Triggers (Community/Official):**
    *   For Dolly In/Out/Left/Right (19B LoRAs): Describe the destination of the movement. [LTX25_ANGLES_AND_CONTROL.md]
    *   For Jib Up/Down (19B LoRAs): Describe what is revealed at the end (e.g., "the sky above"). [LTX25_ANGLES_AND_CONTROL.md]
    *   For `elismasilva/LTX-2.3-LoRa-Camera-Controls`: Use phrases like "the camera tilts up/down," "pans to the left/right," "zooms in on <obj>," "zooms out." [LTX25_ANGLES_AND_CONTROL.md]
    *   For `AhsanHareem/reelbids-ltx25-camera-lora-v2`: Use prefix `rbdollyin` followed by speed tokens `sp05` through `sp50`. [LTX25_ANGLES_AND_CONTROL.md]

## Settings that worked

*   **Distilled Model (Int8):**
    *   **Sampler:** `euler_ancestral` (Stage 1 and 2). `euler` is also fine. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Scheduler:** `ManualSigmas` with values: `1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0`. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Steps:** 8. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **CFG:** 1.0. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Resolution:** Native 1280x704 (Landscape) or 704x1280 (Portrait). Width/Height must be divisible by 32. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Two-Stage Process:** Stage 1 runs at half resolution (640x352), followed by a spatial x2 upscaler and a 3-step Stage 2. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Frames:** 121 frames. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **FPS:** 24. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Max Length:** 10 seconds. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **VRAM:** Typically 38.4 GB, worst case 43.8 GB. Keep ≥ 4 GB free. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Text Encoder:** `gemma/gemma4-12b-ltx2.5-proj-comfy-int8-convrot.safetensors` (Type: `ltxv`). Running on CPU saves ~15 GB VRAM. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **VAE:** `ltx-2.5-video-vae-bf16.safetensors` (+ audio VAE). Conv VAE (`ltx-2.5-video-vae-conv-bf16`) is faster but softer. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]

*   **Dev Model (BF16):**
    *   **Sampler:** `euler_ancestral` or `euler`. [ltx-2.5-22b-dev-transformer-bf16.md]
    *   **Scheduler:** `LTXVScheduler` or `simple`. [ltx-2.5-22b-dev-transformer-bf16.md]
    *   **Steps:** 30. [ltx-2.5-22b-dev-transformer-bf16.md]
    *   **CFG:** 3.0. [ltx-2.5-22b-dev-transformer-bf16.md]
    *   **VRAM:** Typically 80.0 GB. Run only with the card nearly empty. [ltx-2.5-22b-dev-transformer-bf16.md]
    *   **Accelerator:** Can use `ltx-2.5-22b-distilled-lora-450-bf16` to behave like the distilled model (8 steps, CFG 1). [ltx-2.5-22b-dev-transformer-bf16.md]

*   **General Constraints:**
    *   **Frame Count:** Must satisfy `frames % 8 == 1`. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]
    *   **Resolution:** W/H multiples of 32. [ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.md]

## Processes built on it

*   **Quality Ladder (Format Lab):**
    *   **L1 Draft:** Use LTX distilled for fast drafts (19-34 s per 5 s clip). [FORMAT_LAB_kids_and_music_video.md]
    *   **L4 Premium:** Use LTX dev bf16 for the final pass with hand-picked takes and colour match. [FORMAT_LAB_kids_and_music_video.md]
*   **Kids' Shows (Trunk A):**
    *   **Sing-along:** Use LTX audio lock (0.5 s lead, ≤8 s) for singer shots and LTX image-to-video for scene shots. [FORMAT_LAB_kids_and_music_video.md]
    *   **Story/Dialogue:** Use isolated audio tracks to drive LTX locks on characters. [FORMAT_LAB_kids_and_music_video.md]
    *   **Lullaby/Long-form:** Use LTX Extend/Looping samplers for 20-60 s single takes and seamless loops. [FORMAT_LAB_kids_and_music_video.md]
    *   **Read-along:** Use LTX first+last-frame (FLF) for gentle camera moves. [FORMAT_LAB_kids_and_music_video.md]
    *   **Shorts/Canvas:** Use 704x1280 resolution for Spotify Canvas 8 s loops. [FORMAT_LAB_kids_and_music_video.md]
*   **Music Videos (Trunk B):**
    *   **Performance Lip-sync:** LTX is noted as the best lip-sync engine for some voices. [VIDEO_MODELS_PLAYBOOK.md]
*   **Camera Control Workflows:**
    *   **IC-LoRA Union Control:** Use `LTX-2.3-22b-IC-LoRA-Union-Control` with a reference clip to control framing and camera path via depth/canny/pose. [LTX25_ANGLES_AND_CONTROL.md]
    *   **Layout-to-Render:** Use the official Layout-to-Render IC-LoRA with a grey Blender playblast to set exact camera paths. [LTX25_ANGLES_AND_CONTROL.md]
    *   **First/Last Frame:** Use `LTXVAddGuide` with frame_idx 0 and -1 at different angles to force specific moves (e.g., pedestal-down). [LTX25_ANGLES_AND_CONTROL.md]
    *   **T2V + Licon MSR:** Use for identity from up to 5 reference images without a first frame, allowing prompt-defined camera
