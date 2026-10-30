# Poster with real text

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Designed posters and layouts with a title and subtitle: the strongest "graphic design" look on the box. SFW only (a
safety filter is in the weights). For plain signage or short exact text inside a photo, Krea 2 Turbo was as exact and
6x faster (`images.md` summary: text/poster winner = Krea 2, Ideogram = best designed-poster look).

## Step-by-step in the studio UI
1. Image tab → Generator `Ideogram 4 · Poster / text design (full JSON caption) · ~20 s, SFW only`.
2. Aspect chip: `auto` = 3:4 (896x1184); any studio ratio is accepted.
3. takes 1-4.
4. Fill the fields: `title`, `subtitle` (placed on the tested poster boxes), `background`, `style` (optional; defaults
   below). The prompt box is the high-level description of the poster.
5. ✨ enhance is allowed (the description is enhanced; the title/subtitle fields are used as typed).
6. Generate.

## JSON caption converter and the Pictures page (2026-10-17, recipe until rendered)
Ideogram 4's open weights were trained only on structured JSON captions (`ideogram-oss/ideogram4` README and `docs/prompting.md`,
fetched 2026-10-17): plain text "will not work and will likely trigger a safety warning". The studio's tested graph already fed it a JSON
caption elsewhere is). New: `studio/ideogram_caption.py` converts the user's words and the rewrite into the trained caption:
1. the enhancer (family guide `studio/guides/ideogram4.md`) writes plain prose with every exact word in double quotes;
2. a writer LLM gets the schema in its system prompt (three fields, strict key order for photo vs art_style and obj vs text elements,
   uppercase `#RRGGBB`, bbox `[y_min,x_min,y_max,x_max]` on 0-1000, compact JSON with real characters) and returns the caption;
3. `normalize` fixes order / hex / bbox, `repair_text` adds back any exact string the writer dropped (never edits one it kept),
   `validate` checks shape and that every exact string is present verbatim; on any failure the deterministic template (the tested
   poster caption: description, graphic-design style, title / subtitle boxes) is used and the job note says "fallback";
4. the studio text guard runs on the final JSON text (`runners._run_img`), and the tool refuses a non-JSON `caption_json`.
The caption rides in `job.fields["caption_json"]` and the graph `ideogram4_json` feeds it to the text encoder (same nodes, steps 20,
CFG 7 -> 3). Without a caption the old prompt-builder graph runs unchanged. The Pictures page offers `img:poster` (its title / subtitle /
background / style fields are optional: `image_deliverables.OPTIONAL_FIELD_ENTRIES`), so typography, graphic-design and map templates
can use it; it is not offered a character (persona filter). **Licence: Ideogram 4 Non-Commercial** (stated on the entry and the
label; licensing is handled by the author's legal team). Proof level: recipe; A/B prepared, not run: `scripts/ideogram4_ab.py plan`
(6 typography prompts x Krea 2 / Ideogram JSON / Ideogram plain; 18 renders, ~6-7 GPU min, 38 GB peak, needs 44 GiB free).

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision | `ideogram4_fp8_scaled` + its unconditional companion (DualModelGuider) | `image_best_tools.py` docstring; rules page `a local folder` |
| Caption | FULL JSON caption from `Ideogram4PromptBuilderKJ` | the author's build notes "Posters / text design" (CONFIRMED); lora_retest `fu_rv_ideo4_poster_*_json_noopt` |
| Never | `Ideogram4OptimizationsKJ` (always errors), the minimal JSON wrap (grey safety cards on SFW prompts) | `images.md` §2 "Text/poster", §5 "Settings to drop" |
| Steps / CFG | 20 / 7, falling to 3 on the tail (CFGOverride) | the author's build notes rules page notes |
| Title box | x 0.06, y 0.04, w 0.88, h 0.13 (ALPINE EXPRESS row) | `POSTER_TITLE_BOX` |
| Subtitle box | x 0.16, y 0.18, w 0.68, h 0.05 | `POSTER_SUBTITLE_BOX` |
| Default style / background | "bold graphic poster design, flat colour areas, clean lettering, no gradients" / "as described in the high-level description" | `POSTER_DEFAULTS` |
| Resolution | 3:4 896x1184 by default (auto); other ratios ~1 MP on a 16 grid | `BEST_IMAGE_AUTO`, `size_for` |
| Default seed | 20261009 | `KINDS["poster"]` |

## Prompting rules
- Prompt = what the poster shows (scene, mood, palette). Put the exact words in `title` / `subtitle`; the tool also
  quotes them into the description, as the tested caption did (`poster_values`).
- Rules page (read at call time, prompt_style json): `a local folder`.

## Guards and gates
- Layer 1 text guard on prompt + every field (title/subtitle/background/style are all scanned).
  (`guards-text-and-output.md`).
- Download/publish: scrubbed export + TRIBE pre-post (images = recorded "not applicable" pass) (`publish-download-tribe.md`).

## Time and VRAM
- 14-22 s per image, 38 GB port peak (`images.md` summary; capability run median 14.6 s, peak 38.2 GB).
- Code peak 40 GiB → needs 44 GiB free.  a local port. With the  a local port MoE loaded (~46 GB) this usually does not fit: stop it
  or wait (author's call).

## Known pitfalls / failure modes
  caption, so a grey card means the content was refused by the model; reword, don't retry.
- Miscounts people in crowds (S04: 9+ for "six"); weak on hands. Keep posters to graphic subjects.
- Warped product shapes (S05 teapot); use Krea 2 for product packshots.
- Same prompt + fields = same cached file (fixed seed 20261009). Use ✦ Variations for new seeds.
- Ideogram is excluded from character "Explore looks" (its filter blocks persona prompts: `studio/looks.py`).

## Evidence
- Capability run rows `ideogram4_fp8` (10/10 success) in `a local folder`.
- Commit (earlier commit).
