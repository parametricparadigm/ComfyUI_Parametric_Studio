# Voice clone with consent

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- Speak typed text in a voice you saved from a short recording: your own voice, or someone else's voice whose author
  gave you permission.
- Voice-overs, narration, UGC lines and character dialogue, in a real person's voice that you are allowed to use.
- Not for public figures and not for impersonation. Those are refused on the server: see "Guards and gates".

## Step-by-step in the studio UI
1. Open the 🎙 Voice tab. The generator chip offers **OmniVoice · best clone (non-commercial weights)**, the default,
   and **ChatterBox · commercial licence (MIT), English**.
2. **First time: ＋ Add a voice.**
   - Choose a recording. About 10 s of clean speech, one speaker, no music.
   - Give the voice a name.
   - Optionally type what the recording says. If you leave it empty, it is transcribed on this box.
   - Fill in the consent block:
     - "This is my own voice", **or** "Someone else's voice, and they gave me permission" plus the author's name.
     - Answer "Is this voice a public figure?". **No** is required; **Yes** is refused.
     - Tick the statement.
   - Click **Save voice**. Saving takes about 20 s while the clip is prepared and transcribed on the CPU.
3. Pick a saved voice in the 🎙 chip. The preview player plays the stored reference, and the line under it shows the
   consent record and the transcript.
4. Type the text to speak, up to 2000 characters. It is never rewritten: the enhancer is off for voice.
5. Optional chips. "auto" means the model's rules, or else the bake-off values.
   - OmniVoice: Steps (32 is best, 16 is faster), Pace (0.9× / 1.1× / 1.25×), Language.
   - ChatterBox: Style (natural / expressive).
6. Click **Generate**. The card plays the WAV. ⤓ **Download clean** gives the scrubbed export; **Publish** runs the
   TRIBE pre-post gate as usual.
7. 🗑 deletes a voice together with its consent record. Finished clips stay. A deleted voice can no longer be used,
   not even by Retry.

## Optimal settings (bake-off evidence)
| Setting | Value | Why |
|---|---|---|
| Engine | **OmniVoice** | Best on every axis: SIM TitaNet 0.870, CAM++ 0.889 (same-speaker ceiling 0.79–0.90), WER 0.029, RTF 0.06, 3.3 GB. It read every number on the long line correctly. |
| Steps | 32 (auto) | Library default. 16 steps scored 0.830 vs 0.832 on TitaNet, so pick 16 when speed matters. |
| cfg / t_shift | 2.0 / 0.1 | Library defaults (docs/generation-parameters.md). Rules file: `ComfyUI/models/omnivoice/README_MODEL_NOTES.rules.json`. |
| Pace | auto = the reference's own rate | A slow reference gives slow speech (Nick's 10 s clip gave an 18 s long line). Use 1.1× or 1.25× to tighten it. |
| Transcript | always present | Without one, OmniVoice would download Whisper. The studio transcribes locally (faster-whisper large-v3, CPU) and refuses a voice that has none. |
| ChatterBox | exaggeration 0.5 / cfg 0.5 (natural), 0.7 / 0.3 (expressive) | Resemble README "Original Chatterbox Tips". Second on CAM++ (0.879), WER 0.039, 6.3 GB. |
| Watermark | PerTh implicit, on every clip | Resemble's watermark, CPU, bundled weights. Similarity after watermarking: TitaNet 0.836, CAM++ 0.902 (live check). |

## Reference-clip tips
- **~10 s of clean speech is best.** The OmniVoice README says 3–10 s. On the same clip, a 5 s cut lost similarity
  (TitaNet 0.832 → 0.792). The studio trims silence and cuts clips over 12 s at a pause near 10 s. When it cuts, it
  re-transcribes and says so on the voice.
- One speaker, no music, no echo, not clipped. The studio warns on clipping.
- Record in the language you will generate in. A cross-language clone keeps the reference's accent (OmniVoice README).
- Speak the way you want the output to sound: pace and energy carry over from the reference.

