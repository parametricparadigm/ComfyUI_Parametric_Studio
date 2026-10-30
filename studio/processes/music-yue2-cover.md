# Song cover with YuE2

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What it does
SheetSage2 reads the **melody** of a source song into an ABC score; YuE2-3B then sings **your lyrics in your style** on that melody. It is not voice cloning
(the voice is a style choice) and it is not Music 3: the tune stays, the arrangement and singer change. Everything is core ComfyUI (`comfy_extras/nodes_yue2.py`,
`nodes_audio_encoder.py`); no custom-node pack, no pip, no Plenio code. The graph is ComfyUI's own `audio_yue2_music_cover` template wiring, plus the optional
excerpt (`TrimAudioDuration`) from the Plenio v1.0.0 cover workflow (read only, never run or installed; assessment in
[../research/plenio-assessment-2026-10-17.md](../research/plenio-assessment-2026-10-17.md)).

```
LoadAudio -> [TrimAudioDuration] -> SheetSage2AudioToABC (melody) -.
CheckpointLoaderSimple (yue2_3b_bf16) -> YuE2GenerateMusic (mode melody, abc, style, lyrics, max_duration) -> ConditioningZeroOut
  -> KSampler (32 steps dpm_2 / sgm_uniform, cfg 1) on EmptyYuE2LatentAudio(seconds from the conditioning) -> VAEDecodeAudio -> SaveAudioAdvanced (flac)
```

## How to use it
- **Music tab**: pick *YuE2 cover*, drop an audio file or pick a studio audio result in the **audio** slot, write the style (one line: language, genre, voice, tempo,
  instruments) and the lyrics (`[verse]` / `[chorus]` tags). Chips: *Up to N s* (output ceiling, YuE2 follows the lyrics and may stop earlier), *Read N s of the song*
  (default 60, max 240), *From N s in*, Vocals / Instrumental, Master after render. No BPM / key chips: the tune and tempo come from the source.
