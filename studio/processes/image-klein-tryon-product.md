# Try-on and product shots

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- **Try-on** (`img:tryon`): put the garment from image 2 on the person in image 1, replacing what they wear.
- **Product** (`img:product`): turn a photo of a worn outfit into a clean mannequin packshot on white ("try-off").
Both were CONFIRMED picks of the final build. For a garment reference that is itself a photo of someone wearing it,
Qwen-Image 2.1 outfit swap is the alternative (`image-qwen21.md`). For a packshot of a hard product (not clothing),
use Krea 2 Turbo text-to-image (`images.md` summary "Product").

## Step-by-step in the studio UI
1. Image tab → Generator `Klein 9B · Virtual try-on (person + garment) · ~27 s · non-commercial` or
   `Klein 9B · Product shot of a worn outfit (mannequin, white) · ~20 s · non-commercial`.
2. No aspect chip: the chip reads "Aspect: follows input"; the tool renders the tested fixed size.
3. Drop the reference images into the slots: try-on = `person`, `garment`; product = `image`.
   The Character chip does not apply: `img:*` entries refuse a stored character (`characters.apply_character`);
   drop the character's body shot into `person` by hand instead.
4. takes 1-4.
5. Prompt is optional. Empty = the proven instruction. The prompt goes to the tool raw (never rewritten): there is no
   ✨ enhance effect on these entries.
6. Generate. Use ⤓ Download clean for delivery.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Model / precision | Klein 9B **Base** nvfp4 (`flux/fluxKleinFP8_flux2KleinBase9bFp8-nvfp4.safetensors`, 5.8 GB) | graphs; QUANT_BEST_OPTIONS "FLUX.2 Klein": the only Base 9B file, used for the Base-trained LoRAs |
| Try-on LoRA | `KleinBase9B_TryOn`, LoraLoaderBypassModelOnly, 1.0 | graph; `images.md` §3 (helps); the author's build notes "Try-on" |
| Product LoRA | `KleinBase9B_ProductImage`, bypass, 1.0 (decisive: without it nothing changes) | graph; `images.md` §2 "Product", §3 |
| Steps / CFG / sampler | 20 (Flux2Scheduler) / 5 / euler | graphs; `image_best_tools.py` docstring (b21 / b20 rows) |
| References | try-on 2 (person, garment); product 1 (worn outfit) | `KINDS[...].refs` |
| Size | try-on 832x1216; product 768x1344 (fixed) | `KINDS[...].size` |
| Default prompt | try-on "attach the outfit in Image 2 to the person in Image 1"; product "make a product image for her entire outfit, mannequin, white background" | `TRYON_PROMPT`, `PRODUCT_PROMPT` |
| Default seed | 4242 | `Kind` default |

## Prompting rules
- Leave the prompt empty unless you need to steer (the proven wording is used). If you write one, keep it an
  instruction about the images ("attach the jacket in Image 2 to the person in Image 1, keep the background").
- Rules page (read at call time): `a local folder`.

## Guards and gates
- Output guard on every output (`guards-text-and-output.md`). A mannequin product shot has no face: if the classifier

## Time and VRAM
- Try-on ~27 s, 22 GB; product 17.6-23.6 s, 20.3 GB (`image_best_tools.py` docstring, from the b21/b20 rows;
  `images.md` summary).
- Code peaks: try-on 24 GiB (needs 28 free), product 22 GiB (needs 26 free).  a local port.

## Known pitfalls / failure modes
- Without the TryOn LoRA Klein layers the new garment over the old outfit; the studio graph always has it.
- Background drift: MAD 7.0 with the 9B LoRA (vs 9.0 no LoRA); expect small background changes (`images.md` §2).
- Klein 4B ProductImage is neutral; the 4B consist LoRA hurts. Neither is used here.
- FluxKVCache changes faces and garments: it is not in these graphs; do not add it (`images.md` §2 "Editing").
- Fixed seed + content-hashed outputs: same refs + prompt return the cached file. Use ✦ Variations.

## Evidence
- Sheets `a local folder`, `_SHEET_klein_tryoff_productimage_9b4b.jpg`.
- Commit (earlier commit).
