# Dub studio

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What it does
1. **Source.** A finished studio video, a Clip Studio clip, or an upload (up to 240 s and 400 MB, with sound). The **rights box comes first** ("I own this video or have the author's
   permission to dub it, and the people in it are fictional or have agreed"); it is recorded with the run and written into the package manifest.
2. **Transcript.** Clip Studio's Whisper worker (faster-whisper large-v3 int8 on the CPU, word times); the spoken language is detected. A content check of the video runs first
3. **Dub lines.** One per sentence (`clip_logic.build_sentences`), each with a **slot**: from when the speaker starts to when the speaker ends plus up to 0.6 s of the pause after
   (never closer than 0.05 s to the next line). At most 80 lines. A source line the text guard refuses is not translated or spoken.
4. **Translation** by the local writer (`gamebuilder.llm.chat_json`). One writer load for **all** languages. Per line a **length budget in the language's own unit**
   (syllables; characters for Chinese, Cantonese, Japanese, Korean, Arabic, Hindi, Thai) for the slot: `target` (what the writer is asked for) and `max` (what the voice can say at
   1.2x). Rules in the prompt: literal-friendly, keep names and numbers, keep tone, never merge or split lines. **Two passes:** lines over `max` are sent back once to be shortened;
   a line that still does not fit is **flagged** (never forced). Advice chips: a name or number of the source missing from the translation; a line over the voice's 300-character limit.
5. **REVIEW STOP.** The run stops with status *waiting*. For every language the author reads each line (tick *read*, or edit it: an edit counts as read, is guarded and re-fitted, and can be
   reverted to the machine text). **Flagged lines are different (author decision 2026-10-17):** a line is flagged when it does not fit its slot (*over* / *long*), did not fit when spoken
   (*fast*, *clipped*, *silent*), or its original was heard with low confidence (mean Whisper word probability under 0.6). A flagged line cannot be ticked or bulk-approved: it has to be
   opened and **edited, or accepted one by one** (*Accept as is*, `POST .../line/{n}/accept`; the language panel lists them with a counter, "x of y flagged lines accepted"). Both
   *Approve all lines of X...* and *Approve all languages...* **refuse with a message until every flagged line is accepted or edited**; they cover the unflagged lines only. A language is approved
   when every line is read or accepted, or with that language's own *Approve all lines of X...* confirm. *Approve all languages...* is a third, separate confirm (server needs `confirm` and
   `all_languages`). A line with no text blocks approval until it is typed. Changing anything after approval reopens that language (lines flagged after speaking then need a decision too).
   **Nothing is spoken before this**; a batch cannot skip it (tested: zero voice requests until approval and *Make the voices*).
