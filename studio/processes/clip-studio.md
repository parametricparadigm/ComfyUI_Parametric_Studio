# Clip studio

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What it does
1. **Source** (rights box first, always): a link (https only, hosts in `config/clip_studio.json`), a dropped video file, or a finished studio video. Up to 3 hours, 1080p cap, 6 GB.
2. **Run** (one saved, resumable run like Pictures / pose set / timelapse): fetch, audio, Whisper transcript with word times, windows of whole sentences, writer scoring, the best N clips, then per clip: crop, cut, loudness, captions, content check, cover, publish.
3. **Contact sheet**: every clip with its video, score chips, crop note, hook line, posting text, and Keep / Drop / Re-cut / Re-caption / Replace / Rewrite text / Download clean / Wipe + send. A transcript viewer lets you click a first and a last sentence and press **Clip this part**.
4. **Sends**: per clip the existing ✉️ Wipe + send; **Send kept clips** = the Content Studio route (`send_out.send_package`: a fresh Drive folder, one view-only link, one mail, never attachments, the TRIBE pre-post check on by default). Nothing posts anywhere.

## Rights attestation (required)
A checkbox: **"I own this video or have the author's permission to clip it"**, plus an optional note. Without it `plan` and `start` answer 403 and nothing is downloaded, read or stored (tested, including a refused URL run that never calls the fetcher). It is stored with the run (`rights`: text, note, time, source), shown on the run page, and written into the top of `captions.md` that travels with a sent package ("The studio does not check or grant rights"). The studio cannot verify it; it records it. The wording is a decision for the author (below).

## What was reused (audit 2026-10-17, read before writing)
| Need | Reused | Where |
|---|---|---|
| yt-dlp download | `recreate.fetch_url` / `ytdlp_video_cmd` (no cookies, no config, no playlist, mp4 up to 1080 lines, caps, provenance), `song_library.run_with_fallback` (the long-form video 403 / PO-token retry across `FALLBACK_CLIENTS`), `SL.stream` (own session, cancel kills the group), `SL.validate_url` | `recreate.py`, `song_library.py` |
| Whisper | faster-whisper large-v3 int8 on the CPU from `a local folder`, run in the face venv as a subprocess (the pattern of `_vocals_cli.py` / `_voice_cli.py`); word timestamps + VAD are new in `_clips_cli.py` | `_vocals_cli.py` |
| Writer LLM | `gamebuilder.llm.chat_json` (the content chain, its own VRAM gate; no model is evicted), one load per run (all scoring and pack calls back to back, the batch-phases idea) | `llm/content.py`, `batch-phases.md` |
| Export pack | `deliverable_series.export_pack` (its prompt, its text guard, its fallback) fed a clip as the "run" | `deliverable_series.py` |
| Loudness / ffmpeg | `song_library._ff`, `_loudnorm_json`, `loudness`, `mix_into` (library song under the speech, sidechain ducking, -14 LUFS, mux only) | `song_library.py` |
| Probe, scene cuts | `recreate.probe_video`, `recreate.scene_cuts` | `recreate.py` |
| Platform safe margins | `formats.caption_layout` on the short-video / Shorts / vertical short presets (largest margins of the chosen platforms) | `formats.py`, `platform-formats.md` |
| Thumbnail | `thumbnail_tools.best_frame` (sharpest of 12 frames) and `compose` (bold title, 1280x720) | `thumbnail_tools.py` |
| Face model | insightface `buffalo_l` on the CPU (detection + the 106-point landmarks), inside a `guard_state.cpu_slot` like Recreate's face pass | `_recreate_cli.py`, `facescore.FACE_PYTHON` |
| Publish as a studio result | `video_finish.register_publish` + the `videofinish` CPU job (the output guard reads every clip; Download clean, Wipe, Send work on it) | `video_finish.py` |
| Send | `publish.publish_job`, `send_out.send_file`, `send_out.send_package`, `package_prepost`, `content_studio.classify_gate` | `send_out.py`, `content_studio.py` |
| Run machinery | the timelapse / pose-set pattern: JSON per run, a thread, `get()` detects an interrupted run, cancel / resume | `timelapse.py` |
| Trending sounds | the song library pick (`SongPicker`, `song_library.mix_into`); a trending sound that was fetched is a library song | `trending-sounds.md` |

