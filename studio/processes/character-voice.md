# Character voices

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Audit: what FireRedTTS3 can do on this box
Read from `a local folder`, `INSTALL_NOTES.md`, `fireredtts3/core.py`, the harness `a local folder` and

| Question | Answer |
|---|---|
| Zero-shot cloning from a reference clip | Yes: **Base** `FireRedTTS3.generate(prompt_text, prompt_audio, text, language)` and **Instruct** `generate_tts` (ICL). Needs the clip's transcript. Ran once, 2026-10-10 (`run_test.py base`): EN x2 and ES x1 from a synthetic Kokoro reference, WER 0.00 / 0.00 / 0.08. No similarity score and no human listening were done. |
| Voice design from a description | Yes: **Instruct** `generate_voice_design(instruction, text, language)`; the model first writes a voice plan (`[gender] female [age] teenager [pitch] ...`), then speaks. Ran 2026-10-10 and 2026-10-11 (3 descriptions, WER 0.00 short, 0.15-0.21 on a long numbers line). |
| Multilingual | README: 24 languages (Arabic, Cantonese, Chinese, Czech, Dutch, English, Finnish, French, German, Greek, Hindi, Indonesian, Italian, Japanese, Korean, Polish, Portuguese, Romanian, Russian, Spanish, Thai, Turkish, Ukrainian, Vietnamese) and 21 Chinese dialects, for **cloning**. Voice design is benchmarked in **English and Chinese only**. The studio ran only English and one Spanish clone. |
| Dialogue | Not in the public API we call (single speaker per call). Not used. |
| Editing | Semantic edit (insert/delete/substitute) and acoustic edit (speed, pitch, volume) exist in Instruct. Not used by the creator. |
| VRAM | About 15.5 GiB per process (11.4 GiB resident after load, 14.1 GiB torch peak, 23.8 GiB card total in the test). Weights load fp32. Load time 6-7 s. One model per process. Own venv `a local folder`; weights `a local folder`; offline (`HF_HUB_OFFLINE=1`). |

### How it was wired before this work
- A runnable worker existed: `studio/_fireredtts3_cli.py` (design only, English, stdin JSON, one `FIREREDTTS3_RESULT` line),
  called by `tts_preset_tools.fireredtts3_design` as studio entry `tts:fireredtts3` (runner `media_more`, preflight
  `voice.preflight`, PerTh watermark, fail closed). The harness under `a local folder` is a test script, not a CLI.
- No cloning through FireRedTTS3 and no ComfyUI graph (the community wrappers are deleted, farmed, or for v1/v2).
- Character creation offered a voice panel (`Characters.js` 🗣 button → `CharVoice.js`): a preset (Qwen3-TTS Ryan/Aiden), a
  designed voice (40 example descriptions or free words) or a saved Voice-tab clone (omnivoice/chatterbox). The kit page
  (`CharKit.js`) shows the saved voice and an Edit button that opens the same panel. No dropdown form, no seed, no consistency
  pin, no "use everywhere" switch.

## What it offers now
Open **Characters → 🗣** (or the 🧰 kit → Voice → Edit).

1. **Kind**, with a line saying which engine does what:
   - *Designed voice*: FireRedTTS3-Instruct invents a new voice from the composed description. Short lines (300 characters).
   - *Preset voice*: Qwen3-TTS Ryan or Aiden; only the **delivery** dropdowns (pace, energy, mood, style...) apply, as the
     delivery instruction.
   - *Cloned voice*: a **saved Voice-tab recording that passed the consent step**, spoken by OmniVoice (best match,
     non-commercial weights), ChatterBox (MIT, English) or FireRedTTS3-Base (24 languages, not run yet).
