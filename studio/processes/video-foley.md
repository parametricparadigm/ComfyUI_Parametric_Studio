# Sound for a clip (Foley)

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


author decision 2026-10-17: "yes download and wrap mmaudio and yeah i guess wire foley if its on disk?". The ControlFoley entry (`vid:foley`,  a local port sidecar) is separate and unchanged: [audio-controlfoley.md](audio-controlfoley.md).

## Purpose / when to use it
- Every Wan 2.2 clip is silent by rule; H3 makes its own soundscape. **Foley** gives a silent (or already-sounding) clip generated sound effects and ambience from its pictures plus an optional text hint.
- Not for speech or music beds (H3 for dialogue, the Music tab for songs).

## Step-by-step in the studio UI
1. On a finished video card open **📱 Post steps → 🎼 Foley**.
2. Pick the backend (MMAudio up to 32 s, HunyuanVideo-Foley up to 12 s) and the mix (keep the clip's own sound with the foley under it, or replace it).
3. Optionally describe the sounds ("footsteps on gravel, light wind, a distant dog"). Your words go as typed (never the enhancer's rewrite).
4. **Add foley** queues a new card (a normal studio job: it waits for the GPU, can be retried, and the output guard checks the finished video).

## What the step does (studio/foley.py)
1. The backend makes the sound from the clip's pictures (+ the hint). If the asked backend is not installed, cannot take the clip's length, or fails, the other one is tried and the card's notes say so. A **busy GPU** is not a failure: the job waits (queue-when-free).
2. A clip with no sound gets the foley alone. A clip with sound keeps it; the foley sits 9 dB under the clip's own loudness and dips another 6 dB wherever the clip's own sound is present (10 ms gate, 40 ms attack, 300 ms release). `replace` drops the clip's own sound.
3. Master: `sound_dsp.master` to **-14 LUFS**, true-peak ceiling -1.2 dBTP before the AAC encode so the finished file is at or under **-1 dBTP**. The master never uses more than 6 dB of limiting: a spiky sound stops short and a note says what was reached.
4. ffmpeg copies the picture and encodes AAC 192 k / 48 kHz, metadata dropped.
5. If the clip's own voice carries the PerTh watermark it is checked again on the result; the foley goes down 4 dB at a time (4 tries) until it reads, else the mix is refused.
6. Provenance on the artifact (`foley`): backend, model, seed, hint, windows, licence, notes, fallbacks, source hash, master numbers, ducking, PerTh scores.

## Backends
| | MMAudio | HunyuanVideo-Foley fp8 |
|---|---|---|
| Runs | standalone worker `a local folder` (own venv, own torch 2.11+cu128; NOT a ComfyUI venv, not ComfyUI) | the pack's nodes on ComfyUI ( a local port by default, or the port a studio lane runs on; already loaded on  a local port,  a local port,  a local port on 2026-10-17) |
| Weights | `a local folder` (large_44k_v2 3.8 GiB, 44.1 kHz VAE 1.1 GiB, Synchformer 0.9 GiB) + the DFN5B CLIP and BigVGAN v2 already in the HF cache | `a local folder` (fp8 5.3 GB, 48 kHz VAE, Synchformer fp16) |
| Settings | euler 25 steps, CFG 4.5, bf16, seed 42 | euler 50 steps, CFG 4.5, batch 1, 24 fps frames at 512 px (the pack's example workflow) |
| Length | 1-32 s; over 8 s it is made in evenly sized windows (0.5 s overlap, equal-power crossfade) | 1-12 s (the example renders 10 s) |
| Licence (informational) | code MIT; checkpoints **CC-BY-NC-4.0** (non-commercial) | **Tencent Hunyuan Community License**: Territory only (not the EU, UK or South Korea); Outputs may not be used to improve another AI model |
| Known limits | README: sometimes speech-like mumbling or faint music; weak on unfamiliar sources. On the smoke clip the video-conditioned output ended in a ~100 ms loud click; the worker mutes it (length kept) and says so | none seen yet |

## Smoke tests (2026-10-17; nobody listened)
- **MMAudio, standalone worker** (own venv, torch peak 5.84 GiB allocated, card free stayed above 34 GB): text-to-audio 3 s ("rain falling on a tin roof, distant thunder"): 42 s wall (20 s model load, 16 s first generation), steady broadband sound, -24.7 LUFS raw. Video-conditioned, 4 s corgi clip made with ffmpeg from a still: 41 s wall, audio 3.97 s (the model truncates to the shorter Synchformer window), muxed file valid. 10 s clip: 2 windows, 30 s wall (4.7 s generation warm), 9.995 s out, no level dip at the seam. All three file md5s match the published values.
- **MMAudio through the whole Foley step** (real tool, real preflight): 4 s silent clip, 36.9 s wall, finished file -14.1 LUFS / -0.9 dBTP, AAC stereo 48 kHz, 4.0 s.
- **HunyuanVideo-Foley** through `foley_generate` on the idle orchestrator port  a local port (not through the running studio  a local port, which does not have this code until it is restarted): 4 s clip with the same hint, 29.8 s wall including the cold model load, 48 kHz mono flac 4.0 s, raw -36.9 LUFS, peak -15 dBFS, sparse (needed +22.9 dB, stopped at -15.6 LUFS under the 6 dB limiting budget, which the card says). The card's free VRAM dipped about 19.6 GB while it ran (an upper bound: other sessions share the card); the sampler offloads its models afterwards.
- Looked at: duration, loudness, true peak, spectrum, level over time. **Not heard.**

## Time and VRAM
- MMAudio: ~20 s load + ~16 s first generation, 5.8 GiB torch peak, the preflight budgets 8 GiB + the 4 GiB floor. Hunyuan: ~30 s cold for 4 s, budget 16 GiB + floor. Both go through the studio's usual preflight (refused while any ComfyUI port has work, while the studio holds the GPU, or when the card is short; nothing is evicted). The MMAudio worker stops itself if the card's free memory drops under 4 GB.

## Isolation (hard rule 1)
- The MMAudio venv is outside ComfyUI: `a local folder` (build script `a local folder`, frozen list `requirements-frozen.txt`, code `a local folder` = hkchengrex/MMAudio at (earlier commit)). Its torch (2.11.0+cu128) is its own; the first install let PyPI pull torch 2.14.1 for tensordict, which broke torchaudio, so step 3 of the script re-pins the trio. No pip ran in `the ComfyUI venv`, `the ComfyUI venv` or `venv`. The worker runs with `-I`, `PYTHONNOUSERSITE=1`, `HF_HUB_OFFLINE=1`.

## Guards

## Licence notes (informational, for the author's legal team)
- MMAudio checkpoints CC-BY-NC-4.0; Hunyuan license territory excludes the EU/UK/South Korea and bars using Outputs to improve other models. The catalogue entries and the artifact carry these lines; nothing gates on them.

## Not done / next
- Nobody has listened to either backend: listen to a few results and then raise the proof level in this table.
- The running studio ( a local port) shows none of this until it is restarted (author's call); the three ComfyUI ports already have the Hunyuan nodes, so no ComfyUI restart is needed.
