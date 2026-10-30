# Wan Animate 2

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- A still of a character (full body) moves with the motion of a driving clip: dance and motion transfer.
- Animate 2 paints a NEW background from the prompt; it does not keep the driving clip's room.
- **Identity is weak** on every Wan character path on this box: 0.17-0.19 face cosine against the still on the bf16
  sibling of this graph (BEST_OPTIONS wan.json `animate_character`, confidence low). The int8 render was not scored.
  When the face must hold, use the H3 character swap (`video-edits.md`).

## Step-by-step in the studio UI
1. Swap tab (or Video tab) → "Wan Animate 2 · Your character with a clip's motion".
2. Drop the character still in `character` and the driving clip in `source_video`.
3. Prompt: describe the character, the background you want and the camera, e.g. "a woman in a grey t-shirt and jeans
   dances in a bright living room, full body, natural light, photoreal" (the proof's prompt).
4. Generate. The job waits for (or is refused while) anything else is on the card: it runs alone.

## Optimal settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Model | `wan_animate_2/wan_animate_2/wan_animate_2_distill_int8_convrot.safetensors` + `WanAnimate2Cache` gpu/int8 | [tested] late_a2int8 row `a2int8_distill_int8` |
| Accelerator | none (the file is step-distilled) | [documented] Comfy template `video_wan_animate2_distilled.json`; model page DON'T |
| Sampler | lcm / simple, 10 steps, CFG 1, shift 5, SamplerCustom | [tested] same row; [documented] template |
| Size / length | 480x832, 81 frames (one 21-latent window), the driving clip's fps | [tested] |
| Negative | the official Chinese default negative | [tested] |
| Text encoder / VAE / vision | umt5 xxl fp8 (type wan), `wan/Wan2_1_VAE_bf16`, `clip_vision_h` | [tested] |

What the studio does to your inputs ([inference], kept close to the proof): the driving clip is re-encoded at 24 fps
(the proof's clip), cut to its first 81 frames, audio dropped, height capped at 1280. The graph itself area-scales and
centre-crops both inputs to 480x832, so a landscape driving clip loses its sides. Landscape output (832x480) exists in the
template but was never rendered here, so it is not offered.

## Prompting rules
- Prose: who, what they wear, where, light, camera. The motion comes from the clip, so describe it only lightly.
- The rules page read on every job: `a local folder`
  (its `.rules.json` sidecar). It feeds the enhancer; it cannot change the pinned graph.

## Guards and gates
  driving clip's person lends motion only, never a likeness.

## Time and VRAM
- 117 s on the proof (port peak 36.8 GiB, one run). The bf16 + lightx2v sibling peaked 76-83 GiB, so the studio budgets
  **78 GiB** (+4 GiB floor): in practice it runs alone on the 96 GB card. Lower `ANIMATE_PEAK_GIB` to ~42 once a second
  int8 run confirms the measured peak.

## Known pitfalls
- A driving clip shorter than 3.4 s (81 frames at 24 fps) is refused.
- Several people in the driving clip: untested; expect the motion of the most prominent one.
- The bf16 control row of the same A/B was killed twice by the VRAM watchdog (87-93 GB with other residents) before it
  passed at 82.8 GiB; that is why the job runs alone.

## Evidence
- `a local folder` (builder `build_animate2_int8_manifest.py`).
- `a local folder`: `a2int8_distill_int8` success,
  exec 116.9 s, port 37710 MiB, garbage check clean; control success at 187 s, 84740 MiB.
- KB `audits/BEST_OPTIONS_2026-10-10/wan.md` (Animate / character; Pending 11), `the author's build notes
- Upstream: https://huggingface.co/Comfy-Org/Wan-Animate-2 (Apache-2.0), https://docs.comfy.org/tutorials/video/wan/wan-animate-2.
