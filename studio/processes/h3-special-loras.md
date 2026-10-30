# H3 special modes

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
The H3 LoRA picker lists plain add-ons only. 34 family-h3 library files are not add-ons (they need a source clip, keyframes, a camera node, a distill, or the realism look). The picker now shows them under a collapsed **Special modes** group on the Image → video / Selfie entries: each says what uses it ("used by <entry> · <chip>") with an **open <entry>** link, none is selectable, and speed LoRAs say they are covered by the Speed chip. A new **Fast (turbo, rank-concat)** switch on an add-on that has a proven turbo + add-on file renders it at turbo steps.

## Step-by-step in the studio UI
1. Video tab → any entry with the 🎛 LoRAs row (H3 · Image → video, Selfie talking head) → 🎛 LoRAs → bottom of the list, "Special modes".
2. Click **open …** to jump to the entry that uses a file. New entries: **Video → video (VFX edit / style transfer / sharpen)**, **Frozen-time 360 orbit**, **Restore a low-quality clip**.

## Optimal settings
| Mode | Recipe | Source |
|---|---|---|
| Video → video | Ref2VA pruned nvfp4, ONE bypass loader on the rank-concat file (ref2v turbo v0.1 + the LoRA, 1.0), `MiniMaxH3AddGuide` frame 0 = your clip, SigmaShift 12/3, BasicGuider, euler/simple 8 steps. vfx_edit 672x384x73, style_transfer 672x384x107 (+ optional style picture = `<Picture 1>`), sharpen 1024x576x107 (fixed caption, soft clips only). Source sound muxed back | author's workflows (`alissonerdx_v2v/workflows`), recipes §2.4-2.6, LORA_RETEST_2026-10-09 b04-b06 |
| Orbit | FL2VA pruned nvfp4, orbit LoRA 1.0 bypass, the still as first AND last frame, the LoRA's fixed prompt verbatim, 768x768x73, 28 steps, no audio | HF card, recipes §2.7 |
| Restore | Ref2VA pruned nvfp4, Restore LoRA 1.0 bypass, your clip as `ref_video_0`, the LoRA's caption, 20 steps, size = clip ratio (long side 832 / 1344), up to 124 frames | author's page (civitai 2989135) |

## Prompting rules
vfx_edit: the edit first, then what must stay. style_transfer: linework / palette / brushwork. sharpen, orbit and restore ignore typed text (fixed captions). Triggers of the Fast add-ons still lead the prompt.

## Guards and gates

## Time and VRAM
Everything renders on a port picked by the studio (portable graph route), preflight peak + 4 GiB free. Measured here on  a local port (nvidia-smi totals over a quiet baseline): vfx_edit 22 GiB / 47 s cold; sharpen 55 GiB / 98 s cold; style transfer finished in 40 s. The planning peak for `h3p:v2v` is 58 GiB (sharpen). Orbit planning 40, restore 48 (not measured).

## Known pitfalls / failure modes
Orbit was trained on human splats (domain narrow); a bake into nvfp4 gave no orbit, so it runs as a live bypass LoRA. Sharpen on an already sharp clip only darkens it. Restore and orbit have no box render of their own: **marked untested**. author instruction (2026-10-14) was to skip further GPU smoke; before that, three v2v frames were reviewed (below).

## The audit: each of the 34
Home / exists / uses this exact file / plan, and what was done. "tests" = `tests/studio/test_h3_special.py` pins the claim.

