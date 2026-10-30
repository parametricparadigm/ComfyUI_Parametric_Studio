# H3 pipelines

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
| Entry | Makes | When |
|---|---|---|
| `h3p:i2va` | a clip whose frame 0 IS your still, then the person acts and speaks | you need the exact opening frame |
| `h3p:l2va` | a clip that ENDS on your still (walks in, lands on the pose) | you need the exact final frame |
| `h3p:multishot` | 2-3 hard cuts inside one 5.2 s clip, same person | a mini-sequence in one render |
| `h3p:longvideo` | H3LongVideos auto-chain: 2-4 shots of ~5 s, one paragraph each (~20 s) | longer talking scenes |
| `h3p:handheld` | handheld/selfie walk-and-talk look (author pass "walk handheld is sick") | UGC walking selfies |
| `h3p:meridian` | re-films an existing landscape clip from a new camera path (orbit 20°/45°, dolly-in, crane up) | new angle on footage you have |

## Step-by-step in the studio UI
1. Video tab → Generator → the `H3 · …` pipeline entry.
2. Slots and fields:
   - i2va: `still`; fields dialogue (spoken words only), soundscape. l2va: `last_frame`; same fields.
   - multishot: `still` (= `<Picture 1>`); field subject (who Picture 1 is).
   - longvideo: `still` (the character); field character = one line `Name: who they are`.
   - handheld: no slot; fields dialogue, soundscape.
   - meridian: `source_video`; field subject_box (pre-filled `[L=0.320, T=0.170, W=0.360, H=0.830]`, edit to frame your
     subject); chips move (orbit20 / orbit45 / dolly_in / crane_up) and audio (source / none). No prompt.
3. Aspect: 16:9 only (1344x768) on i2va/l2va/multishot/handheld; longvideo is 16:9 fixed; seconds 5 only.
4. ✨ enhance: i2va/l2va/handheld take the rewrite when it is prose; multishot and longvideo always send your words raw
   (their structure must survive). Generate.

## Optimal settings
| Entry | Base · sampler (fixed, proof values) | Source |
|---|---|---|
| i2va / l2va | FL2VA pruned **nvfp4**, `MiniMaxH3ImageToVideo.first_frame` / `.last_frame`, turbo v4 1.0, TurboSampler 4 steps, 1344x768x124 | LTX_H3_BATCH §5 (frame 0 SSIM 0.869, ArcFace 0.77, 56 s; last frame SSIM 0.859, 43 s) |
| multishot | Ref2VA pruned **int8**, turbo v4 1.0, 4 steps (render_h3_mode, distill turbo only; DMAD on cuts untested) | LTX_H3_BATCH §6 (cuts within ~0.1 s, later cut ~0.2 s early, 61 s, 45.7 GB) |
| longvideo | FL2VA pruned **nvfp4** → `MiniMaxH3TurboLoRA(turbo v4)` → H3LongVideos **euler, 4 steps, simple** + sigmas from `BasicScheduler(simple, 4)`; 1.0 MP 16:9, 5 s shots, 2-4 shots | LTX_H3_BATCH §9-fix B4/L4 (4 shots / 20.5 s in 181 s, seams SSIM 0.87-0.89) |
| handheld | Ref2VA pruned **int8** + `handheld_h3_100` **baked 1.0** before turbo v4, TurboSampler 4, TE unloaded | CIVITAI_TESTS W2 (51 s, 47.2 GB). Author recipe 1.7 is broken on every loader (h3_ltx_video.md surprise 3) |
| meridian | NyckM camera (MoGe-2 warp) → Ref2VA conditioning + MeridianFrozenPrompt → ONE bypass rank-cat LoRA (Meridian teacher + turbo) 1.0 → shift 3/3, euler/simple 3 steps, 1344x768x124. **Now on FL2VA int8 + bypass** (flag `H3_INT8_BYPASS_VERIFIED = True`); the proven arm was FL2VA nvfp4 | MERIDIAN_TEST §8-9 (orbit20 119 s, orbit45 186 s, dolly-in 166 s, crane up 165 s, 34.1 GB on nvfp4); int8 looked equal in one pair (158 vs 142 s, h3_ltx_video.md) |
| seeds | 4242 (meridian 1234) | `h3_pipelines.PIPELINES` |

## Prompting rules
- Rules pages: `a local folder` (h3p:*),
  `a local folder` (handheld).
- i2va / l2va / handheld: these take no reference stills for identity, so name hair, wardrobe and place in the prompt.
  Handheld example (from the entry): "A young woman in a denim jacket and white t-shirt walks along a sunny city sidewalk
  past shop windows, filming herself at arm's length as she walks, smiling and talking".
- multishot: `[Shot 1] …` then `[Shot 2] At 00:01.800, the camera cuts to …` (MM:SS.mmm, seconds 00-59; "At 1.8 s" is
  refused), 2-3 shots, times rising, last cut inside 5.2 s. Plan a later cut ~0.2 s early.
- longvideo: paragraph 1 = the scene; each further paragraph = one shot, each with a quoted line. A beat with only
  "laughs" babbles.
- meridian: no prompt; source must be native 1344x768, 24 fps, ≥ 124 frames (≥ 5.17 s). Other sizes are refused, never cropped.

## Guards and gates
- Text guard on prompt and fields; output guard on the clip (4 fps + scene changes + first/last frame); TRIBE pre-post
  check when a video is published. See `guards-text-and-output.md`, `publish-download-tribe.md`.
- Meridian's output is a new render: it is classified like any other output, whatever the source passed.

## Time and VRAM (port  a local port; needed free = peak + 4 GiB)
| Entry | Code peak | Measured |
|---|---|---|
| i2va / l2va | 40 GiB | ~39 GB; 43-56 s |
| multishot | 46 GiB | 45.7 GB; 61 s |
| longvideo | 41 GiB | ~40 GB; 181 s for 4 shots (~45 s per shot) |
| handheld | 48 GiB | 47.2 GB; 51 s |
| meridian | 35 GiB (nvfp4); int8 path preflights 44 GiB — an estimate, not measured | 34.1 GB on nvfp4; 119-186 s |

## Known pitfalls / failure modes
- 9:16 on these graphs is untested, so not offered.
- A 1-2 frame colour flash can appear at a multishot cut.
- H3LongVideos' node default `res_multistep` with a turbo LoRA burns every shot; the entry forces euler. Licence: no
  redistribution.
- Meridian bullet time is partial and orbits above 45° are untested; the VGGT-Omega route was worse (and gated).
- Duo is unlisted: the AB8 proof failed (the right person became a look-alike of the left).
- Most entries need tens of GB free; if the  a local port MoE (~46 GB) is loaded, stop it first (author's call; it is on-demand
  since 2026-10-11).

## Evidence
- Tests: `tests/tools/test_h3_pipelines.py`; dry run `scripts/chatbox/h3_pipelines_check.py`.
