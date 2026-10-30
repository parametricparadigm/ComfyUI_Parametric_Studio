# MiniMax Music 3

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested here.


## Pre-retirement record (dfserve port, superseded)

### Purpose / when to use it
- Full songs with vocals, lyrics and structure (or instrumentals), 44.1 kHz stereo, from a caption + lyrics.
- Quick drafts in the studio. For release-grade tracks (auditions, QC, mastering to −14 LUFS, licence sidecars) use the
  `mm3.py produce` pipeline / `music3-producer` skill instead (see Evidence).

### Step-by-step in the studio UI
1. Music tab → Generator `minimax_music · Text → music`.
2. Seconds chip: 30 / 60 / 90 / 120 (a ceiling: the model may end the song earlier).
3. Prompt box = the caption. `lyrics` field = the lyrics with section tags.
4. ✨ enhance rewrites the caption with the Music 3 guide (optional). Generate.
5. The card plays the audio; ⤓ Download clean gives the scrubbed export.

### Optimal settings
| Setting | Value | Source |
|---|---|---|
| Weights | local ComfyUI files: DiT `diffusion_models/mini_max_music/minimax_music3_dit_fp16`, AR text encoder `text_encoders/minimax/minimax_music3_text_encoder_pruned_bf16` (int8 variant = faster AR), VAE `vae/minimax_music3_dav` | dfserve `pipeline.py`; files present 2026-10-11 |
| Sampling | dfserve's bit-exact port of the ComfyUI graph; the official template uses cfg_scale 1.7, top_k 50, KSampler 30 steps / cfg 1.7 / euler / simple. The studio exposes only seconds; dfserve's own defaults apply — not verified that they equal the template | MINIMAX_MUSIC3.md "Settings"; registry note |
| Length | seconds = ceiling; ~6 s per sung line is the sizing rule (CUT_OFF if length == ceiling and the end is loud) | MINIMAX_MUSIC3.md 2026-10-08 rule 2 |
| Seed | 0 + take index (studio default) | `runners._run_dfserve` |

### Prompting rules
  ("Prompt format", 2026-10-08 rules) feed the enhancer.
- Caption: three labelled blocks in order — `Global Metadata:` (genre, BPM, key, mood, production), `Vocal Details:`
  (gender, register, delivery), `Arrangement:` (instruments section by section). A detailed caption sang 13/16 lines
  intelligibly vs 5/16 for a one-liner.
- Lyrics: `[intro] [verse] [pre-chorus] [chorus] [bridge] [outro]`, every tag on its own line, no ordinals (`[Verse 1]`
  is out of distribution). Text after a tag on the same line is not sung.
- Instrumental: only non-vocal tags (`[intro] [instrumental] [solo] [instrumental] [outro]`) and "No vocals. Purely
  instrumental." in the caption; a lone `[instrumental]` still hums.
- BPM/key are suggestions. Caption + lyrics over 5000 tokens raises an error.

### Guards and gates
- Caption and lyrics go through the text guard. Audio output: the output guard accepts exactly one audio stream.
- Publishing an audio file runs a TRIBE pre-post check (audio pathway, GPU). See `guards-text-and-output.md`,
  `publish-download-tribe.md`.
- Licence: MiniMax-Music3 Community License — commercial use requires showing "MiniMax-Music3" (MINIMAX_MUSIC3.md).

### Time and VRAM
- Port  a local port (dfserve, self-unloads after 15 min idle). dfserve sets its own VRAM need; short → the card waits for GPU.
- Studio live check: 10 s song ~35 s incl. cold load, peak 15.69 GiB (LOCAL_MOE_REFERENCE §15, music PASS 2026-10-09, not
  listened to). ComfyUI reference runs: 30 s in 61.8 s cold, 120 s in 203.8 s warm (~1.7x realtime); GPU contention
  roughly halves throughput.

### Known pitfalls / failure modes
- The AR stage dominates and is latency-bound: schedule long songs when the card is quiet.
- Raw renders master hot (true peak ≥ 0 dBTP): master before release.
- The studio has no audition/QC step; a CUT_OFF ending is not detected here. Mastering is an option since 2026-10-17 (off by default; the raw take is kept): see [music-mastering.md](music-mastering.md).
- Only the 10 s studio path has been run through dfserve; 30-120 s studio renders are not verified.

### Evidence
- `a local folder` (`minimax_music` spec), `.../models/minimax_music3/pipeline.py` (weight paths).
