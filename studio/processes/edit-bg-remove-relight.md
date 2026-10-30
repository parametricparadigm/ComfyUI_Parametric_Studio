# Remove background and relight

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Remove background
### When to use it
- Cut-outs for stickers, product listings, compositing, thumbnails. People, hair and fur edges hold well.
- **Glass and liquids come out solid**: every model tried (core BiRefNet, the ComfyUI-RMBG pack, RMBG-2.0) cut the perfume
  bottle as an opaque shape, with no see-through alpha. Cut glass by hand.

### In the studio
1. On any finished image card: **✂ Remove background** (one per image). A new card appears with the RGBA PNG.
2. Or Edit tab → "BiRefNet · Remove background", drop the picture in `image`, Generate. No prompt.
3. ⤢ Upscale on a cut-out drops the alpha (the upscaler is RGB only).

### Settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Graph | `LoadBackgroundRemovalModel birefnet.safetensors` → `RemoveBackground` → `InvertMask` → `JoinImageWithAlpha` → SaveImage | [tested] ut_bg_core_* = official template `utility_birefnet_remove_background` |
| Size | the input's own size | [tested] |
| Model | core BiRefNet (Comfy-Org repack), MIT | [documented] ZhengPeng7/BiRefNet |

### Time and VRAM
0.2-1.3 s warm, ~8 s cold;  a local port port peak 0.8-4.0 GiB warm, 7.8 GiB on the cold first row (8 GiB budgeted + 4 GiB
headroom).

## Relight a product
### When to use it
- A product photo into a new light and scene: soft studio top light, window shadows, sunset over the sea, city neon.
  The bottle shape, cap and label were kept in the test.
- **Not for people.** On the person test (`ut_icl_closeup_*`) the face and hair colour changed (identity is not held at
  512 px SD 1.5). The studio runs insightface on the input first and refuses a picture with a face; if the face check
  cannot run, the job is refused too (fail closed).

### In the studio
1. Edit tab → "IC-Light SD 1.5 · Relight a PRODUCT".
2. Drop the product photo in `image`.
3. Prompt = the product in a few words: `a glass perfume bottle with a gold cap, product photo`. It is sent as typed
   (never enhanced); the graph adds the light's prompt and `best quality`.
4. Light chip: `studio_top` (default), `window_left`, `sunset_left`, `neon_right`. Takes 1-4 (seed +1 per take).

### Settings (pinned in the graph)
| Setting | Value | Source |
|---|---|---|
| Recipe | FG masked grey (core BiRefNet) → `VAEEncodeArgMax` → `ICLightAppply` on DreamShaper 8; initial latent = gradient light map; denoise 0.9 | [tested] ut_icl_* = ComfyUI-IC-Light-Native `examples/fg_lightmap.json` |
| Sampling | KSampler 25 steps, cfg 2, dpmpp_2m_sde, karras, seed 4242 | [tested] |
| Size | 768x512 for landscape / square inputs, 512x768 for portrait (scaled, centre-cropped) | [tested] the two sizes rendered |
| Prompt | `<product>, <light prompt>, best quality`; negative `lowres, bad anatomy, bad hands, cropped, worst quality` | [tested]; [documented] IC-Light gradio quick prompts |
| Light map | linear 255 → 0 gradient, bright side = the light (generated once into ComfyUI/input) | [tested] prep_inputs.py; [documented] IC-Light: "Lighting Preference" is only the initial latent |
| Hi-res pass | none (the gradio does x1.5 at 0.5) | [tested] as rendered |

### Time and VRAM
3-13 s per take warm (~20 s cold);  a local port port peak 7.3 GiB (8 GiB budgeted + headroom).

### Licence
IC-Light code Apache-2.0 (lllyasviel/IC-Light LICENSE); the IC-Light SD 1.5 weights and DreamShaper 8 are in the SD 1.5
OpenRAIL family (model store pages).

## Guards
Both results are images: the output guard checks every one before it is served. The text guard reads the relight prompt.

## Evidence
- Tool smoke 2026-10-11 on  a local port (the studio tools called directly, not through the UI; vram claim held): cut-out of
  `pp02_54ae0f02_bottle__white.png` → RGBA 1024x1024, 17.9 % foreground (the test's 18.0 %), 5.5 s incl. load; relight of
  `compare3_4_product_commercial.png` with `window_left` → 768x512 window-light scene, bottle and cap kept, 18 s cold; the
  person still `retest_e00_in_closeup.png` → refused by the face check (4.8 s, CPU).
- `a local folder` (rows `ut_bg_core_*`, `ut_icl_*`),
  `a local folder`.
- Sheets `a local folder`, `icl_perfume.jpg`, `icl_closeup.jpg`.
- Upstream: https://github.com/ZhengPeng7/BiRefNet, https://github.com/lllyasviel/IC-Light.