**Not reused, and why:** the Deliverables `captions` step (`post:captions`, pp's `_ass` over the speaches Whisper service) burns 4-word groups from a service that is not guaranteed to be up and has no word highlight; Clip Studio writes its own ASS (word-by-word, 6 styles) and uses the same margins. `facescore` / `character-faceless-crops` find and crop faces for a character; the speaker follow needs mouth movement over time, which they do not give. Output-guard scene sampling is the guard's own, not a clip-boundary detector.

## What is on this box (checked read-only 2026-10-17)
In the face venv `a local folder`: faster-whisper 1.2.1, insightface 2.0 with `a local folder` (incl. `2d106det.onnx`), opencv 5, mediapipe 0.10.21 (its bundled face landmark tflite), ultralytics 8.3.224, scenedetect 0.7.1, silero-vad, webrtcvad, whisperx 3.8.5, pyannote.audio 3.3.2 (no diarisation weights checked). yt-dlp at `a local folder`, ffmpeg 9.0 with libass, loudnorm, sidechaincompress, cropdetect. **Nothing needs installing or downloading today.**

**Tracker choice: insightface mouth movement.** The face worker samples the clip at 5 per second; per face the vertical spread of the lip landmarks over the face height is a mouth-opening number; the face whose number varies most over about a second is the speaker; the camera only switches when another face has been at least 1.6 times as active for 0.6 s (no ping-pong). It is a heuristic, not an audio-visual model: a person who nods or yawns can be followed, and two people talking over each other follow the louder mouth. mediapipe face mesh and a diarisation model were not chosen (mediapipe would be a second face stack; pyannote needs weights this box does not have verified). A decision for the author below.

## Degrades without extra models (nothing is installed by the studio)
| Missing | Effect | Queue command (for the author; syntax not run, check `dlq status`) |
|---|---|---|
| face python or `2d106det.onnx` | clips are centre-cropped (cropdetect removes black bars), each card says "centre crop: no face tracker on this box"; a face in under 30 % of the samples also centre-crops with that reason | `a local folder add clip-buffalo-l - <<<'mkdir -p a local folder && cd a local folder && curl -L -C - -o buffalo_l.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip && unzip -o buffalo_l.zip -d buffalo_l'` |
| Whisper large-v3 folder | the run stops at the transcript with this command in the error; no clips without a transcript | `a local folder add clip-whisper-large-v3 - <<<'hf download Systran/faster-whisper-large-v3 --local-dir a local folder` |
| yt-dlp / a blocked long-form video | links fail with the reason; drop the file instead; the 403 retry tries 5 player clients first | `a local folder -U` |
| the writer LLM (no room or down) | the run waits for room up to 12 minutes, then the step fails with the scores kept; **Resume** continues. Or start with the writer off: heuristic ranking, titles from the transcript, no GPU | none |

## Safety
- Text guard (`character_policy.prompt_problems`) on the typed focus and rights note, the writer's titles / hooks / hashtags (a refused text is replaced by the transcript's own words, with a note), the pack (its own guard, then the plain template), a typed hook, a typed title for a picked range.
- Every clip is published as a studio job: the output guard reads the file; nothing is served or sent that did not pass.
- This feature generates no people. No automatic posting; the only outward actions are a click on Wipe + send (single file route, exempt from the pre-post gate like every private send to the author) or Send kept clips (gate on by default; a blocked clip is left out and listed; a gate that cannot run needs the author's "send without it").

## Estimates (every number is an assumption until the proof run)
Transcription: faster-whisper large-v3 int8 on the CPU at 0.3 / **0.6** / 1.0 x the audio length (no measured number for long audio exists in the KB). Audio extract 1/200 of the video, loudness curve 1/400. Writer: load 90 s, 45 s per 6 windows, 20 s per clip's text. Per clip: x264 re-encode 0.15 s per clip second, captions 0.15, face tracker 0.5, the guard check `video_finish.GUARD_S_PER_VIDEO_S` = 6 s per second (also an assumption there; the plan counts the guard once per clip although the content check and the publish job both run it: whether they share the guard's segment cache is not verified), 15 s overhead. Examples from `clip_logic.estimate` (8 clips of 45 s, tracker on): a 10 min video about 58 min, a 1 h video about 89 min, a 3 h video about 2.7 h; most of the clip stage is the assumed guard time. **GPU: the writer LLM only** (the content model, about 24-33 GiB when it has to load, plus the 4 GiB reserve; the run waits for room and evicts nothing). Whisper, the tracker and ffmpeg are CPU; the box was at load 26 on 32 cores while this was built, so wall time depends on what else is running.

