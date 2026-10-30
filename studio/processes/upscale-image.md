# Upscale an image

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
- Enlarge a finished studio image (any image card) as a new card, without re-generating.
- 2x (ESRGAN) for web/social; 4x (4x-UltraSharp) for print-size or crop-in work.
- Images only: there is no video upscale path in the studio.

## Step-by-step in the studio UI
1. On a finished image card press **⤢ Upscale** (one button per image when the card has several takes). That sends 2x.
2. A new card appears with the upscaled image; it records which job/image it came from.
3. 4x: not a button. It is the `scale: 4` setting of `upscale:image` (API `POST /api/studio/generate` with
   `settings.scale = 4`, or a retry of an upscale card that already had scale 4).
4. If it failed for VRAM: Retry, or Queue when free.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Scale | 2 (default, what the button sends) or 4 | `variants.UPSCALE_SETTINGS` |
| Models | ESRGAN 2x / 4x-UltraSharp on ComfyUI  a local port | `variants.UPSCALES` label; graph |
| Prompt / enhance | none (upscales are never enhanced) | `server._studio_generate` |
| Realism chip (opt-in, OFF by default) | `Realism: off / on` on the Edit tab's Upscale entry. On + x4: after the upscale the picture is fitted to a 3840 long edge, gets a light luma-weighted camera grain and loses its metadata (`realism.post_image(target="4k")`); x2 is left alone with a note; a failed step keeps the plain upscale. The card shows "Realism: ... (proof: kb-ab ...; proxy-tested on 5 phone photos, not a guarantee)". Not a guarantee of photographic quality: the 4K file is an upscale | `studio/realism.py`, `runners._run_upscale`, `docs/processes/realism-4k.md`; tested with fakes only |

## Prompting rules
- None. The source is resolved by job reference on the server, never a client path.

## Guards and gates
- The upscaled image is a new output and goes through the output guard like any render; a source that was withheld
  cannot be upscaled. ⤓ Download clean = scrubbed export. See `guards-text-and-output.md`, `publish-download-tribe.md`.

## Time and VRAM
- Port  a local port. Code peaks 3 GiB (2x) / 5 GiB (4x) — estimates, not measured; needed free = peak + 4.
- 4x-UltraSharp 256 → 1024 px took 4 s in pp (2026-10-05). The studio path was not live-measured
  (LOCAL_MOE_REFERENCE §15).

## Known pitfalls / failure modes
- It refuses while any ComfyUI port is busy (shared preflight), even though it needs little VRAM.
- Upscaling cannot fix anatomy or text errors; re-generate or edit first (Qwen 2.1 edit).
- Remix is not offered on upscale cards; Retry re-resolves the original source image.

## Evidence
- Tests: `tests/tools/test_image_upscale_tools.py`, `tests/studio/test_realism_wiring.py` (the Realism chip).
