# Image to 3D splat

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


## Purpose
- One picture → up to 262,144 3D Gaussians (PLY, for SuperSplat / Spark viewers), a rough mesh from them (GLB, vertex
  colours) and a rendered still. Best on stylised objects (template note). MIT (VAST-AI / Tripo).

## Graph (official template `3d_triposplat_image_to_gaussian_splat`, flattened to API form)
| Step | Value | Source |
|---|---|---|
| Cut-out | LoadBackgroundRemovalModel `birefnet.safetensors` → RemoveBackground | [documented] template |
| Preprocess | erode 1, size 1024 | [documented] |
| Conditioning | DINOv3 ViT-H (`dino_v3_vit_h`) + Flux2 VAE | [documented] |
| Sampling | `triposplat_fp16`, KSampler 20 steps, CFG 3, dpmpp_2m/simple, seed 46 | [documented] |
| Decode | VAEDecodeTripoSplat 262,144 gaussians, seed 790219963981395 | [documented] |
| Outputs | SplatToFile3D **ply**; SplatToMesh 384/5/0/0.6/500/0.02/2 → GLB; RenderSplat 1 still, sharpen 2, #848484 | template; PLY + one still are [inference] (the template saves SPZ and a 75-frame orbit) |
- Validated against  a local port `/object_info` 2026-10-11; weights on disk (~3 GB). VRAM unknown: 12 GiB budgeted + 4.
- Output guard: the PLY and GLB are judged by the input picture; a PLY whose bytes happen to contain an image signature
  is withheld (fail safe).

## Evidence
- https://github.com/VAST-AI-Research/TripoSplat (fetched 2026-10-11), https://huggingface.co/VAST-AI/TripoSplat.
