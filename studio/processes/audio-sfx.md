# Sound effects

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## When to use it
One sound per prompt: a door creak, glass shattering, rain on a metal roof, a car passing left to right, a level-up chime,
footsteps on gravel. Not music (use the Music engines) and not speech.

## In the studio
1. Music tab → "Stable Audio 3 SFX".
2. Prompt in the template's SFX style: **source + material + space + how it evolves**, e.g. `Glass bottle shattering on
   concrete, sharp impact, scattered fragments tinkling.` Sent as typed (never enhanced).
3. Seconds chip: 4 (default), 2, 3, 6, 12 (template rule: 1-3 s one-shots, 3-6 s actions, 6-15 s ambiences).
4. Model chip: `small` (fast, 2.5 GB) or `medium` ("fuller": louder and fuller, 5.7 GB).
5. **Listen before you use it.**

## Settings
| Setting | Value | Source |
|---|---|---|
| Graph | CheckpointLoaderSimple + CLIPLoader t5gemma_b_b_ul2 (stable_audio) → CLIPTextEncode / empty negative → EmptyLatentAudio → KSampler 8 steps CFG 1 lcm/simple → VAEDecodeAudio | [tested] ut_sa3_{small,medium}_* = Comfy template `audio_stable_audio_3_medium` (reprompt off) |
| Trim | trailing silence removed (reverse → silenceremove at -50 dBFS, 0.1 s kept → reverse) | [tested] on the 12 test clips (tails of 0.2-2.0 s removed); threshold [inference] |
| Loudness | two-pass EBU R128 loudnorm, -16 LUFS / -1.5 dBTP / LRA 11, 44.1 kHz flac | [documented] the pipeline library `pp/audio.py` loudnorm_2pass (pp's audio mastering default); [tested] 12 clips landed at -16 to -19 LUFS, transient glass lower (held by the -1.5 dBTP ceiling) |

## Time and VRAM
small 0.2-0.6 s warm (3.4 s cold),  a local port port peak 2.5 GiB; medium 0.3-0.9 s warm (4.2 s cold), 5.7 GiB. The CPU post-step
adds well under a second.

## What the test found
Spectra match the prompts (doppler sweep for the car, evenly spaced step transients, a harmonic arpeggio for the chime).
Small is quieter (door -41 dBFS RMS) and often ends early (the door sound ends ~55 % in; rain has a ~1.5 s silent tail):
that is why the trim + loudnorm step exists. Medium is fuller and louder for twice the VRAM.

## Licence
Stability AI Community License: commercial use under USD 1 M yearly revenue; Enterprise licence above

## Evidence
- Tool smoke 2026-10-11 on  a local port (direct call): small, "Glass bottle shattering on concrete…", 3 s → 2.97 s raw, 1.06 s
  after the trim, -25.3 LUFS (a transient held by the -1.5 dBTP ceiling), 5.1 s incl. load.
- Manifest rows `ut_sa3_*`; `sa3_spec.jpg` in `a local folder`.
- https://huggingface.co/stabilityai/stable-audio-3-small-sfx
