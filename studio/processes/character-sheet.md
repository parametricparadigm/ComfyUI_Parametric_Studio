# Character sheet

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
9 reference edits of that anchor (3 more headshots, 3 full-body, 3 expressions). Later Image and Video jobs take their
identity input from the sheet. Use it for personas and any recurring person. Do not re-describe a person in plain prompts
to get consistency: on this box that gives a new face on every seed (intra-character ArcFace about 0.45).

## Step-by-step in the studio UI
1. Open the **👤 Character** tab. Pick the generator: **Character sheet · Klein 9B anchor + Qwen-Image 2.1 edits** (default)
   or **· Qwen-Image 2.1 anchor + edits**.
   the description).
3. Fill the `name` and `outfit` fields (empty outfit = "a plain fitted black t-shirt and blue jeans").
4. Pick **candidates** (2 default; 1, 3, 4). More candidates = more takes per shot to choose from, more time.
5. Leave **🔍 explore looks first** ticked to choose the look across every image model first (see
   `character-explore-looks.md`), or untick it to build the sheet straight from the anchor model.
6. Press **Generate**. The shelf shows the status: queued → building → pending_check → **ready** (or unverified / withheld).
7. To use it: press **Use** on the shelf (switches to the Image tab), or pick the character in the **👤** chip on the Image
   or Video tab, then generate as usual. Drop your own file into a slot to override the sheet image for that slot.

> Several characters at once: see [character-batch.md](character-batch.md) (the **👥 Batch** form on the Character page: up to 10 rows, anchors rendered together, sheets queued in order).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Sheet edit engine | Klein 9B edits by default since 2026-10-17 (Qwen 2.1 on a failed face check, the back view always Qwen; chip **Sheet engine**): see [sheet-engine.md](sheet-engine.md). The table rows below describe the earlier Qwen-edit sheet that was measured at 0.751 |
| Sheet model | `character:klein9b` (Klein 9B distilled anchor + Qwen 2.1 edits) | `variants.CHARACTER_MODELS` (default); the author's build notes "Still PROVISIONAL: character sheet stays Klein 9B anchor + Qwen edits" |
| Candidates | 2 | `variants.CHARACTER_SETTINGS`; measured A/B ran with 2 (report below) |
| Aspect | 3:4 fixed | `characters.ASPECT` |
| Look line | plain light grey studio background, soft even light, photoreal | `characters.LOOK` (fixed for every character) |
| Weak-shot threshold | ArcFace < 0.5 to the anchor = flagged weak (kept) | `facescore.MIN_SIM` |
| Age floor | every face must read 20+ (insightface) | `facescore.MIN_FACE_AGE` |
| Klein-edit arm (`klein9b_edit`) | hidden; do not use | catalogue "skipped": unmeasured A/B arm (but see pitfalls) |
| QuadView / LCS consist LoRAs | not wired into the sheet | BEST_OPTIONS images.md "Character consistency" row picks Klein 9B dist + QuadView_klein9b; the studio sheet does not use it |

## Prompting rules
  words (school, teen, "looks younger"); the create path refuses them.
- The sheet's own shot wording is fixed and never enhanced; only the description, name and outfit are yours.
- When using a character, the prompt describes the action and place. Describing engines get the character's description
  added; Qwen 2.1 text-to-image is rerouted to the Qwen edit (the identity path). FLUX.1 and SDXL fine-tunes (`ckpt:*`)
  take the face through an identity adapter (PuLID-FLUX / IP-Adapter FaceID) fed with a face crop of head_front, with
  an Identity strength chip (`image-finetunes-ckpt.md` § Character reference). Entries without an identity input
  (Krea 2, Z-Image, HiDream, SD 1.5, the SVDQuant row) refuse with the reason.

## Guards and gates
- Text guard (`character_policy`) on create and on every request that uses the character (no exemptions on the use path).
- Image backstop: any anchor candidate or edit take whose face reads under 20 aborts the build and deletes the character.
- The finished sheet is `pending_check` until the output guard clears every image; then `ready`. A guard failure leaves it

## Time and VRAM
  0.751, 0 weak shots; about 24 s per edit shot. Klein-edit arm 100 s, 0.714, 2 weak shots.
- The variants.py comment's "near 10 minutes" for 2 candidates is an estimate; the one measured run was ~4 min.
- VRAM: smoke budget "~45 GB,  a local port idle" (LOCAL_MOE_REFERENCE §15). Qwen 2.1 bf16 holds ~33-36 GB; Klein 9B ~28 GB peak.
- Face scoring runs on the CPU and hands the GPU locks back while it runs.

## Known pitfalls / failure modes
- `head_profile` and `body_side` score lowest (0.56 / 0.63 in the A/B); expect weak flags on side views.
- The back view is never scored (no face).
- Deleting a character removes the stored copies; the original renders stay in the ComfyUI output folder.
- Retry of a sheet keeps the locked seed and reuses finished takes.
- `klein9b_edit` is still hidden as "unmeasured", although `character_ab.py` did measure it on 2026-10-10 (report below).
  the author decides whether to list it; it is faster but had 2 weak shots.
- The 👤 chip lists only `ready`/`unverified` characters; a stale pick is cleared automatically.

## Evidence
- A/B report: `a local folder` (+ `report.json`, `sheet.png`).
- Dry run: `scripts/chatbox/character_check.py` → 20/20 graphs valid on  a local port (2026-10-10).
- Guard round 17b verification: `/tmp/charmode-verify-r17b/` (`rerun_summary.txt`: bypass probes closed;
  `pytest_full.log`: 7855 passed, 5 failed incl. the known launcher/llama weights tests). Text-guard checks, no renders.
