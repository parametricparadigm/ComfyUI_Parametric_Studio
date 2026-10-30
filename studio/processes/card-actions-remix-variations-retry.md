# Remix, variations and retry

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Tested on the author's old stack.


## Purpose / when to use it
Iterate on a result without retyping: more takes of the same prompt, a new seed, the same settings with edits, image to
video, a 2× upscale, or a retry after a VRAM refusal.

## Step-by-step in the studio UI
- **takes** chip (image entries, 1-4): N images in one job with consecutive seeds, under one VRAM check.
- **Cancel**: while the job is queued, writing the prompt, or waiting for the GPU.
- **↺ Remix**: puts entry, settings, fields, LoRA picks and the final prompt back in the composer. Reference files are NOT
  carried: drop them again (the card says so).
- **🎬 Animate** (finished image): switches to the Video tab; drag the image from the card into the `still`/`image` slot.
- **✦ Variations**: the same job (prompt as shown, settings, refs) with a new random seed. On a creative-take card it
  renders that creative take alone; on a LoRA card of a pair, a new pair.
- **🧍 10 poses** (finished plain image, 2026-10-17): N new pictures of the same person, setting and outfit in different poses, edited from that picture; contact sheet with
  per-picture re-render. See [pose-set.md](pose-set.md).
- **⤢ Upscale** (per image): 2× as a new card (`upscale:image`, ESRGAN), passed by job reference.
- **Retry** (failed/interrupted): the same job, new seed, refs re-validated. **Queue when free**: the same, but a VRAM/lock
  refusal waits in the queue instead of failing.
- **Copy prompt**, **prompt** details (final text; "not enhanced" if it fell back), **⤓ Download clean** (scrubbed export).
- Character sheet cards add **✂ Faceless crops** per shot.

## Optimal settings
| Setting | Value | Source |
|---|---|---|
| Takes | 1 while exploring a prompt, 4 for a pick-the-best round (one model load) | `MAX_TAKES = 4` in the image tools |
| Seed on Retry/Variations | random new seed; character jobs keep the character's locked seed | `server._studio_retry` |
| Queue when free | re-tries every 30 s for up to 30 min | `JobStore(wait_s=30, wait_max_s=1800)` |
| Upscale from a card | 2× (first option); 4× via the upscale entry | `variants.UPSCALE_SETTINGS` |

## Prompting rules
- Retry/Variations reuse the enhanced prompt the card showed; no second rewrite. To change wording, Remix.
- Remix of an edit keeps the target text raw (edits are never enhanced).

## Guards and gates
- Every retry is a new request: the text guard runs again on its prompt and fields; refs are re-resolved (never trusted
  from the old record). A generator no longer offered, or now unavailable, refuses the retry.
- Outputs go through the output guard like any job; see `guards-text-and-output.md`. Downloads are scrubbed (`publish-download-tribe.md`).

## Time and VRAM
- Outputs are content-hashed: an identical request (prompt, refs, size, seed) reuses finished takes instantly ("reused").
- Upscale 2×/4× peaks 3/5 GiB (code estimates); 4x-UltraSharp 256→1024 px took 4 s in pp (LOCAL_MOE_REFERENCE §15).

## Known pitfalls / failure modes
- Remix starts without the reference files; a job that needs them refuses until you drop them again.
- An upscale that lost its source image says so; upscale again from the source card.
- "Lost track of this job — refresh the page" = the card's job store entry is stale; reload.
- A creative take's Retry is that take alone; to get a fresh pair, retry the LoRA card.

## Evidence
- Tests: `tests/studio/test_jobs.py`, `tests/chatbox/test_studio_routes.py`, `tests/chatbox/js/*.test.mjs`.
