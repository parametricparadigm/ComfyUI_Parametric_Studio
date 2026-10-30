# LightWan 720p

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
A 720p, 81-frame clip (16 fps, ~5 s) in about **70 s** at **~35 GB** of VRAM (measured port peak 33.4 GiB), where the
box's fp8 KJ + lightx2v Wan 2.2 stack needs 67-72 GiB at 720p for the same time. In the test the results were on a par
with that stack (comparison sheet `outputs/lora_retest_2026-10-09/sheets/lightwan720_vs_box720.jpg`).

**720p only.** the author's call (2026-10-11): "if the wan 720 works we dont need wan 480". The 480p rows ran too, but
the studio has no 480p option for LightWan.

## In the studio
1. Video tab → "LightWan 2.2 · Image → video 720p" or "LightWan 2.2 · Text → video 720p".
2. Image to video: drop the start still in `image`.
3. Prompt: prose, 30-80 words: who and what they wear, the setting, the motion beat by beat, the camera, the light (the
   tested prompts). ✨ enhance reads the Wan guides. A prompt under 20 words gets a note on the result.
4. Aspect: I2V `auto` (the still's orientation), `9:16` (720x1280, tested), `16:9` (1280x720, not rendered for I2V);
   T2V `16:9` (1280x720, tested), `9:16` (not rendered for T2V). Both stay at 720p.
5. Every result goes through the output guard like any other studio job.

## The recipe (pinned in the graphs; the tested graphs node for node)
| | I2V (`lb_lw_i2v720_{spin,sprint,laugh}`) | T2V (`lb_lw_t2v720_{dog,skate,breakdance}`) |
|---|---|---|
| Experts | `wan2.2/lightwan/Wan2.2-I2V-A14B_NVFP4_Sparse_{high,low}_comfy` | `…-T2V-A14B_NVFP4_Sparse_{high,low}_comfy` |
| LoRA | none (the 4-step DMD2 distill is baked in) | none |
| Shift | 7 | 5 |
| Sampling | KSamplerAdvanced euler/simple, CFG 1, 4 steps: high 0-2, low 2-4 | same |
| Latent | WanImageToVideo 720x1280 x81 | EmptyHunyuanLatentVideo 1280x720 x81 |
| Text / VAE | umt5_xxl fp8 (wan), empty negative / wan_2.1_vae | same |
| Output | CreateVideo 16 fps → SaveVideo, seed 4242 | same |
| Time / peak | 69-72 s exec, 34,152 MiB port | 65-71 s exec, 33,808-34,032 MiB port |

## Decode chip (standard / fast / preview)
`decode`: **standard** (default, the tested graph), **fast** = LightVAE Pro (1.45-1.5x decode, same quality as standard vs the source; finals), **preview** = LightVAE Lite (2.8-3x decode, 1-3.6 dB softer; drafts). Only the decode changes; the encode stays the stock Wan 2.1 VAE. Until  a local port has restarted with the LightVAE pack a fast/preview job renders standard with a card note. Numbers and details: [video-wan-decode.md](video-wan-decode.md).

## VRAM budget
`PEAK_GIB = 35` (the measured 33.4 GiB port peak, rounded up) plus the usual 4 GiB headroom in the preflight. The tool
refuses rather than queues when a ComfyUI port is busy, the studio holds the GPU, or the card is short after idle  a local port
caches are reclaimed.

## Files and output
- Weights (8.38 GB each, sha256-checked by dlq 0130-983, `.sha256-ok` markers): the job refuses if either expert or its
  marker is missing.
- Results: `a local folder,t2v}_<hash>.mp4`, a hardlink of ComfyUI's own file (which
  stays visible in  a local port's history).

## Sources
- [tested] the late batch rows above (KB SCOUT_2026-10-11_TESTS.md, "Late batch (dlq 0130-0160)").
- [documented] LightX2V `configs/wan22/extreme/wan_moe_{i2v,t2v}_distill_nvfp4_sparse_attn.json`: 4 steps, boundary step
  2, shift 7 / 5, cfg off, 81 frames. HF `lightx2v/LightWan2.2-A14B`: NVFP4 QAT DMD2, Blackwell only. Apache-2.0.
- [inference] euler/simple reproduces the 1000/750/500/250 step list; dense attention (the LightX2V sparse attention has
  no ComfyUI node, so the card's speeds do not apply).
