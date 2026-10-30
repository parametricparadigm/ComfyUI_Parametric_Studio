# Hand-drawn keyframes on H3

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Hand-drawn animation keys that hold the drawing's line and colour (the base H3 slides into vector easing):
| Entry | Inputs | Makes |
|---|---|---|
| `h3p:kf_hero` | `still` = the current key drawing | the natural NEXT hero key (no destination shown on purpose) |
| `h3p:kf_tween` | `still` = the rolling current frame, `last_frame` = the beat's far end extreme | the next inbetween, one small step toward the end |
| `h3p:kf_seq` | `still` = the window's first drawing, `last_frame` = its natural end | a short self-contained held sequence on twos |

Each render is 1344x768, 22 frames (0.9 s) at 24 fps, with H3's audio track.

## Step-by-step in the studio UI
1. Video tab → Generator → "H3 · Keyframe: …" (hero, tween or seq).
2. Drop the drawing(s). Write the caption in the adapter's dialect (below). ✨ enhance is ignored: the caption goes as
   typed (the studio only adds the opener / alignment line when missing).
3. Generate. To chain tweens, take a frame of the result as the next `still` and keep the same `last_frame`.

## Caption dialect (refused when a section is missing)
- hero: `SCENE: <framing + subject type + medium + props>. MOVEMENT: <the full arc: start, path, where it lands>.
  STATIC: <what holds, ending with framing + ground>.` (the studio adds "Create the next keyframe in the sequence.")
- tween: `SCENE: … FIRST FRAME: <pose in the near drawing; which way they face>. TARGET END FRAME: <the far pose as a
  destination, never comparative>. MOVEMENT: <one step>, landing <a quarter of the way / hold / anticipation /
  overshoot / arrival>. STATIC: …`
- seq: `Subject: <medium + subject type + ground>, animated on twos. Action: <path in beat order>. Camera: <angle /
  move, and the reason>. Preserve: <axes that must not drift>, and the on-twos rhythm.` (the studio adds "Picture 1
  aligns with the 0.00-second mark …; Picture 2 aligns with the 0.88-second mark.")
- No negations (CFG-distilled: no negative branch; the studio warns), no character / show names, the medium string
  identical across a shot (`clean line on white`, `flat black-and-white animatic`, `flat cel colour on white`).

## Optimal settings (pinned in the graphs)
| Setting | Value | Source |
|---|---|---|
| Base | Ref2VA **pruned** int8_convrot (unpruned = pruned, SSIM ≥ 0.996, +13 GB) | [tested] fu_g_kf_* pruned vs unpruned |
| Adapter | `minimax_h3/alvdansen_keyframe/h3_{hero,tween,seq}_step12000.safetensors`, LoraLoaderModelOnly 1.0 (the converted fused-qkv files: 0 keys not loaded) | [tested]; [documented] strength 1.0 = trained |
| Conditioning | MiniMaxH3ReferenceToVideo, ref_image_size max, 1 or 2 refs | [tested]; [documented] |
| Sampling | SigmaShift 12/3, BasicGuider (no CFG, no negative), euler/simple 30 steps, denoise 1 | [tested]; [documented] 30-100 steps |
| Size / length | 1344x768, 22 frames, 24 fps | [tested]; [documented] |
| Seed | 42 hero / tween, 7 seq (the paper figure seeds the proofs used) | [tested] |
| Never | turbo v4, DMAD or any step-distilled H3 (the linework is lost) | [documented] card warning |

## Guards and gates
- Text guard on the caption; output guard on every frame. Rules page read on every job: Ref2VA pruned int8's page.

## Time and VRAM
- 45-52 s per render;  a local port port peak 44.3 GiB with the adapter (26-36 GiB without). Budget 45 GiB + floor.

## Licence
- `h3-keyframe-animation-adapter-license-1.0.0` (PolyForm Small Business derived): free for individuals, researchers,

## Evidence
- `a local folder` rows `fu_g_kf_{hero,tween,seq}_pruned_lora1.0` (the
  templates, node for node; a test compares them); results 2026-10-10: 45.0 / 52.3 / 51.5 s, 44.3 GiB port.
- KB `audits/BEST_OPTIONS_2026-10-10/h3_ltx_video.md` "Keyframe adapters": hero helps strongly (kept the white card and
  cel style; the control went black), tween and seq mildly (steadier holds, no erratic arm swing).
- KB `the author's build notes CONFIRMED pick, "Not wired" until this entry.
- Upstream card: https://huggingface.co/alvdansen/h3-keyframe-animation (local copy with LICENSE under
  `a local folder`).