6. **Voice.** *Make the voices* (its own press) speaks every line of every approved language, one language after the other, line by line, as **ordinary studio jobs**
   (`_studio_generate`, so the text guard, the likeness refusal and the PerTh watermark all run). The voice is exactly one of:
   - a **character's saved voice** (`charvoice`: designed or preset, with its auto-lock anchor when it has one; the saved seed is used), or
   - a **designed voice** picked here (the voice builder's library), or a **preset speaker** (Ryan / Aiden: English only in this studio, so a preset is refused for any other language).
   **Refused:** a cloned recording (even a character's saved clone), a voice id, "the voice in the video", a character made from a real person's photo. The locked sample is an English
   clip; cloning it into another language is untested, so the page has a *use the voice lock* tick and a note.
7. **Fit.** Each spoken line is trimmed of silence and time-stretched into its slot with `sound_dsp.time_stretch` (phase vocoder, pitch kept) in **0.85-1.2x**. Slower than 0.85x is never
   done (the rest of the slot stays silent). Faster than 1.2x is capped and the line is flagged *fast*; a line that would run into the next one is cut there with a 30 ms fade and flagged
   *clipped*. The rate and flag are shown on the line and written into the manifest.
8. **Mix.** The dub track is assembled on a silent bed. **Without a speech stem the original is ducked 22 dB under the dub inside the speaker's own lines (padded, smoothed) and sits
   at -3 dB elsewhere. Its speech is lowered, not removed; the page, the run and the manifest say so.** With *separate and remove the original speech* ticked (Hybrid Demucs on the CPU
   through the song-recreate vocal worker, `_vocals_cli.py`; never run on this box) the bed is the original minus the vocals. The sum is mastered with `sound_dsp.master` to
   **-14 LUFS / -1 dBTP** (the report is stored: before, after, true peak, limiter reduction).
9. **Captions** in the target language: ASS word by word over the interval each line was really spoken in (the TTS gives no word times, so the words share the interval in proportion
   to their length), Clip Studio's caption styles and safe margins, a font that has the script (Noto CJK / Naskh Arabic / Thai / Devanagari; fallback DejaVu), Turkish never upper-cased.
   An `.srt` is written too.
10. **Export** per language: the mp4 (published as a "videofinish" studio job, so the output guard reads it), the `.srt` and the dub `.wav`.
11. **Lip-sync (optional).** Per finished language, **author-pressed, one language at a time, never automatic**, with a second consent tick ("The person whose mouth is re-synced is a fictional
    character, or has agreed...": re-syncing a real person's mouth is a deepfake). It calls `latentsync_tools.latentsync(video, dubbed wav)` (GPU, ~18 GB, its own preflight: a busy ComfyUI
    port or short VRAM refuses and the refusal is shown). LatentSync takes clips up to **20 s**; a longer video is refused with the reason (cut a shorter piece with Clip Studio). The
    inputs are copied under the ComfyUI outputs folder (the lip-sync tool reads media roots only) and removed afterwards; the captions are burned onto the result. The plain dub is kept next to it.
12. **Send.** *Send* makes one Drive folder through the Content Studio package route (`send_out.send_package`: a new folder for that send, one view-only link, one mail, **never attachments**)
    with, per language, the mp4 (and the lip-synced mp4), the `.srt`, the dub `.wav` and a manifest (rights, voice, per-line text and speed, mix, limits). The TRIBE pre-post check is on by default.

## Supported languages (verified in the code and docs, not from memory)
Exactly the **24 languages of the FireRedTTS3 README** (`tts_preset_tools.FIRERED_LANGUAGES`, `voice_options.json` `firered_languages`, KB `FIREREDTTS3.md`; a test keeps the three equal):
English, Arabic, Cantonese, Chinese, Czech, Dutch, Finnish, French, German, Greek, Hindi, Indonesian, Italian, Japanese, Korean, Polish, Portuguese, Romanian, Russian, Spanish, Thai, Turkish,
Ukrainian, Vietnamese. **Anything else is unsupported and refused by name** (Hebrew, Swedish, Danish, Norwegian, Hungarian, Bulgarian, Persian, Bengali, Tamil, Urdu, Swahili, Tagalog,
Malay, Catalan and 30 more are listed in `dub_langs.UNSUPPORTED`; a language that is in neither list says the supported ones). The source may be any language Whisper hears.

What each language's proof is (the table the page shows):
| Tier | Languages | Meaning |
|---|---|---|
| verified | English | a designed voice was spoken and ASR-checked (WER 0.00, 2026-10-10/11 and 2026-10-17) |
| upstream | Chinese | the README benchmarks voice **design** in English and Chinese; not run on this box |
| ran_once | Spanish | only the **clone** path ran once (WER 0.08); design in Spanish has not run |
| listed | the other 21 | named by the README for cloning; design not benchmarked; nothing ran here |
Every tier describes the **engine**; no finished dub exists in any language. The text normaliser (`wetext`) covers Chinese and English only; other languages get basic cleaning (KB), so
numbers and abbreviations in other languages are read less reliably: write numbers as words if a line sounds wrong.

## What was reused (read-only)
`charvoice` (records, `speak_payload`, `validate`), `_fireredtts3_cli.py` / `tts:fireredtts3`, Clip Studio's `clip_media.transcribe` and `clip_logic` (sentences, caption styles, ASS builder,
safe margins), `sound_dsp` (`time_stretch`, `mix_at`, `master`, `decode`, `write_wav`, `trim_silence`), `latentsync_tools`, `video_finish` (publish job), `send_out.send_package`,
`character_policy.prompt_problems`, `recreate.source_guard`, `songrecreate`'s vocal worker. No existing module was edited except the shared registration files (server routes, mode list, app,
CSS, process card, readiness, README row).

## Batch behaviour
Stages run for all languages together: prepare (once) -> translate every language (one writer load) -> **review** -> voice every approved language back to back -> fit, mix, captions, export
(CPU) -> optional lip-sync one at a time. Per-language status (*waiting, translating, needs your review, approved, speaking, mixing, done, failed, skipped*); a failure is isolated to its language
(three failed lines in a row stop that language; the others carry on) and **Resume** retries only what failed (finished lines keep their audio, so nothing is spoken twice). **Pause** stops after
the line being spoken; **Cancel** keeps the finished lines. A run that was working when the studio restarted shows *interrupted* and **nothing restarts by itself** (the boot does not touch it);
Resume is the author's press. A video already in a requested language skips that language.

