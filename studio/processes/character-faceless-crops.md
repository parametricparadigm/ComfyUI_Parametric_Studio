# Faceless crops

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / when to use it
Get images of a verified character without the face (torso, hips-down, back view), for posts where the face should not
show. Crops only cut pixels from an already verified image, so they inherit that image's age verdict by provenance.

parent's verdict (provenance), never re-judged as a faceless image. A sheet whose `body_back` is withheld is re-rendered
automatically as a fully clothed back view (see "Automatic re-render" in [guards-text-and-output.md](guards-text-and-output.md)).

## Step-by-step in the studio UI
1. Build a character until its status is **ready** (not "unverified").
2. On the sheet's media card, under a shot, press **✂ Faceless crops**.
3. The studio makes torso, hips_down and back crops in turn; each appears as a **⤓ <kind>** link (a scrubbed download).
4. Picked looks (primary/favourite) are also valid parents through the API (`parent: {kind: "look", image_id}`); the Looks
   panel has no crop button in the code read here.
5. Outpaint (wider composition of a crop): API only, `POST /api/studio/crops/{id}/outpaint {prompt, scale, session_id}`;
   no UI button (only `api.studioCropOutpaint` exists).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Crop kinds | torso, hips_down, back (custom box via API; must not touch a face) | `crops.KINDS`, `Crops.js` |
| Box placement | YOLO person segmentation + face boxes, cut below the lowest face | crops.py docstring |
| Outpaint scale | 1.25, 1.5 (default), 2.0 | `crops.OUTPAINT_SCALES` |
| Outpaint model | FLUX.1 Fill OneReward fp8 on ComfyUI (`tools/image_fill_tools.py`; dfserve `flux_fill` until dfserve was retired 2026-10-12): guidance 30, 28 steps, euler / normal, at the canvas size | `image_fill_tools.py`; the model page `flux.1-fill-dev-OneReward-transformer_fp8.md` |
| Outpaint seed | 4242 | `crops.outpaint` |

## Prompting rules
- Crops take no prompt.
- Outpaint prompt: describe what fills the new area (setting, surface); it gets the Layer 1 text check. Fill models want
  full sentences (the flux_fill prompt skill, `config/df_prompt_skills.json`).

## Guards and gates
  withheld or deleted parents give no crop.
- Serving re-checks provenance every time: parent still exists, file unchanged (sha256), verdict still cleared; otherwise
  the crop is refused and deleted.
  parent's verified face (ArcFace ≥ 0.5) or it is withheld. See `guards-text-and-output.md`.

## Time and VRAM
- Plain crop: CPU only (person/face boxes), a few seconds; not measured.
- Outpaint: a ComfyUI FLUX.1 Fill job under the studio GPU locks, on the port the picker gives it (crops became portable
  when dfserve was retired 2026-10-12); time and peak not measured through the studio yet. The Fill transformer file
  is 11.9 GB on disk (`flux.1-fill-dev-OneReward-transformer_fp8.safetensors`); BEST_OPTIONS images.md quotes Flux.1 Fill
  OneReward fp8 at 27 s, 21.5 GB.

## Known pitfalls / failure modes
- An error that mentions parent/withheld/refused stops the remaining crop kinds.
- No pose model is on the box: boxes are geometry below the face; odd poses can give odd crops.
- The Fill graph loads the local fp8 OneReward transformer with `clip_l` + `t5xxl_fp16` and `flux/ae.safetensors`
  (store files); nothing comes from the HF cache.
- Crop files live under the parent's folder and are pruned with the character.

## Evidence
- `earlier_studio/studio/crops.py` docstring (rules), commit (earlier commit).
- No GPU render of a crop outpaint found in the evidence read.