- **Song recreate** (single and batch): *Recorded with* = **YuE2 cover**. The source can be a URL (the song library's safe import), a library song, an upload or a studio
  review stop; lyrics modes (new / the heard words / instrumental) work as before. It reads at most the first 240 s of the song and writes lyrics only for that part.
  The batch takes `engine` as a shared setting and as a per-song override.
- The Music tab takes an upload or a studio result; the library / URL sources are in Song recreate (the generate request also accepts `refs.audio = {"song_id": ...}`).

## Rules and notes
- **Licence (informational, never a gate)**: YuE2-3B and SheetSage2 weights are **CC BY-NC 4.0** (non-commercial; individual creators may monetise outputs per the YuE2
  repo, companies need a licence from M-A-P); code Apache-2.0. The entry is labelled non-commercial (`commercial: false`). the author's legal team handles licences.
- **Cover rights (informational)**: a cover keeps the source melody, so releasing it needs a cover / mechanical licence from the song's rights holders. The result card,
  the run notes and the entry note say so, in every lyrics mode.
- **Text**: the style line and the lyrics go through the text guard at submit (and again on retry); the style line never imitates (`in the style of`, `sounds like`,
  `by <Name>`) and, when the source came from the library, never contains the source's title or artist (a genre word such as "Blues" is not a name). Song recreate builds the
  style from the genre card, so no artist or song name ever exists in it. Style at most 400 characters, lyrics 2000.
- **Instrumental**: the adapter Plenio uses (`ar_lora_inst_v3abc_comfyui`) is not on this box. Instrumental uses the `music:yue2` workaround (non-vocal tags, "no vocals"); the model may still sing.
- **Known model weaknesses** (model card notes): covers copy the detected notes closely (3-track-MIDI feel, no portamento), synthetic voices, limited genre knowledge.
- **Availability**: the entry is listed unavailable, with the exact steps, when `checkpoints/yue-music/yue2_3b_bf16.safetensors` or `audio_encoders/music/sheetsage2_bf16.safetensors` is missing
  from `a local folder`, and a render on a port without the nodes fails with the same steps. The three nodes are core ComfyUI: a port lacking them needs a restart onto the
  ComfyUI core (`systemctl --user restart <unit>`; ask first, queue empty). All three live ports (a local port, a local port, a local port) had them on 2026-10-17.

## Checks
- `python3 scripts/lanes/validate_yue2_graphs.py [--port a local port]`: read-only GETs of `/object_info/<class>`; all three graphs (whole song, excerpt, instrumental) passed on  a local port,  a local port and
   a local port on 2026-10-17 (every class, required input, link type, range, and the checkpoint / encoder names in the port's lists). A saved snapshot is `tests/studio/data/yue2_cover_object_info.json`.

## Smoke test (2026-10-17, session `yue2-trial`)
One job through the real `POST /api/studio/generate` handler (`Handler.do_POST`, in-process, a scratch job store; the running studio on  a local port has no newer code until it is restarted, and it was not).
Source: a 25 s excerpt (20-45 s) of the studio-generated Music 3 soul ballad from `music_knowledge_2026-10-10` (not a copyrighted download). Settings: read 30 s from 0, ceiling 45 s, seed 4242, vocals,
2 short stanzas of new lyrics, style `English, warm indie folk, soft female vocal, finger-picked acoustic guitar, gentle, 80 BPM`.

| Measure | Value |
|---|---|
| Result | done; `outputs/moe_music/yue2_cover_ae163e9e05a2ccd3.flac` |
| Time | 150 s end to end, of which about 90 s waiting for the GPU (another studio render held the lock, then  a local port was busy) and the rest the render (model load included) |
| Duration | 34.6 s (ceiling 45 s; stopped at the end of the lyrics), 48 kHz stereo flac |
| Loudness | integrated -13.3 LUFS, LRA 11.2 LU, true peak -1.5 dBTP (not mastered: Master after render was off) |
| Spectrum (share of energy) | 20-150 Hz -18 dB, 150-500 Hz -1 dB, 500-2k -8.5 dB, 2-5k -21 dB, 5-10k -26 dB, 10-12k -35 dB: low-mid heavy and dark against the source (500-2k -1 dB, 2-5k -12 dB, 5-10k -17 dB) |
| VRAM | the card was at 79 GB used before and 51 GB after (the studio room logic unloaded an idle 31.7 GB content LLM, see below); the job's own peak was **not measured** (the 18 GB in the entry is an estimate) |

**Not verified**: nobody listened (no ears here), so whether the melody follows the source, whether the words are sung and intelligible, and whether it sounds good are all unknown.
Proof level stays **recipe**.

The single smoke above finished before the pause arrived; no YuE2 job is queued or running and my VRAM reservation is released. No further GPU work was done. To repeat it, only when
every ComfyUI port is idle and `vram list_claims` shows room (peak about 18 GB + the 4 GB floor):
1. Put a short (<= 30 s) studio-made or own song in the session workspace (`a local folder`), for example
   `ffmpeg -ss 20 -t 25 -i <studio song>.flac dropped/studio_soul_25s.flac`.
2. `vram reserve` 18 GB, then run the harness idea used on 2026-10-17: POST `/api/studio/generate` with `entry_id: "music:yue2_cover"`, `refs: {"audio": "dropped/<file>"}`,
   `settings: {"seconds": 45, "vocals": "vocals", "source_s": 30, "source_from": 0}`, a one-line style and two short stanzas of lyrics. On the live studio ( a local port) this needs a studio restart first
   (author OK, empty `GET /api/admin/restart` queue); the 2026-10-17 run used an in-process handler with a scratch job store instead.
3. Measure the file (`ffprobe`, `ffmpeg -af ebur128=peak=true`, a band-energy split), note the port's peak with `nvidia-smi` during the job, `vram release`.

## Open
- Listen to three covers (own song, studio song, a different genre) and record a verdict; measure the real peak with `nvidia-smi dmon` or the port's peak during a job.
- Whether to add a library / URL picker to the Music tab's audio slot (today: upload or studio result there, everything in Song recreate).
- Instrumental adapter (`ar_lora_inst_v3abc_comfyui`, CC BY-NC) is not downloaded.