2. **Persona** dropdown (56 ready-made archetypes that fill several dropdowns at once), **Surprise me** (rolls every dropdown,
3. **Dropdowns generated from the data file**, grouped "Delivery" and "The voice itself". The composed description is shown
   in an editable box (the author can change any word; it is then marked "edited by hand" and "Re-compose" hands control back).
   Over 400 characters the least important categories are left out and the form says which.
4. **Language** (the README's 24) and a **seed**.
5. **▶ Voice sample** (one fixed test sentence, or the sentence saved with the voice) and **🗣 Speak this line** (any line).
   Both are ordinary studio jobs, so the text guard, likeness refusal, consent re-check and watermark run as always.
6. **💾 Save as the character's voice**, then the *Pinned* box (below).

### The option catalogue (`studio/data/voice_options.json`, 529 options in 21 categories, 56 personas)
Every option has a key, a short label and the **phrase** it contributes. The first option of each category is "Auto (let the
model choose)" with an empty phrase. Edit the JSON to add options; `voice_options.load()` validates the file and refuses to
start on a bad one.

| Category | Group | Options (with Auto) | Applies to |
|---|---|---|---|
| presentation (voice presentation) | voice | 14 | design |
| language (FireRedTTS3's 24, marked) | voice | 25 | design, clone |
| accent_en (English varieties and regions) | voice | 40 | design |
| accent_l1 (English with another first language) | voice | 40 | design |
| dialect (Chinese dialects, **cloning only**) | voice | 22 | clone |
| register (voice register and pitch) | voice | 27 | design |
| timbre (timbre and texture) | voice | 39 | design |
| quirks (fry, uptalk, smile in the voice...) | voice | 28 | design |
| diction (articulation) | voice | 19 | design |
| pace | delivery | 19 | design, preset |
| rhythm (and pauses) | delivery | 19 | design, preset |
| energy | delivery | 21 | design, preset |
| emotion (baseline mood) | delivery | 38 | design, preset |
| warmth (and formality) | delivery | 19 | design, preset |
| confidence (and attitude) | delivery | 29 | design, preset |
| style (delivery style by role) | delivery | 39 | design, preset |
| volume (and projection) | delivery | 16 | design, preset |
| mouth (breathiness and mouth noise) | voice | 15 | design |
| laughter | delivery | 17 | design, preset |
| recording (recording character) | voice | 20 | design |

`character_policy.legacy_named_people` and `likeness_problem`); no "sounds like", "impression of", "in the style of";
labels and keys unique per category; accent options are neutral region or language-community descriptions; every persona
picks an age band; between 12 and 40 options per category; at least 50 personas.
Contradictions (slow pace with a fast one, soft with loud) show a warning and never block.

## Consistency: how the same voice is kept
The saved record (`<guard state>/charvoice/voices.json`) pins, per character:

| Pinned | Why |
|---|---|
| `kind`, `engine` (fireredtts3, qwen3_tts, omnivoice, chatterbox, firered) | the same engine every line |
| `description` (designed) / `speaker` + `instruct` (preset) / `voice_id` + `ref_sha256` (clone) | the same words or the same reference |
| `options`, `persona`, `description_edited` | the dropdown keys, so the voice can be re-created and edited later |
| `seed`, `language`, `sample_text` | the same sampling seed and language; one fixed test sentence |
| `pin` | a 16-character hash of all of the above: if it is unchanged, the voice is unchanged |
| `anchor` + `use_anchor` (designed only) | a rendered sample copied into `charvoice/anchors/<id>.wav` with its sha256 |
| `use_everywhere` | default ON once saved |

Every request built from the record (`speak_payload`) carries the pinned seed and language; Deliverables, the lyric reader and
the Voice page all go through that function.

**Designed voices drift between lines.** A voice-design call re-plans the voice for each line (the plan is generated text), so
the same description can come back a little different for different sentences. The seed pins the sampling, not the plan.
So after saving, press **▶ Voice sample** and, when it finishes, **📌 Pin the last sample as the anchor**
(`POST /api/studio/charvoice/{id}/anchor {job_id}`). From then on every line is **cloned from that clip** with FireRedTTS3-
Instruct's ICL (`generate_tts`), so it keeps the anchor's voice. The anchor is dropped automatically if the words, seed or
language change; it is re-hashed before every use and an altered file is ignored (the line then falls back to words + seed).
The client never sends a file path: the job carries only the character id and the server resolves the anchor.
**The anchor clone is wired and tested with fakes only. Whether it keeps the voice better than words + seed is unproven.**

**Auto-lock on save (author 2026-10-17: "for characters with the voice their voice should auto lock to them").** Saving a voice locks it:
- *Designed voice:* the server pins a finished plain sample of exactly this voice (same words, seed and language; the panel sends its
  last matching sample as `sample_job_id`, else the newest in the session is searched) in the same save; if none exists it queues the
  sample (`queue_when_free`, same guards) and records `lock_pending` on the voice. The lock completes when that job finishes (the
  studio's on_done hook, or the next read of the voice) and the panel and kit page show `locking...` then `locked to the sample`.
  (`lock_error`, shown as `not locked: <reason>`). After a studio restart (`charvoice.resume_on_boot`, a boot thread like the Signature
  10 resume) a finished sample is pinned, a cut-off one is queued once more (a second cut-off gives up with the reason). Changing the
  voice while the lock waits drops the old wait; a late old sample is ignored.
- *Preset and consented clone:* fixed voices by construction; the record just shows `locked (a fixed voice ...)`.
  **🔒 Lock this voice** action below.
- Makers that speak with a character voice: Deliverables (and Content Studio through it) and the lyric reader. All build the request
  with `speak_payload` from the full record, so they carry `anchor_character` and the pinned seed; the Deliverables run says
  `locked to the saved sample` or `not locked: words + seed only` per shot, and a missing/changed sample is said on the line's card
  (`voice_note`). The music video, Recreate and Fusion work from a song/sound and do not speak with character voices.

Lock this voice with the last sample. The panel sends the form and the job to `POST /api/studio/charvoice/{id}/lock {voice, job_id}`:
the server validates the voice, checks the sample is a finished plain designed-voice sample of exactly that voice (same words,
same seed, not itself an anchor clone) and only then saves the voice and pins the sample. Nothing is half-saved on a mismatch.
"Speak this line in the SAVED voice" speaks any line with the saved seed, language and the lock (the older "Speak this line"
button speaks the form's voice without the lock, by design: it is a preview). Label: recipe, not yet judged by ear.

What is guaranteed (the panel says it too): same engine build + same words + same seed + same line should give the same sound
(sampler seeded; a repeat run has not been checked). Not guaranteed: the same voice on another line or seed.

**Clones** are consistent by construction: the same saved reference clip and transcript, the same seed; the consent record is
re-checked (and the clip re-hashed) on every use.

### When the voice is not used (never silent)
Deliverables run notes, the Content Studio plan ("assumed" lines) and the kit page now say `voice not used because ...` (voice set not
to be used everywhere, a speaker with no voice, a LoRA template, lip-sync unticked, a two-person shot, a line over 300 characters
for a designed voice). The panel plays the last sample and shows waiting / failed reasons. See
[the diagnosis, section 7](../research/charvoice-diagnosis-2026-10-17.md).

### Use everywhere
`use_everywhere` (checkbox in the Pinned box, `POST /api/studio/charvoice/{id}/use_everywhere`) is ON by default once a voice is
saved. `charvoice.active_voice(cid)` is the one call that honours it.
- **Deliverables**: when the request has no `voice_lock` and every character who speaks a one-person talk shot has an
  active saved voice, the voice-lock lip-sync defaults **ON** (`deliverables.voice_lock_default`; run option
  spoken shot, two-person shot, line over the lock length, refused or failed voice job, no ffmpeg) still applies and falls back
  to H3's own speech with a run note. The H3 "voice words" for non-locked shots also skip a voice that is not used everywhere.
  The Deliverables UI shows the box ticked by default for such a cast and sends `voice_lock: false` when it is unticked.
- **Content Studio**: it creates its runs through the same Deliverables start, so it gets the same default (its own
  `dialogue.voice_lock: true` still forces it).
- **Lyric reader**: a character picked as a reader speaks with the saved voice including the pinned seed and anchor.
- **Voice page**: the character's sample is an ordinary voice result card.
- **Not wired**: Recreate's sound input takes a finished voice result (pick the character's sample there) and the music video
  sings a song; neither makes a character speak, so there is nothing to switch.

## Clone consent path (unchanged gate)
Clone mode embeds the Voice tab's `VoicePicker` and its **Add a voice** form: a recording (about 10 s), a name, the attestation
("own voice" or "someone else's voice, they gave permission" with the author's name), "public figure?" must be No, and the tick.
The server (`voice.attestation_problems`) refuses public figures, named real people and impersonation wording, and stores the
statement, time, session and clip hash. `charvoice.validate` accepts a clone only for a voice that `voice.usable_voice` passes
now; the record also pins the clip hash; every line re-checks consent in `_studio_generate` and in the runner right before the
engine starts; a deleted voice or changed clip is refused. The creator adds no other way to bring in a voice, and cloning a
real person without those answers is not possible. All outputs carry the PerTh watermark.

## FireRedTTS3 as a studio voice entry
- `voice:firered` (Voice tab, "Clone a saved voice" group; label ends "(not run yet)"): FireRedTTS3-**Base** clone of a saved
  voice, 24 languages, in its own venv. Same consent gate, offline, preflight (peak 16 GiB + 4 GiB headroom, waits for idle
  ports), PerTh watermark on the CPU, fail closed. Listed unavailable with the reason when `a local folder` is missing
  (`COMFY_FIREREDTTS3_PYTHON` overrides).
- `tts:fireredtts3` (designed voice) now also takes a `language` and, for the creator, a hidden `anchor_character` field.
- Worker `_fireredtts3_cli.py` modes: `design` (default, the tested script; now passes the pinned seed to the model's own
  `seed` argument, which the old worker left at the library default 2) and `clone` (`model` base or instruct).
- Start/setup needs: the venv and weights above; nothing to install. Run order: gate on a quiet GPU (idle ports, >= 30 GB free),
  a vram claim, then the studio job. Start no server by hand.

## Wired vs proven
| Piece | Proof level |
|---|---|
| Option catalogue, validator, composer, randomiser | unit-tested (shape, counts, safety rules, determinism). **Whether a given combination sounds like its words is unproven**; accents and quirks are guidance to the model, not guarantees |
| Record, pinning, `pin`, use_everywhere, consent gate on clones | unit- and route-tested with fakes |
| Deliverables default lock | tested with fake voice/lock jobs (ffmpeg makes tiny clips); not rendered live |
| FireRedTTS3 voice design (English) | **verified** earlier: spoken and ASR-checked 2026-10-10/11 (by the old worker, default seed) |
| FireRedTTS3 voice design with a non-English language, the pinned seed argument, composed (long) descriptions | **wired only**; design is benchmarked in EN/ZH only |
| Anchor clone (Instruct `generate_tts` from a pinned sample), 🔒 Lock route and panel | **wired only**, never run on the GPU; the panel was driven in a browser against the real routes with fake jobs (2026-10-17) |
| Designed voice, English, composer-made description + seed | **verified** 2026-10-17: two real samples, WER 0.00, PerTh 1.0 (unmarked speech scores 0.0) |
| `voice:firered` / worker `clone` mode | **wired only**; the underlying Base call ran in the harness, the studio path (consent, watermark, runner) has not |
| Qwen3 delivery from the dropdowns | wired only; the preset instruct accepts free words, the composed phrasing is untested |
| UI form (`CharVoice.js`) | syntax-checked and helper-tested; not opened in a browser (the studio was not touched) |

## Decisions for the author
1. Is the anchor clone the right default for designed voices (it is ON once pinned)? Alternative: seed only.
3. Whether to restart the studio to make the new UI and routes live.
4. The 21 categories / 529 options are first-pass wording; the real test is listening to a sample set (suggested: five personas,
   English, one fixed sentence, then five lines per voice with and without an anchor).

## Tests
`tests/studio/test_voice_options.py`, `tests/studio/test_character_voice.py`, `tests/chatbox/test_charvoice_routes.py`,
`tests/studio/test_charvoice.py`, `tests/studio/test_charvoice_diagnosis.py` (one test per bug of the 2026-10-17 diagnosis), `tests/studio/test_deliverables_lipsync.py`, `tests/chatbox/js/voice_creator_helpers.test.mjs`.
