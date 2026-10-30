# Platform formats

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.

A **format** presets the composer for one kind of post on one platform, and the **post steps** on a result card turn a
S1–S37) and the preset library `PLATFORM_PRESETS_PROPOSAL_2026-10-11.json` (copied into the repo as
`earlier_studio/studio/data/platform_presets.json`; the KB copy stays the research source).

Status: **untested** as a whole. Every format is wired; none has been rendered and judged through the studio as a
format yet. The post steps were run for real on CPU (pp's code, ffmpeg) in the tests.

## Choosing a format

- **Composer → Format** (next to the aspect chooser): the Image tab lists single-image and carousel formats, the Video
  tab video formats. Choosing one sets the generator the format names (when it is in the catalogue), the ratio, the
  clip length where the generator offers it, and the enhancer's style.
- **Launcher → 📱 Formats**: one card per format that is buildable now; *Choose* opens the composer on it.
- The **strip** under the generator shows the caption template, hashtag count, safe zone, audio advice, delivery size,
  the post steps to run, the policy notes, and the **AI label reminder**: turn the platform's AI toggle on and keep the
  AI line first in the caption. The clean download strips all metadata, so no platform auto-label fires.
- **Enhancer**: the format's style, camera, light and "avoid" list go to the enhancer as a fenced *FORMAT STYLE* data
  block, like model rules and take directions. The subject, the model rules and every content rule win over it. Without
  a format the enhancer prompt is unchanged, byte for byte.

## Carousels

Generate queues N ordinary jobs with **one seed family** (seed, seed + 1, …), shown as one group in the feed
("Carousel · N slides"). Each slide is enhanced with the format's style plus its slide's role (slide 1 = the hook /
grid cover, the last slide = the question or CTA, the rest = variety). Pick a **character** for one persona across
the set. **⤓ Download set (numbered)** on the first slide saves every slide through the clean download as
`<format>_01.jpg`, `_02` ….

## Post steps (📱 Post steps on a finished card)

Each step is a new studio job with its own card. Its result goes through the **output guard** like any render.

| Step | What it does | Defaults and where they come from |
|---|---|---|
| 🎞 Assembly | 2–8 clips or stills (➕ Assembly on cards, ordered in the composer's tray), an optional music bed and voice-over (🎵 / 🎙 on audio cards) → one video. | `pp.video.assemble` itself: stills get slow pan and zoom, the bed is ducked under the voice, −14 LUFS, optional caption line per clip. No burnt AI label unless `settings.label: true` (default off, see *AI label* below). Each clip's own audio is its voice take; a voice-over replaces them, cut at the clip boundaries. pp's 0.4 s air after a take is off (the clips' lengths are the timeline). Size = the format's delivery size (1080×1920 for 9:16). |
| 🖼 Cover frame | Pick a time with the slider → the cover at the format's size, plus the 3:4 centre crop the photo feed grid shows. | vertical short grid shows the centre 1080×1440 [V S14]; short-video and Shorts take any frame [O S1, S16]. |

Every step runs pp's code under pp's venv (`earlier_studio/studio/_post_cli.py`). The CPU work runs with the GPU locks
handed back, so a long encode never blocks a render. Outputs are content-hashed, so a retry reuses the file.

## Which formats are buildable

`GET /api/studio/formats` lists the formats with `buildable_now`, the pieces each one needs, and `unlocked_by` (the
piece that made it buildable). Counts on this branch:

- **26 SFW formats** build with one studio job, as before.
- **14 more** became buildable with the post steps:
  - captions + assembly (+ export): short-video talking head, day in the life, storytime, faceless explainer, AI street
    interview; IG vertical short talking tips; vertical short video and long-form faceless explainers; LinkedIn 4:5 talking video;
  - assembly only: UGC unboxing;
  - cover only: vertical short cover;
- **3 GIF formats** became buildable with the GIF maker (live since the 2026-10-11d merge), all on the Edit tab:
  - X reaction GIF on `gif:still`, 3 s, up to 15 MB (X allows 15 MB GIFs [V S25]);
  - GIF teaser loop on `gif:still`, 3 s, ping-pong;
- **Not yet buildable**, with the piece each one misses:
  - text overlay: POV skit, before/after, Pin video, buy-again listicle;
  - beat sync: outfit transition, photo dump;
  - green screen: green-screen commentary;
  - slide designer: educational carousel, LinkedIn document;
  - loop tool: Shorts hook loop;
  - pp 38 thumbnails in the studio: long-form video thumbnail;
  - H3 identity across many clips: GRWM;

## Rules (unchanged guards)

  that adds one.
  wording in the prompt, fields, typed captions and transcripts.
- **Every result goes through the output guard.** That includes captions burnt on an already-cleared clip, assemblies,
  exports, covers and blurred previews.
  post to that character's anchor check.
- **Text guard.** It reads every typed caption at submit and again in the job queue, and every transcript before burn.
- **AI label: none on outputs by default** (author 2026-10-11: no AI labels, stamps or watermarks on outputs; the AI
  disclosure is a publish-time step). Captions, Assembly and Export each take `settings.label` and default it to off;
  `true` burns "AI-generated" in the top-right safe corner, and Export's `"auto"` burns it unless the source already
  carries one. The format strip's AI reminder (platform AI toggle, AI line first in the caption) is unchanged. The
  PerTh voice watermark on studio voices is not a label and stays.
