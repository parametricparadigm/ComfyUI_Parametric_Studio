# Re-sync lips

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## What it is
A finished clip + a voice clip -> the same clip with its mouth synced to the voice. LatentSync is **not a ComfyUI node pack** here: it is the standalone
install `a local folder` (own venv; README_formatlab_tools.md: "installed, LipsyncPipeline imports OK on CPU, inference not run"), so there is no graph to
validate against `/object_info`. The route is the repo's `inference.sh` command: stage-2 512 config, 20 steps, guidance 1.5, DeepCache, seed 1247.

## Where it is offered
* Video tab entry `video:latentsync` (clip + voice).
* Deliverables on the Wan engine: `wan_talk: latentsync` (the shot renders as a silent Wan I2V clip, then the saved voice's line is synced onto it) and the
  **Lip-sync this clip** add-on on a finished Wan run's shot (adds a new take; pick it to re-join).

## Needs (read 2026-10-17)
`checkpoints/latentsync_unet.pt` (5.07 GB), `checkpoints/whisper/tiny.pt`, `checkpoints/auxiliary/models/buffalo_l`, the SD VAE from the offline HF cache. All are on
disk today. If one is missing the route is shown as not available and says how to queue it (needs the author's OK; nothing is downloaded by the studio):
`systemd-run --user --unit=model-dl-queue bash -c 'bash a local folder >> a local folder 2>&1'`
after putting a job for HF `ByteDance/LatentSync-1.6` (`latentsync_unet.pt`, `whisper/tiny.pt`) into `a local folder`.

## Time and VRAM
About 18-20 GB (the README); time unmeasured. Run offline (`HF_HUB_OFFLINE=1`). The pipeline resamples to 25 fps and crops the face to 512 px.

## Limits
consented subjects only: re-syncing a real person's mouth to other words is a deepfake.