## Estimates (every number is an assumption until the proof run)
Whisper 0.3 / 0.6 / 1.0x the video; one dub line per ~4.5 s of video; writer: 90 s load + 45 s x 1.4 per batch of 10 lines per language; voice: 15 / 25 / 60 s per line (a FireRedTTS3 process
per line, ~7 s load, 15 GiB); build: 20 s + 6 s per video second per language (the guard check); lip-sync 2 / 5 / 15 min per language. Speaking rates per language (`dub_langs.SUPPORTED[..].per_s`)
are typical conversational values; the proof run replaces them with measured seconds per unit.

## Routes (`/api/studio/dub/*`)
GET `config`, `voices`, `runs`, `runs/{id}`, `runs/{id}/lang/{code}/srt`. POST `plan`, `start`, `runs/{id}/cancel|pause|resume|voice|approve_all|check|send|lipsync`,
`runs/{id}/lang/{code}/approve|unapprove|retranslate`, `runs/{id}/lang/{code}/line/{n}` `{text}`, `.../line/{n}/approve|unapprove|accept|revert`. `{code}` is the language code (`es`, `zh`, `yue`...).

## Safety
  TRIBE gate on the send; the dub `.wav` / `.srt` are plain derived files (the PerTh mark of each spoken line is not guaranteed to survive stretching and mixing: unmeasured).
- Nothing posts anywhere. The only outward action is *Send*, the author's press.

## Honest limits
- **Translation quality is unmeasured.** The writer is a local LLM; a native speaker must read every language before posting. Idioms and humour will be literal.
- **TTS prosody and identity.** Designed voices are only benchmarked in English and Chinese. The same words can sound like another person on another line unless the voice is locked, and cloning an English lock sample into another language is untested.
- **Time-stretching** with a phase vocoder smears consonants a little; lines needing more than 1.2x are flagged, not fixed. The fit uses a *spoken-length estimate* for the translation, not a measured one, so some lines will turn out too long only after they are spoken.
- **One voice for every speaker** (no speaker separation).
- **Ducking, not removal,** unless the CPU separator is ticked; the separator is untested and its subtraction leaves artefacts.
- **Lip-sync:** 20 s clips only; LatentSync is trained mostly on English speech and its sync in other languages is unknown; it needs ~18 GB of VRAM.
- Whisper hears the source once; a mis-heard word is translated as heard (the review shows the original next to every line).

## Decisions for the author
1. (Decided 2026-10-17: the English locked sample stays the default when a voice has one; the tick turns it off.)
2. (Decided 2026-10-17: lip-sync above 20 s stays refused.)
3. (Decided 2026-10-17: a character's own clone stays refused.)
4. (Decided 2026-10-17: flagged lines must be accepted or edited one by one; see step 5.)

## GPU / CPU proof plan (do not run until the card is free; nothing here has run)
`scripts/dub_proof.py` (prepared, **not run**; it drives the studio's own routes and refuses unless the GPU gate is clear). Case `plain`: one **20 s** clip of your own character talking
(author-supplied or generated), rights box ticked, **Spanish + French**, the character's saved voice, captions on. The script runs plan -> start, then *stops at the review* and prints the lines;
the author reads and approves (`approve`), then `voice`, then `report`. Case `lipsync`: the same run afterwards with the consent tick, Spanish then French. To record: time per stage (`steps[*].secs`,
per-line voice seconds -> measured seconds per unit per language), the stretch rate per line, loudness (-14 +-1 LUFS), and what the author heard.
What to judge (write who judged into `readiness.json` `dub.studio` evidence):
1. A native speaker reads both translations against the original: meaning, names, numbers, register.
2. Each line starts with its original and ends before the next; none sped past 1.2x without a flag.
3. One voice across the lines (with the lock, and with the lock ticked off, for comparison).
4. The original speech is only faintly audible (ducked) and the dub is clear; loudness reads -14 LUFS.
5. Captions: the right script, inside the safe margins, roughly in time.
6. Lip-sync: the mouth follows the new audio, the face is not degraded, captions and audio intact.
Pass criteria for "judged": 2 of 2 languages read as faithful by a native speaker, no unflagged overrun, loudness within +-1 LU, one recognisable voice, every guard step recorded.
Anything else is recorded as the verdict and this document is corrected.

## Tests
`tests/studio/test_dub.py` (language table equals the FireRedTTS3 list, unsupported refused, length model, stretch range, mix and master on tones, SRT/ASS, voice rules, review stop, approve-all
confirms, edits, second pass, full pipeline with real ffmpeg, locked-voice tick, isolation, pause / cancel / interrupted, stems, lip-sync consent / 20 s / one at a time, package),
`tests/chatbox/test_dub_routes.py`, `tests/chatbox/js/dub_helpers.test.mjs`.
