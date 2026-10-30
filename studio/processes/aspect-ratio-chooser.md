# Aspect-ratio chooser

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Pick the frame shape per job. The composer sends only the ratio; the server turns it into a size each engine family can
render. **Auto** = the model's old default (image 1:1, video 9:16, Ideogram/HiDream 3:4), so ignoring the chip changes nothing.

## Step-by-step in the studio UI
1. Pick the generator first (the chip's options depend on it).
2. Open **Aspect:** and choose a ratio: 1:1, 4:5, 2:3, 3:4, 4:3, 9:16, 16:9, 3:2, 21:9, or Auto.
3. The choice is remembered per medium (image and video separately) for this browser session; Remix restores a job's ratio.
4. "Aspect: follows input" means the size comes from the input image/clip (edits, try-on/product, inpaint/variation).

## Optimal settings
Sizes the server renders (computed from `aspects.size_for`, 2026-10-11):

| Ratio | Image (Krea, Qwen, Klein) | H3 | Wan 2.2 | SDXL ckpt | FLUX.1 ckpt | SD1.5 ckpt (base, ×2 hires) |
|---|---|---|---|---|---|---|
| 1:1 | 1024x1024 | 1024x1024 | 624x624 | 1024x1024 | 1024x1024 | 512x512 |
| 4:5 | 928x1152 | 896x1120 | 560x704 | 896x1152 | 912x1152 | 448x576 |
| 2:3 | 832x1248 | 832x1248 | 512x768 | 832x1280 | 832x1248 | 448x640 |
| 3:4 | 896x1184 | 896x1184 | 544x736 | 896x1152 | 880x1184 | 448x576 |
| 4:3 | 1184x896 | 1184x896 | 736x544 | 1152x896 | 1184x880 | 576x448 |
| 9:16 | 768x1344 | 768x1344 | **480x832** | 768x1344 | 768x1360 | 384x704 |
| 16:9 | 1344x768 | 1344x768 | **832x480** | 1344x768 | 1360x768 | 704x384 |
| 3:2 | 1248x832 | 1248x832 | 768x512 | 1280x832 | 1248x832 | 640x448 |
| 21:9 | 1568x672 | 1344x576 | 848x368 | 1536x640 | 1568x672 | 768x320 |

| Rule | Value | Source |
|---|---|---|
| Image family | ~1 MP, 32 grid, sides 512-2048; the 5 original sizes pinned | `aspects.IMAGE`, `LEGACY` |
| H3 | 32 grid, long side ≤ 1344 | `aspects.H3` |
| Wan 2.2 | 16 grid around the measured 480x832 / 832x480 | `aspects.WAN` |
| Fine-tunes | SDXL 64 grid, FLUX.1 16 grid, SD1.5 ~0.26 MP base doubled by hires fix; a tested size within 5 % of the ratio wins | `aspects.SDXL/FLUX1/SD15`, `finetunes.TESTED_RATIO_TOLERANCE` |
| Best-proven ratios | Wan: 9:16 / 16:9; H3 pipelines (`h3p:*`): 16:9 only | wan_tools comment; h3_pipelines `ASPECT_CHIP` |

Per-entry exceptions: HiDream-O1 offers only 3:4 (1728x2304), 1:1 (2048x2048), 4:3 (2304x1728); try-on 832x1216 and product
768x1344 fixed; Redux uses "Auto (match input)" = nearest ratio to the reference; Meridian needs a native 1344x768 source;
long video is 16:9.

## Prompting rules
- Compose for the frame: in 21:9 full-body shots, feet may leave the frame (composition, not a size fault).
- I2V/edit inputs are cover-cropped or resized to the target; give a start image of the same ratio to avoid cropping.

## Guards and gates
- Server-side: the ratio must be "auto" or one of the list; anything else is refused before queueing.

## Time and VRAM
- Port peaks barely move with ratio at ~equal pixels: Wan 4:5/2:3/21:9 64-65 GB; H3 21:9/4:5 30.5 GB, ~56 s; Krea 4:5/21:9
  22 GB, 3 s warm (aspect check 2026-10-11).

## Known pitfalls / failure modes
- Wan ratios other than 9:16/16:9 render ~399k px; 4:5, 2:3, 21:9 were proven clean; 1:1, 3:4, 4:3, 3:2 on Wan: not verified.
- Wan 21:9 is 848x368 (312k px): sharp but small. 960x416 is an unrendered option.
- H3 on 4:5 pushed the camera in although the prompt said static (one seed).
- Fine-tune ratios beyond the tested portrait/landscape are computed, not individually tested.

## Evidence
  "no size change needed"; contact sheet `outputs/gif_live_test_2026-10-11/aspect_check_contact_sheet.jpg`).
- Tests: `tests/studio/test_aspects.py` (in the repo).
