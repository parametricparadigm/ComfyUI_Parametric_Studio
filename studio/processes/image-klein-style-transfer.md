# Klein style transfer

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Re-render an existing image (image 1) in the lighting and colour style of a style reference (image 2), keeping its
composition, person and dress. This is the studio's only style tool: Redux copies the reference's content and is not
offered as style (`image-redux-reference.md`).

**author verdict (2026-10-11) vs what the studio has:** the best style tool on the box is **Klein 9B 1-ref** (the style
reference + a text subject): strong watercolour transfer, prompt kept 6/6, no content leak. The studio entry is the
**2-ref** recipe, which is weaker (a warmer painterly grade over the image-1 composition). A 1-ref entry is **not
wired**. Use 2-ref when an existing image must keep its composition; for "this subject in that style" there is no
studio button yet. ReduxAdvanced (token downsampling) rendered 80/80 rows on 2026-10-11 but is not scored yet, so it
does not change this.

## Step-by-step in the studio UI
1. Image tab → Generator `Klein 9B · Style transfer (image + style reference) · ~3 s · non-commercial`.
2. Aspect chip: `auto` = 1:1, or any studio ratio (output size; references are not cropped to match automatically).
3. Drop image 1 (content) into `image`, image 2 (style) into `style`.
4. takes 1-4.
5. Prompt optional: it is appended after the fixed lead (see below); sent raw, never rewritten.
6. Generate.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision | Klein 9B **distilled** bf16 (`flux/flux-2-klein-9b.safetensors`) | graph; the author's build notes "Style transfer" (CONFIRMED) |
| Steps / CFG / sampler | 4 / 1 / euler | graph; `images.md` §2 "Style transfer" (`dn_t4_style2_A`) |
| FluxKVCache | off (it changes faces, garments, references) | `images.md` §2 "Editing" |
| References | 2: image 1 = content, image 2 = style | `KINDS["style"].refs` |
| Lead text | "Re-render the scene and the person of image 1 in the lighting and colour style of image 2" (+ your words) | `STYLE_LEAD`, `style_prompt` |
| Size | studio ratio on a 16 grid (1:1 1024x1024 default) | `size_for` |
| Default seed | 20261009 | `KINDS["style"]` |

## Prompting rules
- If your prompt contains "image 2" it is used as is; otherwise it is appended after the lead. Describe what must stay
  ("keep her face and the red dress") rather than the style itself; the style comes from image 2.
- Klein carries painting/illustration styles; it does **not** carry a photographic film-stock look (film grain,
  tungsten): use a text prompt or a LoRA for that (`images.md` §8).
- Rules page: `a local folder`.

## Guards and gates

## Time and VRAM
- ~3 s per image (`image_best_tools.py` docstring); Klein 9B measured 27.4-28.4 GiB port peak (`images.md` §8; capability
  run `klein9b_distilled` 28.4 GB).
- Code peak 36 GiB (conservative) → needs 40 GiB free.  a local port.

## Known pitfalls / failure modes
- Weak transfer is normal for 2-ref: the image-1 composition dominates. Stronger look = the 1-ref recipe (not wired).
- References are full-res inputs; very different aspect ratios between image 1 and the output ratio are untested.
- Fixed seed: same inputs return the cached file; ✦ Variations for new seeds.

## Evidence
- `a local folder,film,poster}.jpg`.
- ReduxAdvanced rows (rendered, unscored): `a local folder` (80/80 success).
- Commit (earlier commit).

## Klein 9B edit (`img:klein_edit`, added 2026-10-11)
The same graph as `img:style1` (`graphs/klein9b_edit.api.json`: Klein 9B distilled bf16, the input as a 1 MP
ReferenceLatent, 4 steps, CFG 1, euler, Flux2Scheduler), used as a plain instruction edit: the prompt is sent as typed
(no style sentence) and the output keeps the input's shape (up to 4 MP, 16 px grid, as `image_klein_tools.klein_edit`).
Pick a saved character and it edits the character's front headshot with the identity-edit wording
(`characters.apply_character`), like `qwen21:edit`: the character builder's hidden Klein edit arm, now a studio entry
(author 2026-10-11) so the Game Builder can render sprites with it (`config.json` `sprite_models`). Measured only as a sheet
edit arm (2026-10-10: 0.714 vs Qwen's 0.751); not yet rendered through the studio. Non-commercial weights.
