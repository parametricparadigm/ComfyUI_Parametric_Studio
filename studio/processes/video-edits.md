# Video edits

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
| Entry | Does | Use for |
|---|---|---|
| `edit:char_swap` | recasts one person in a clip as the character in a picture; camera, motion, background kept | putting your character into stock or earlier footage |
| `edit:remove_person` | erases one person (H3 Person Remover), composites only the masked area back | clean plates; better than VOID for people |
| `edit:remove_object` | erases a non-person object (VOID), composited at full res | racks, props, signs |
| `edit:interpolate` | doubles the frame rate (core RIFE 4.26); audio passes through | smoother motion, 24 → 48 fps |
| `edit:depth_restyle` | a NEW H3 clip that follows the source's depth (layout, camera, motion, silhouettes) | restyle a clip while keeping its blocking |

## Step-by-step in the studio UI
1. Video tab → Generator → the edit entry.
2. Drop the clip into `source_video`. Char swap also needs `character` (the new person's picture; a stored character can fill it).
3. Prompt box = the TARGET, not a scene: "the man in the brown fur coat" (swap, remove person), "the clothes rack" (remove
   object). Depth restyle: describe the NEW clip. Interpolate: no prompt.
4. Remove object: fill the `background` field ("a plain white wall") = what shows where the object was (required).
5. Chips: interpolate `model` rife_v4.26 / rife_v4.26_heavy; depth_restyle `depth` strict (1.0 only) and `base` pruned/full.
6. Edits are never enhanced (no ✨ checkbox). Generate. Card: ⤓ Download clean, Retry / Queue when free.

## Optimal settings
| Entry | Recipe (fixed) | Source |
|---|---|---|
| char_swap | Ref2VA pruned **int8** + `h3_character_swap_pro4500_1000` 1.0 baked, res_multistep/simple **12 steps**, no turbo, text encoder unloaded, + `MiniMaxH3BlockCacheT8` defaults (350 → 195 s, SSIM 0.953) | H3_ADDONS_AB §1b arm D (author pass); h3_ltx_video.md node-pack table; `h3_pipelines.EXISTING` |
| remove_person | Ref2VA pruned int8 + Person Remover LoRA + h3-relay, SAM 3.1 text mask, Qwen 2.1 clean first frame, 12 steps, window 22; LoRA now on **bypass** (int8 bypass verified 2026-10-11; the proven arm was baked) | H3_ADDONS_AB §2; (earlier commit) |
| remove_object | VOID pass 1 + pass 2 (separate prompts, /free between), 45 frames from the start, 384x672 work size; mask = object box minus dilated person mask (core SAM 3.1) | MEDIA_CAPABILITIES §8 |
| interpolate | RIFE 4.26 (or heavy) x2 | `video_edit_tools.interpolate_frames` |
| depth_restyle | FL2VA pruned nvfp4 + pruned Fun Union 2.0, depth only, strength **1.0**, 40 steps res_multistep, CFG 1, + EasyCache 0.2 / 0.15-0.95 after the Union patch (419 → 189 s, control kept) | the author's build notes "H3 Union"; h3_ltx_video.md Union table |
| depth_restyle base `full` | unpruned FL2VA int8 + full Union 2.0: same control, 403 s, 63.6 GB, no speed gain: experiments only (the file `model_patches/minimax_h3/MiniMax-H3-Fun-Controlnet-Union-2.0.safetensors` is now complete, `.sha256-ok`, checked 2026-10-11) | h3_ltx_video.md; the author's build notes |
| seeds | char_swap/remove_person/remove_object have tool defaults; Variations sends a new seed | `runners.EDIT_ARGS` |

Never wired (the speedups guard refuses): Union depth + pose both at 1.0 (flat noise), CacheDiT / Block Cache /
sparse attention after the Union patch (control erased), Block Cache stacked with Spectrum or sparse attention
(`the author's build notes "Never wired").

## Prompting rules
- Rules pages: `a local folder` (swap,
  remover), `a local folder` (depth).
- Targets: name the person/object by clothing and position ("the woman on the left in the red coat"); SAM 3.1 finds it.
- Remove object: never a person; text-SAM alone mis-masks ("clothes rack" masked swimwear), which is why the tool subtracts
  the person mask.
- Depth restyle: the prompt cannot change hair or wardrobe that contradicts the source silhouette.
- Char swap: source ~5 s at 24 fps works best (the proven length); a clear, front-facing character picture.

## Guards and gates
- The target words and fields go through the text guard; the new clip goes through the output guard (char swap with a
  stored character must also show a face matching the character's anchor). Source clips are tool inputs and are assessed
  too. See `guards-text-and-output.md`; publishing a video runs TRIBE (`publish-download-tribe.md`).

## Time and VRAM (port  a local port; needed free = peak + 4 GiB)
| Entry | Code peak | Measured |
|---|---|---|
| char_swap | 50 GiB | 333 s, 51 GB at 12 steps (A/B arm D); with Block Cache 195 s; ~5.5 min per 5 s |
| remove_person | 65 GiB | 73 frames 213.8 s, 64.4 GiB (live tool run PASS) |
| remove_object | 23 GiB | ~33 s + ~39 s at 384x672x45 |
| interpolate | 2 GiB | not measured |
| depth_restyle | 48 GiB (full base 64) | 435.7 s, 46.5 GiB (live check, Pearson 0.948); ~189 s with EasyCache |

The "needs  a local port stopped" labels date from when the  a local port MoE (~46 GB) loaded at boot. Since 2026-10-11 it is on-demand
and off by default; if it is loaded, char swap, remover and depth will not fit — stop it first (author's call).

## Known pitfalls / failure modes
- Char swap: never below 12 steps (cuts turn into crash-zooms, objects vanish at 8), never on nvfp4 (identity collapses,
  ArcFace 0.47), never stacked on the 4-step turbo.
- Remover re-renders the whole frame; the tool composites back with the mask. After a remover run  a local port once held
  ~24 GiB that `/free` did not release (a unit restart cleared it).
- VOID works at low res on 45 frames; long objects/clips need several passes (not automated).
- Depth `loose` (0.7) was removed: unmeasured.

## Evidence
- Tests: `tests/tools/test_video_edit_tools.py`.
