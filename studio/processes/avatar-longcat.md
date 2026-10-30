# Talking head from a still

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
A still of a person + a voice clip → a **3.72 s** clip (93 frames, 25 fps) of that person saying it, lip-synced, with
the voice muxed into the file. No voice clip? Type the line and a Qwen3-TTS preset voice (Ryan / Aiden, the Voice tab's
preset engine, no cloning) speaks it first. For a saved voice of your own, make the clip in the Voice tab and drop it.

## In the studio
1. Video tab → "LongCat Avatar 1.5 · Talking head".
2. `image`: a clear, front-facing still (a chest-up portrait was tested). `audio` (optional): the voice clip.
   directly to the camera, natural lip movement, small head movements and blinks"), framing, light, background.
4. `line`: the words, when you drop no clip. `voice`: which preset speaks them.
5. `size`: 480p portrait 480x832, 480p landscape 832x480, 720p portrait 768x1280. `audio_cfg`: auto (= 1, the official
   script's value), 1 or 4. **Keep 1**: cfg 4 (the card's 3-5 tip) blows the mouth up into a glossy pink O on open
   vowels (see "Visual check" below).
6. The result goes through the output guard like every studio job.

## The recipe (pinned; the graph is `lb_lc_acfg4_short` node for node)
| | value |
|---|---|
| DiT / LoRA | `LongCat/LongCat-Avatar-15_bf16` (bf16, sdpa) + DMD distill LoRA rank128 1.0 |
| Audio | Whisper-large-v3 encoder fp16 → LongCatAvatarWhisperEmbeds (loudness normalised, scale 1, audio cfg 4 / 1) |
| Sampling | WanVideoSchedulerv2 longcat_distill_euler, 8 steps, shift 7; WanVideoSamplerv2 cfg 1; seed 4242 |
| Conditioning | the still resized + centre-cropped, WanVideoEncode → LongCatAvatarExtendEmbeds (overlap 1, ref frame 10) |
| Output | VHS_VideoCombine h264 25 fps with the audio (the `-audio` file) |

| Row | Size | audio cfg | exec |  a local port port peak |
|---|---|---|---|---|
| lb_lc_acfg4_short | 480x832 | 4 | 170 s | 41,252 MiB |
| lb_lc_off_short / off_emo | 480x832 | 1 | 132 / 88 s | 55,670 / 53,730 MiB |
| lb_lc_off720_short | 768x1280 | 1 | 296 s | 44,806 MiB (first try OOMed on a full card) |
| lb_lc_vs_lsync | 832x480 | 1 | 173 s | 51,890 MiB |

Budgets: 55 GiB (480p), 62 GiB (720p, the row estimate) + 4 GiB headroom.

## Visual check (2026-10-11 ~20:05)
`outputs/studio_motion_smoke_2026-10-11/longcat_test_acfg4_vs_acfg1.jpg`: top row = lb_lc_acfg4_short (audio cfg 4),
bottom = lb_lc_off_short (cfg 1), same still, line and seed. Cfg 4 inflates the lips into a glossy pink "O" on the open
vowels; cfg 1 moves them naturally. A studio-graph smoke on idle  a local port (149 s, whole card +47 GB) reproduced the cfg 4
clip frame for frame (`longcat_480p_00001-audio.mp4`, 93 frames, 3.72 s, AAC audio). The studio therefore defaults to
cfg 1 at every size; 4 stays selectable with a warning note.

## Limits
- One segment: audio longer than 3.72 s is cut there (a note says so); shorter is padded with the start.
- Lip sync has not been judged by ear yet (the late-batch sheet note); the 720p cfg 4 pair was not rendered.
  talking clip of a real person is a deepfake.