| # | LoRA (under minimax_h3/ unless noted) | Home | Home existed, same file? | Result |
|---|---|---|---|---|
| 1 | MiniMax-H3-Realism-People-LoRA/h3-realism-people-t2v-i2v-r2v | Look chip 'realism' (Image → video / Selfie) | yes: `h3_tools.REALISM_LORA`, baked 1.0 before turbo v4 on Ref2VA nvfp4 | verified, listed as "used by" |
| 2 | minimax/H3-World/step-10000 | H3-World node | node installed (T8) but errors: "forward contract is not compatible with H3-World; missing markers" in all 5 box runs; raw PEFT file | **BLOCKED**, stays in Special modes with the reason |
| 3 | alissonerdx_v2v/loras/minimax_h3_lms_v1.0_r64 | `h3p:v2v` chip sharpen | new | built (via rc_ref2vturbo4v01_lms) |
| 4 | alissonerdx_v2v/loras/minimax_h3_style_transfer_v1.0_r64 | `h3p:v2v` chip style_transfer (+style picture) | new | built (via rc_ref2vturbo4v01_style) |
| 5 | alissonerdx_v2v/loras/minimax_h3_vfx_edit_v1.0_r128 | `h3p:v2v` chip vfx_edit | new | built (via rc_ref2vturbo4v01_vfxedit) |
| 6-8 | alvdansen_keyframe/h3_hero / h3_seq / h3_tween _step12000 | `h3p:kf_hero` / `kf_seq` / `kf_tween` | yes: `HP.KF_LORAS`, baked 1.0, 30 steps | verified (test pins the three files) |
| 9 | civitai_wide/h3_upscale_1920 | image upscaler | no | **BLOCKED**: the author's workflow zip (civitai 2924512, optional download) is not on the box and the page omits steps / scheduler / which frame; only prompt (`A static still blurry pixelated picture crossfades into a clear sharp detailed picture, 4psc4l3,`), strength 1, CFG 1, 24 frames, 1280-1920 px are known. Not guessed |
| 10 | civitai_wide/Restore_Enhance_Improve_rank16_v1_H3-lora | `h3p:restore` | new | built from the author's notes (clip on the video reference, strength 1.0, same ratio); untested |
| 11 | dmad/minimax_h3/dmad_minimax_h3_4step_full_critic_comfyui | Speed chip 'dmad' | yes: `h3_tools.DMAD_LORA` | covered by the Speed chip |
| 12 | H3-Person-Remover-V1 | `edit:remove_person` | yes: `h3_addons` route + `h3_person_remover` template, 1.0 | verified |
| 13-14 | hyperflow/minimax_h3_hyperflow_8step_v1.0; minimax_h3_hyperflow_8step_v1.0_comfyui_pruned_bf16_resized_avg_rank_20_bf16 | Speed | n/a | speed LoRAs the Speed chip covers; exposed nowhere |
| 15-18 | MiniMax-H3-FL2VA-Acc-8Step (+_comfyui_pdd), MiniMax-H3-Ref2VA-Acc-8Step (+_comfyui_pdd) | Speed | n/a | same |
| 19 | minimax_h3_fl2v_turbo_4step_v1.2_768p_comfyui_bf16 | own distill of H3 · Text → video | yes (pp `T2VA_LORA`) | covered |
| 20-21 | minimax_h3_fl2v_turbo_4step_v0.1_768p_sla_comfyui_bf16; minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16 | Speed | n/a | covered (the 8-step 0.7 share lives in the Booster file) |
| 22-23 | minimax_h3_ref2v_turbo_4step_v0.1; minimax_h3_ref2v_turbo_8step_v1.0_768p | Speed | n/a | covered (they are the turbo halves of the rank-concat files) |
| 24 | minimax_h3_taomate_3step_lora_avg_rank_19_bf16 | Speed | n/a | covered |
| 25-26 | minimax_h3_turbo_v4_step600_ema; …_pruned_comfyui | Speed chip 'turbo' (default) | yes: the studio templates load step600_ema; the pruned copy is unused | covered |
| 27 | meridian/comfyui/meridian_teacher_plus_turbo_rankcat_lora | `h3p:meridian` | yes: `h3_addons._ROUTES` | verified |
| 28 | orbit360/minimax_h3_flf2v_lora_v1 | `h3p:orbit360` | new | built from the card; untested (KB: baked nvfp4 gave no orbit; bypass b07 ran 60 s, no verdict recorded) |
| 29-31 | retest_rankcat/rc_ref2vturbo4v01_{vfxedit,style,lms} | files the `h3p:v2v` chips load | new | built; box evidence: the b04-b06 rank-concat arms rendered with sane frames (reviewed 2026-10-14) and three smoke renders (below) |
| 33 | retest_rankcat/rc_ref2vturbo8_unlocked | Fast option of Minimax_H3_Unlocked_V2 | new | wired (6 steps euler_ancestral); c06 arm rendered (59 s); quality unjudged |
| 34 | retest_rankcat/rc_fl2vturbo8_booster | Fast option of Motion Booster V2 | no | **BLOCKED**: the pair was built and rendered on the FL2VA base with a first frame; the add-on list renders on Ref2VA. Stays in Special modes; the 20-step add-on route stays |

## What was verified on the box (and what was not)
- All new graphs validate against  a local port `/object_info` (17/17 in `h3_pipelines_check.py`): no node or model missing, nothing installed or downloaded.
- Smoke renders through the graph builder on  a local port ( a local port carried another session's claim), neutral person-free inputs (a Wan river-valley clip, a H3 forest clip, a watercolor dog picture): vfx_edit snowfall (47 s, +22 GiB, scene and camera motion kept), style_transfer watercolor (40 s, look applied, motion kept), sharpen (98 s, +55 GiB, scene kept, slightly crisper). **Not run: orbit360, restore, the Fast options** (author asked to stop GPU work); all five new entries and options are marked untested.

## Evidence
`audits/LORA_USAGE_RECIPES_2026-10-09.md` §2.4-2.7, §4.1; `audits/LORA_RETEST_2026-10-09.md` (b04-b07, c01-c06); `audits/LORA_RETEST_2026-10-09_h3know.md` (H3-World k04 errors); civitai.com/models/2924512, /2989135; `a local folder`.