## Routes (`/api/studio/clips/*`)
GET `config`, `plan?...`, `runs`, `runs/{id}`, `runs/{id}/transcript?from=&to=&q=&limit=`, `runs/{id}/candidates`, `runs/{id}/clip/{n}/cover|thumb`. POST `plan`, `start`, `runs/{id}/cancel|resume|pick|check|send`, `runs/{id}/clip/{n}/recut|drop|keep|recaption|replace|rewrite|send`. `send` without `confirm: true` returns the summary only.

## Decisions taken (change on request)
- Default **8 clips of about 45 s** at 9:16; lengths 15 / 30 / 45 / 60 / 90 (a window is 0.6x to 1.3x the length, never over 90 s).
- A clip is **kept by default**; Drop removes it from the send and the pack; "Send kept clips" sends kept, finished clips.
- Posting texts for short-video, Shorts and vertical short come from the Deliverables export-pack writer (`long-form video` is written too but not shown).
- Captions are written in the spoken language; titles too (the writer is told to).
- Scene cuts are off by default (slow on long videos, skipped over 30 minutes).
- The 3 h cap and 1080p cap come from `config/clip_studio.json`.

## Decisions for the author
1. **Rights wording.** The box text is "I own this video or have the author's permission to clip it". Does the legal team want a different line, a recorded licence field, or a stricter rule for third-party long-form video links (for example only your own channel)?
2. **Defaults.** 8 clips x 45 s, kept by default: right?
3. **Tracker.** insightface mouth movement now. Worth a proof against mediapipe face mesh or an audio-visual model (not installed) after the first run?
4. **Pre-post gate on a clip package** stays ON (as for Content Studio packages). Each clip is checked by TRIBE, which is slow; say if you want it off for clips.
5. **Whisper speed assumption** (0.6x): confirm or replace after the proof run.

## GPU / CPU proof plan (do not run until the card and the CPU are free; nothing here has run)
One 10-minute talking video that is **author-owned or public domain** (an interview of yours, or a public-domain lecture), 16:9, 1080p, one or two speakers, with ordinary speech and at least one natural topic change. Drop the file (no download), tick the rights box and write the real source in the note.
Time per stage from the run's `steps[*].secs` and `stats.transcribe_s` (the estimate for this setup: transcript 3.6 min at 0.6x, writer about 5 min, 3 clips about 11 min, mostly the assumed guard time):
| Stage | Estimate | Record |
|---|---|---|
| audio extract | seconds | `steps.audio.secs` |
| Whisper | 3-10 min (0.3-1.0x) | `stats.transcribe_s`, real-time factor |
| windows | seconds | `steps.segment.secs` |
| writer | load 90 s + 45 s per batch | `steps.write.secs`, writer load count |
| per clip | tracker 0.5 s/s, cut 0.15 s/s, captions 0.15 s/s, guard 6 s/s (assumed) | wall time per card, the guard share |
What to judge (who judged and what each saw goes into `readiness.json` `clip.studio` evidence):
1. **Clip boundaries at sentence ends:** open each clip, listen to the first and the last second; no clipped word, no cut mid-sentence, a natural opening.
2. **Hook quality:** is the title / hook line true to what is said and would it stop a scroll; is the best moment of the video among the 3 (compare with the candidates list); heuristic arm versus writer arm.
3. **Caption sync:** the highlighted word matches the spoken word within a frame or two across the whole clip; the caption stays in the platform safe margins (check against the short-video / vertical short overlay screenshot).
4. **Crop follows the speaker:** on a two-person stretch the crop pans to whoever talks, with no jitter and no ping-pong; the face stays inside the frame; the crop chip says "follows speaker".
5. **Loudness:** each final file reads -14 LUFS +-1 (`song_library.loudness`), no clipping, speech clear with a song laid under it (run once with a song).
Pass criteria for "judged": 3 of 3 clips start and end cleanly, caption sync within 2 frames, no crop jitter, loudness within +-1 LU, every guard step recorded. Anything else is recorded as the verdict and the doc is corrected.
