# Mesh to photo

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose / how to start it
- Paints a photoreal product photo over a render of a 3D model, keeping its angle, zoom and framing.
- **📷 Photo** on a 3D card's hero still, or Image tab → `Klein 9B · 3D render → photoreal product shot` with any render.
- Prompt optional: empty = the workflow's product-photo wording; anything typed is added after it ("on white marble").

## Recipe (Pixaroma ep34-7 "Flux Klein 9b - 3D Model to Image - Keep the Angle", core nodes only)
| Setting | Value | Source |
|---|---|---|
| Model | Klein 9B distilled (`flux/flux-2-klein-9b`), qwen_3_8b TE (flux2), flux2-vae | [documented] workflow (int8 ConvRot there; bf16 here [inference]) |
| Latent | the render at ~1 MP, VAE-encoded, denoise 0.70 | [documented] (0.67-0.80 give the same picture at 4 steps) |
| Reference | the render shrunk to 0.25 MP → ReferenceLatent on positive and negative | [documented] (0.25 MP cleans smudges/torn edges) |
| Sampling | 4 steps, CFG 1, euler/simple; negative = ConditioningZeroOut | [documented] |
- Time / VRAM: 2.3 s at 1 MP, 22.8 GB on a 24 GB 4090 (workflow notes); the studio budgets 30 + 4 GiB (box Klein edit peak
  27.4-28.4 GiB). Non-commercial (Klein licence).

## Evidence
- `a local folder` (notes
