# Sheet engine

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
author 2026-10-17: Klein should replace Qwen image edit for character sheets and for the sheets of every studio. A "sheet" is the set of edits of one reference
picture: a character's 9 shots (3 more heads, 3 bodies, 3 expressions), a designer's multi-angle sheet (Settings, Vehicles, Animals, Plants, Hair, Nails, Tattoos,
setting. Not covered (unchanged): outfit swap / try-on, Marigold, Fix lighting, Recreate, the pose set, 3D.

## The setting `sheet_edit_engine`
Saved in `a local folder` (`COMFY_STUDIO_SHEET_ENGINE_FILE` moves it; `COMFY_STUDIO_SHEET_EDIT_ENGINE` is the global value when the file
has none). `GET /api/studio/sheet-engine` returns the setting, each studio's override, the effective engine per studio and the honest label of each engine;
`POST` with `{"default": "qwen21", "studios": {"hair": "klein9b", "fashion": "default"}}` saves (`"default"` or `""` clears one override). To pin a studio to Qwen:
`{"studios": {"fashion": "qwen21"}}`.

| Where | Control |
|---|---|
| Character composer (single sheet, batch, looks "build sheet", photo character) | chip **Sheet engine**: Follow the setting / Klein 9B / Qwen-Image 2.1 / FLUX.3 Klein (lane); each option carries its trade-off. The hand-kept `character:qwen21` model stays on Qwen unless the chip says otherwise |

## What a Klein sheet does
* **Prompt**: Klein reads prose and ignores negatives, so the edit words are `sheet_engine.klein_prompt`: "Same woman, same face, hair and skin as in the picture, in a new
  photo. The new photo is <shot wording>. <head framing for head shots> Her outfit: <outfit, legwear dropped for head shots>. Keep her face and hair exactly as in the picture;
  <look line>." (the pose-set Klein edit shape: instruction, what stays). Qwen keeps the sheet's own `characters.edit_prompt`; FLUX.3 writes the result with `<ref_image_0>`.
* **Identity fallback** (character sheets, after the face scoring): a shot whose best take is under its floor is rerolled once on Klein with a new seed, then redone on
  Qwen 2.1 edit (its own words, its grain gate). Floors (`floor_for`): **0.50** for a front-facing face (the sheet's pass line `facescore.MIN_SIM`), **0.40** for the
  turned and small roles (3/4, profile, body front, body side), set from the A/B. The picture carries `engine` and `engine_note` ("Klein failed identity (0.36 under 0.40):
  rerolled with a new seed (0.37), redone on Qwen (0.51)"); the candidates of the shot carry the engine of each take. A Qwen redo that is still weak is kept and flagged weak
  by the sheet's own `accepted` flag, never hidden. A shot is never silently swapped.
* **Which role uses which engine** (author 2026-10-17 "lets do all of this", from the same-day A/B; `PINNED_ROLES`, `PIN_NOTES`). Pinned shots are made after the Klein ones so the
  model swaps once; they are never rescued on Klein, only flagged weak by the sheet's own `accepted` flag, and each carries its reason as `engine_note`:

  | Role | Engine (default Klein sheet) | Why (A/B, 2 characters x 2 takes) |
  |---|---|---|
  | head 3/4, head profile, body front | **Klein 9B**, redone on Qwen under its floor | 3/4 0.76 vs 0.79 (equal); profile 0.66 vs 0.54; body front 0.86 vs 0.76 |
  | smile, laugh, serious | **Qwen 2.1** (pinned) | Klein over-smiles (a full grin) and the face drifts: 0.56 vs 0.74 on the smile |
  | body side | **Qwen 2.1** (pinned) | both read low on a tiny side face, Qwen slightly better (0.49 vs 0.42); Klein changed the footwear |
  | body back | **Qwen 2.1** (pinned) | no face to check; Klein drifted the outfit on 2 of 4 (shoes added, boots changed), Qwen held 4 of 4 |

  With the `qwen21` setting nothing is pinned (the whole sheet is Qwen). FLUX.3 sheets pin the same roles.
* **Designers and Fashion views** (`sheet_engine.sheet_view`): Klein first; a failed job or a failed subject check (`subject_check`: ArcFace >= 0.40 when the picture has a
  face, otherwise a coarse palette check, floor 0.20, uncalibrated: it only catches a wrong-colour result) rerolls once with a new seed, then redoes the view on Qwen with a note.
* **Grain gate**: Klein showed no grain (max ratio 1.46 against the 2.0 fail line); the Qwen tool keeps its own grain gate for the Qwen shots and the fallback.
* **Unverified sheets** (face scorer down): no fallback can run (nothing to compare); the sheet is `unverified` as before.
* **VRAM**: the character port picker asks for both edit graphs (Klein 9B about 30 GiB, Qwen 36 GiB); the 4 GiB floor rule is unchanged. A Qwen fallback that cannot get the room is a
  VRAM wait (the sheet resumes, finished takes are reused), not a skipped fix.

## Evidence (trial results, 2026-10-17)
2 saved characters, 2 takes, seed 7, from the head_front: face to the head_front, Klein / Qwen: head 3/4 0.76 / 0.79, profile 0.66 / 0.54, body front 0.86 / 0.76, body side
0.42 / 0.49, smile 0.56 / 0.74; no picture grainy on either; Klein 27 s against 56 s per two-take job; Klein drifted the outfit on 2 of 4 back views. One FLUX.3 body front
per character read the same as Klein (0.84) with a warm cast and a 28 s lane start. Full table and the visual read: [sheet-engine-ab](../research/sheet-engine-ab-2026-10-17.md).

## Known pitfalls
* Expressions, side and back views are Qwen on every Klein sheet (pinned), so a "Klein sheet" is Klein for four of its nine edits (3/4 left and right, profile, body front) and Qwen for five; the speed gain is correspondingly smaller than the 2x per Klein job.
* Garment / object detail drift on designer and Fashion sheets is not measured by the coarse palette check (no live designer render was made).
* Changing the setting does not change finished sheets; only new sheets (and re-made views) use it. A running studio has the new code only after a restart.
* The character batch's time and estimate numbers (`SHEET_S_REF`, measured on Qwen) are now high for Klein sheets.
