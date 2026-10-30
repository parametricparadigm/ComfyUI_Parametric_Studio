# Long prompts for H3

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


Status: merged on `an earlier branch` (2026-10-16). Code: `earlier_studio/studio/h3_techniques.py`,
`studio/enhance.py` (long mode, `notes`, `must_keep`), `studio/deliverables.py` (`_brief`), `studio/musicvideo.py`
(`long_brief`), `studio/fashion.py` (`design_notes`), `scripts/chatbox/server.py` (`h3_brief`, `enhance_notes`).

## What it does
Every shot of a **Deliverable** and every shot of a **music video** is now written in two steps:

1. The ordinary writer (the Deliverables fill, the music video's `sing_prompt` / `vibe_prompt` / `broll_prompt`) produces a
   short **brief** you can still review and edit (Deliverables) .
2. At render time the **H3 enhancer** expands it into the full H3 prompt (Ref2VA six sections or the base three), through
   the same path as the composer: the model's rules page, LoRA notes, the official guides, the builder
   (`render_h3_mode`), the lint and the prompt guard. The shot renders with that prompt. If every model fails the short
   brief renders and the run notes say why.

**Long prompt mode** (the `✍ Long H3 prompts` chip, on by default; off = the old short prompts): the description body is
asked for **950-1100 words from 5 s up (800-950 for the shortest shots)**, sized so the BUILT prompt lands at about
**2000 tokens** (author 2026-10-16: "the h3 prompts should be 2000 tokens long"): a real 5 s Deliverables shot built to 4,863
characters (~1,200 tokens) from a 681-word body, i.e. 6.06 characters per body word plus ~1,300 for the builder's sections,
soundscape and music, so 950-1100 words build to ~7,100-8,000 characters (~1,780-2,000 tokens). Hard ceiling 8000 characters
(about 2000 tokens, the studio's own prompt cap; the text encoder is Qwen3-VL-32B and sets no smaller one).
How the length is reached (local models stop near 450 words per answer however much is asked; live test 2026-10-16: 410-462
words for a 600-1000 ask, 681 after one rewrite): (1) the first answer; (2) one whole-reply rewrite if it is under the
minimum; (3) up to 3 **continuation** passes, each asking only for an ADDITIONAL passage (second-by-second timeline, then the
layered environment and light, then the camera path, audible actions and end state) that is appended, so no single answer has
to be long. A failed round keeps the draft so far. Past the ceiling the body is shortened at a sentence end in proportion to the
overshoot (so a prompt just over keeps nearly all its length) and rebuilt. Not yet measured live with the new targets (the writer
did not fit in free VRAM while ComfyUI was rendering): check the "Full H3 prompt (N words, ~N tokens)" line on a shot card.

## What the enhancer is told (`h3_techniques.TECHNIQUES`, in every H3 enhancer call)
One main action per shot; camera as action + amplitude + speed + start/end framing; "one continuous shot, no cuts" and
no "then" chains; restate props/place/light in identical words; observable detail and named imperfections; referenced
people as `<Subject N>` with no contradicting hair/clothes, plain garments with no print, no "tripod"; dialogue words from
the field with the voice described outside `<d>`, lines early, ~2.3-3.3 words/s; two sound lanes (soundscape in action
order, music by instrument/tempo); singing shots: tight frame, mic at chest height; production-style realism.
Sources are marked in the module (MiniMax guides, KB `MINIMAX_H3_PROMPTING.md`, our renders, the studio's recipes).

## Per-shot brief (Deliverables)
Template and production style, the run's fixed **scene** (the fill now returns one 2-4 sentence scene per video that every
shot restates word for word), the Look & direction choices and video look, the cast with outfits and character-bible
notes, the template shot's beat and camera, the shots before and after. The finished prompt is stored on the shot
(`long_prompt`) and shown under it (`✍ Full H3 prompt (N words, ~N tokens)`).

## Realism option (opt-in, OFF by default)
A job that switched the `Realism` chip on and carries a shot brief gets `brief["realism"] = True`: `long_block` adds one line right after the brief's rules,
"Realism direction (wording only: the brief's facts, rules and cast win over it): ..." (`realism.direction_text("video")`, ~1.4k characters). Without the
option the block is byte-identical to before. See [realism-4k.md](realism-4k.md).

## Music video maker
The brief carries the maker's own recipe as **rules the rewrite must keep**: sing = tight face-and-shoulders framing, the
microphone at chest height (never at the mouth), straight to camera, one continuous shot; vibe = lips closed, face visible;
broll = one believable action, one smooth camera move. For singing shots the result must still contain `close-up` (and
`microphone` + `chest` when the mic chip is on) or the proven short prompt is rendered instead. The lock recipe itself
(4 steps, 1.25 s lead, lyric words as the dialogue, independent shots from one sheet) is unchanged.

## Fashion studio
Only **Design** is enhanced (`✨ Enhance the prompt`, on by default). The enhancer rewrites the packshot prompt for the
picked model (Krea 2, Z-Image, anime, your fine-tunes) and is told to keep every dropdown choice, the presentation, the
designer's idea and to end with `Original design: no logos, no brand names, no text.`; the garment word and `no logos`
must survive or the plain prompt is used. Try-off, try-on and outfit sheets are never enhanced.

## Limits
Each long prompt costs one extra LLM call per shot (about 15-45 s, more with expansion rounds); the time estimate adds
45 s per shot as a guess until measured shot times exist. Not yet measured: whether a ~2000-token prompt renders better than
a ~700-word one on H3 (run the same deliverable with the chip off and on).

## H3 prompt length setting and the A/B (2026-10-17)
Why: the official Ref2VA guide (https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md, fetched 2026-10-17) says "For generation
tasks, `detailed_description` is normally 350-500 English words. Dialogue-dense content prioritizes fitting the complete spoken timeline rather than mechanically
(2026-10-16), not an H3 source, and was never A/B-tested. So the length is now a visible setting instead of a fixed number; nothing was dropped.

**H3 prompt length: Long (author, ~2000 tokens) | Official (350-500 words) | Auto.** One switch (`h3_techniques.LENGTH_MODES`, `long_targets(secs, mode=)`):
* **Long** = the author's setting and the DEFAULT. Unset, `"long"` or an unknown word changes nothing anywhere: the key is never written to a run's options, the brief
  or the request body, so prompts, system blocks and payloads are byte-identical to before (pinned by `tests/studio/test_h3_prompt_length.py`).
* **Official** = 350-500 words at every clip length. **Auto** = the studio's own inference (the guide gives one range, not a per-second rule): 70 words per second
  clamped to 350-650, +150 for the top, so 350-500 at 5 s, 560-710 at 8 s, 650-800 from 10 s. A hidden **mid** value (600-800 words, ~700) exists only for the A/B.
* Where it is a control: Deliverables (select next to `Long H3 prompts`; field `prompt_length`; also kept by Remix and the recent setups), Music video maker (same
  place; field `prompt_length`), Content Studio (package option `options.prompt_length`, carried to every video and music-video unit). The select is greyed while Long H3
  prompts is off (the setting only acts on the long-prompt path). A typo is a 400 (`prompt_length must be one of long, official, auto`), never a silent Long.
* Where it travels: run option -> the shot brief (`brief["length"]`, only when not Long) -> `sanitize_brief` -> `long_block` (the heading becomes `DETAILED PROMPT
  MODE (Official (350-500 words))`, the word range and the "do not write more than N words" line follow it; the claim "H3 follows far more detail" is dropped) ->
  `enhance.py` `_expand_if_short` / `_extend_long` / `trim_body` use the same targets, so an Official answer of 420 words is not stretched and one of 900 is trimmed to 500.
* On the job card: the enhance note starts with `H3 prompt length: Official (350-500 words), body N words` (absent for Long); the Deliverables run header shows
  `H3 prompt length: ...` for a non-default run; the shot card keeps `Full H3 prompt (N words, ~N tokens)`.
* **Long video (Long video maker, H3 chained segments) does not use this path**: it builds its own four-shot paragraph prompt (`longvideo.h3long_prompt`) without the
  long enhancer, so the setting does not apply there (a Content Studio long video ignores it).

**A/B (prepared, NOT run): `scripts/h3_prompt_length_ab.py`** (modelled on `negative_ab.py` / `realism_ab.py`; the repo has no `scripts/h3_bench.py`, the bench is
`earlier_studio/tools/h3_bench.py`). Arms: official 350-500, long 950-1100, mid 600-800. Cases: 3 library personas (fictional, stated age 21+, finished sheet) x 3 scene
kinds (talk to camera = lip sync and voice; act = pour tea = hands and physics; move = walk, stop, turn = motion) = 9 cases x 3 arms = **27 renders**, one fixed seed
per case (sha256 of the case id) shared by its three arms, the same scene brief for every arm. Each arm POSTs to `/api/studio/generate` (`h3:cinematic`, Draft turbo,
5 s, 9:16, the same brief Deliverables builds plus the arm's `length`), so the guards, the enhancer, the GPU turn and the output guard run as for a real shot; the
written prompt of every arm and its word count are stored in `results.jsonl`.
* Judging checklist (marks ok / bad per arm and case): **adherence** to the brief, **identity**, **motion** and physics artefacts, **lip sync** (talk cases), **audio**.
* Commands: `plan` (arms, cases, cost, gate now), `run --approved [--wait N]`, `verdict CASE ARM --ok adherence,identity --bad motion`, `sheet` (writes `sheet.html`:
  three arms side by side per case with players, frame strips and the written-prompt size, plus the tally), `tally`. Output folder
  `a local folder` (`H3_LENGTH_AB_OUT`); resumable, a rerun only renders what is missing.
* Gating: refuses (records `refused`, exit 2) unless nvidia-smi shows >= 24 GB free AND the queues of  a local port/ a local port/ a local port are empty AND the render's peak (46 GiB, route
  `h3_cinematic`) still leaves the 4 GB floor (so about 50 GiB free); `run` also needs `--approved`.
* Cost: about **23.5 GPU minutes** (27 x ~50 s per 5 s Draft turbo clip + one ~60 s cold load), plus ~17 minutes of writer-LLM time (a guess: 20 / 35 / 60 s per
  shot for official / mid / long), so about 41 minutes wall. VRAM: the render peaks at ~46 GiB; the writer LLM is loaded before it, not together with it.
* The default flips **only after the author has seen the sheets**.