## Guards and gates
- **Consent gate (server side, `voice.attestation_problems` / `consent_problems`).**
  - A voice is saved only with:
    - `kind` set to `own_voice` or `owner_permission` (the latter needs the author's name);
    - `confirm: true`;
    - `public_figure: false`, given explicitly.
  - Refused: public figures; names, owners or transcripts that name a listed real public person; and impersonation
    wording such as "sounds like", "impression of", "celebrity", "famous", "deepfake".
  - Stored with the voice: the fixed statement the user agreed to, the time, the session and the clip's SHA-256.
- **Every use re-checks consent:** at generate, at retry, and in the runner right before the engine starts. A deleted
  voice, an edited consent record, or a clip whose bytes changed after consent is refused.
- **No impersonation helpers:** no preset, dataset or celebrity voices. The tab lists only your saved voices.
- **Text:** the spoken text goes through the Layer-1 text guard like every studio prompt, so naming a listed real
  person is refused. It is never sent to the enhancer.
- **Output:** the normal output guard (an audio file must be exactly one audio stream), the scrubbed download path,
  and the unchanged TRIBE pre-post gate on publish. A clip whose watermark does not verify is deleted and the job
  fails (fail closed).

## FireRedTTS3-Base as a third engine (`voice:firered`, not run yet)
- Same consent gate, same saved voices, same per-use re-check and watermark; nothing is different for the user except the
  engine chip (language list = the README's 24). It runs in FireRedTTS3's own venv (`a local folder`) through
  `studio/_fireredtts3_cli.py` mode `clone`, then PerTh-watermarks on the CPU. ~15.5 GiB per process, so the preflight wants
  20 GiB free and waits for idle ComfyUI ports.
- Licence: Apache-2.0 code and model card, but the README limits its cloning to academic research: treat as non-commercial.
- Proof: the Base `generate` call cloned a synthetic reference on 2026-10-10 (WER 0.00 / 0.00 / 0.08); the studio path has no run.

## Time and VRAM
- Saving a voice: ~20 s on the CPU (decode, trim, faster-whisper large-v3 int8). No GPU.
- Generating: a fresh the ComfyUI venv subprocess per job, offline (`HF_HUB_OFFLINE=1`). OmniVoice took 13 s end to end for
  a 4.8 s line (load ~9 s + generate); torch peak 2.2 GB, process ~3.3 GB. ChatterBox: ~27 s, ~5–6.3 GB. Same text,
  voice, settings and seed returns the existing file.
- The job holds the studio's GPU locks. The preflight (`video_edit_tools._gpu_busy`) **waits while any ComfyUI port
  has work queued**, as every studio GPU tool does, then needs peak + 4 GB free. Tick "queue when free" during long
  sweeps. The worker also stops itself if card-wide free VRAM falls under 4.5 GB.

## Known pitfalls / failure modes
- **Licences.** OmniVoice weights are CC-BY-NC (non-commercial), and its audio tokenizer is under the Boson Higgs
- ChatterBox misread "9:30" as "9,030" and "1,250" as "2,250" once each in the bake-off. Spell out numbers and times
  for it.
- The bake-off's emotional-line ranking comes from automatic checks only. Nobody has listened to the clips yet.
- OmniVoice's own number normaliser (`normalize_text`) needs `omnivoice[tn]`, which is not installed. It was not
  needed in the test. Do not pre-normalise with `wetext`: it dropped the "one" in "1,250".
- The voice store lives at `<sessions root>/../studio_voices` (per port; override with `COMFY_STUDIO_VOICES_DIR`).
  Back it up with the character store.

## Evidence
  `a local folder`. Harness in `a local folder`.
- Engine docs: github.com/k2-fsa/OmniVoice (README, docs/tips.md, docs/generation-parameters.md) and
  github.com/resemble-ai/chatterbox (README "Original Chatterbox Tips", PerTh watermark).
- Tests: `tests/studio/test_voice.py`, `tests/chatbox/test_voice_routes.py`, `tests/chatbox/js/voice_helpers.test.mjs`.
