# Wan Animate and SVI notes

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- This page exists so nobody picks the wrong Wan entry. For Wan in the studio use `wan:i2v` / `wan:t2v`
  (`video-wan22-i2v-t2v.md`).
- The four `wan22_* · …` entries in the Video drop-down are dfserve's diffusers pipelines. **Do not use them**:
  - dfserve's `HF_HOME` is `a local folder`; `models--Wan-AI--Wan2.2-{I2V-A14B,T2V-A14B,TI2V-5B,Animate-14B}-Diffusers`
    are 28 KB stubs each (checked with `du -sh` 2026-10-11). A request would start a tens-of-GB in-worker download, the
    same failure that got `qwen_image` / `qwen_image_edit` hidden (`DF_HIDDEN`: "a request starts a 57.7 GB in-worker
    download that wedges dfserve").
  - They run diffusers defaults (40 steps, no lightx2v, no LoRAs), not the box's proven 4-step stack.
  - `df:wan22_animate` is the original Wan2.2-Animate-14B (not Animate 2), and dfserve says it "needs driving video+ref",
    but the studio entry has one image slot only. Never tested here.
- Wan Animate 2 (pose/motion transfer onto a character) and the SVI 2.0 PRO long chain are studio entries now
  (`vid:animate2` on the int8 distill that passed 2026-10-11, `vid:svi`); their pages have the wired recipes. The
  tables below are kept as the pre-wiring reference.

## Step-by-step in the studio UI
- dfserve Wan entries: none. Skip them in the drop-down.
- Wan Animate 2 / SVI chain: Swap or Video tab → `vid:animate2`; Video tab → `vid:svi` (pp `recipes/wan.json` `long` still works).
- Removed 2026-10-10 by the author, not documented further: LTX (all), Wan 2.1, Kandinsky 5/6 (K6), HunyuanVideo 1.5,
  Mage-Flow, PixelDiT, TinyBreaker.

## Optimal settings
Wan Animate 2 (BEST_OPTIONS wan.md "Animate / character", confidence **low**):
| Setting | Value | Source |
|---|---|---|
| Model | `diffusion_models/wan_animate_2/wan_animate_2/wan_animate_2_bf16.safetensors` (official rebuild; old-format file mapped 11/731 keys) | wan.md |
| Accelerator | Wan 2.2 I2V lightx2v v1030 HIGH | wan.md |
| Sampler / steps / CFG / shift | lcm, 6 steps, CFG 1, shift 5 | wan.md |
| Size / frames | 480x832, 81 frames @ 24 fps | wan.md |
| Speed / VRAM | 85 s, 76-78 GB peak | wan.md (`fu_wan_animate2_blueprint`); h3_ltx_video.md surprise 9 |

SVI 2.0 PRO long video (BEST_OPTIONS wan.md "Long video (SVI)", confidence medium; the author's build notes "Long video" CONFIRMED):
| Setting | Value | Source |
|---|---|---|
| Base | Wan 2.2 I2V A14B fp8 KJ experts | wan.md |
| SVI LoRA | `SVI_v2_PRO_Wan2.2-I2V-A14B_{HIGH,LOW}_lora_rank_128_fp16` 1.0 / 1.0 (essential: without it the chain falls apart from clip 1) | wan.md |
| Accelerators | lightx2v v1030 high **0.6**, v1 low 1.0 | wan.md |
| Steps / CFG / shift | 4, CFG 1, shift 5 | wan.md |
| Chain | `WanImageToVideoSVIPro`: anchor = VAEEncode(start still), prev_samples = previous clip's latent, motion_latent_count 1, new seed per clip, drop first 5 frames of clips 2+ | wan.md |
| Output | 3 × 81 f = 233 frames (14.6 s) in 66 s, 74.8 GB, 480x832 | wan.md |
| Where | pp `pp/formatlab/recipes/wan.json` variant `long` + `pp/formatlab/wan.py` (1-3 clips) | the author's build notes pp table |

## Prompting rules
- Animate 2 / SVI: give each SVI clip its own prompt (one shared prompt made clip 3 drift: she sat on the sideboard).
- Rules page for the Animate 2 int8 file: `a local folder`
  (a hand-edited page; the builder left a `.md.new` beside it).
- dfserve Wan prompt skills say "not independently researched" (dfserve `/modes`).

## Guards and gates
- If a dfserve job ever ran, its output would pass the same output guard (dfserve proxy serve check) and publish gate as any
  studio video (`guards-text-and-output.md`, `publish-download-tribe.md`).

## Time and VRAM
- dfserve Wan: not measured on this box (no weights). dfserve decides its own VRAM need (`needs_vram` → the card waits).
- Animate 2: 85 s, 76-78 GB — near the 4 GB floor on the 96 GB card; it cannot share the GPU with H3 or the MoE.
- SVI chain: 66 s for 3 clips, 74.8 GB.

## Known pitfalls / failure modes
- Selecting a dfserve Wan entry can wedge dfserve with a background download (inferred from the qwen_image precedent and
  the empty caches; not tried). If it happens, dfserve needs an operator restart (`systemctl --user restart dfserve-a local port`,
  ask first).
- Identity is weak on every Wan character path (Animate 2 ArcFace 0.17-0.19 vs the still): do not use Wan as the
  identity-critical character engine; use H3 (`video-h3-modes.md`, `video-edits.md` char swap).
- SVI 2.0 non-Pro ghosts in the last frames and is not chained; Wan 2.1 SVI left with Wan 2.1.
- Recommended fix (code, not done here): add the four `wan22_*` names to `DF_HIDDEN` like `qwen_image`.

## Evidence
- `du -sh a local folder` → 20-36 KB each (2026-10-11).
- `a local folder` lines ~200-225 (repo ids, default_steps 40, animate note).
