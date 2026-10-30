# Talking clip with Wan S2V

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose
A portrait still + a voice clip -> a talking clip of that person (16 fps, the voice muxed in), up to **4.8 s** (one 77-frame chunk). It is the default talk
route of a Wan Deliverables run (`wan_talk: auto`): the character's saved voice (charvoice anchor/seed, the same voice job as H3's lip-sync) says the line, S2V animates the
sheet's head shot. See [wan22-deliverables.md](wan22-deliverables.md).

## Step by step
Video tab -> "Wan 2.2 S2V": drop the `image` and the `audio`, describe how they speak and the scene, pick the size and the speed. Official is the default.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model | `wan2.2_s2v_14B_bf16` (UNETLoader default), wav2vec2 audio encoder, umt5 fp8 scaled, Wan 2.1 VAE | model page, row e_wsp_s2v_official |
| Sampler | ModelSamplingSD3 shift 3, euler/simple, 20 steps, CFG 4.5, official Chinese negative | same (tested); `uni_pc` breaks on this torch |
| Lightning | + T2V lightx2v 250928 high 1.0, 4 steps, CFG 1, empty negative: 13 s but "not trained for S2V" | row e_wsp_s2v_lightning; a preview only |
| Size / fps | 480x832 (tested), 832x480 (card, not rendered), 16 fps | rows |
| Length | `length` 4n+1 up to 81; 4 pad frames dropped; the studio puts 0.25 s of silence before the voice | `wan_s2v_tools.frames_for` |

## Time and VRAM
Official 191 s, 43.1 GB model / 49.0 GB port; lightning 13 s, 74.4 GB (port budgets 50 / 75 GiB + the 4 GiB floor).

## Known limits
Flatter than H3; one face, a clean portrait; the first 2 s may not move; a line over 4.8 s is cut (longer lines need the S2V Extend subgraphs, not wired);
