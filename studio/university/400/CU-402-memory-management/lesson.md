# CU-402 - Memory management: who gets the GPU

**Objective.** Read the load and unload lines in a ComfyUI log, predict an eviction, and know which flags change what. Taught by Bit Bandit.

## The idea

There are several models, one card, and activations that need room as well. ComfyUI budgets before each load, and evicts only what it has to. Models stay loaded after a run, and this is why the second run is fast.

## The mechanism

From `load_models_gpu` and `free_memory` in `comfy/model_management.py`:

```
inference_memory = 0.8 GB + EXTRA_RESERVED_VRAM          (400 MB on Linux, or --reserve-vram)
extra_mem        = max(inference_memory, memory_required + reserved)
free_memory( total_model_size × 1.1 + extra_mem )
```

`memory_required` is what the caller estimates its run will need, so it grows with latent size and batch. Eviction candidates sort by (offloaded memory, largest first), then reference count, then size, and unloading stops once enough is free. If a model cannot fit whole, `partially_load` places what fits, and the rest stays in RAM. Then it works, slowly.

**Two regimes.** `enables_dynamic_vram` in `comfy/cli_args.py` turns dynamic VRAM on unless you pass `--disable-dynamic-vram`, `--highvram`, `--gpu-only`, `--novram` or `--cpu`. In that mode `free_memory` skips unloading dynamic models for other dynamic models, as the code's comment says this "works on-demand". The help text says `--lowvram` does nothing when it is on. The lab models the estimate-based path. We did not study the dynamic path in depth, and we make no timing claims about it.

**Other flags and events.** `--reserve-vram` keeps room for other software. On an out-of-memory error, `execute` in `execution.py` calls `unload_all_models`. `POST /free` is the manual route.

## Lab

The sizes are examples, not measurements. The arithmetic and order come from the code, simplified: this model unloads whole models, ignores reference counts, and ignores dynamic VRAM.

```text
minimum_inference_memory: 1.191 GB
encode the prompt                            free  19.00 GB   loaded: text_encoder 5.0
    evict text_encoder (5.0 GB)
sample                                       free  12.00 GB   loaded: unet 12.0
decode                                       free  11.70 GB   loaded: unet 12.0, vae 0.3
```

The text encoder had to go, even on a 24 GB card, because 12 GB × 1.1 plus 6.4 GB does not fit beside it. Then the VAE fits with no eviction. A small card:

```text
    unet does not fit: 4.61 of 12.00 GB on the GPU, the rest is streamed from RAM per layer
model share on the GPU: 38%. It runs, and each step copies the rest across PCIe.
```

Weights are simple arithmetic:

```text
  SD 1.x U-Net         fp32:   3.2 GB  fp16:   1.6 GB  fp8:   0.8 GB
  SDXL U-Net           fp32:   9.7 GB  fp16:   4.8 GB  fp8:   2.4 GB
```

The parameter counts, 860 million and 2.6 billion, are from Table 1 of the SDXL paper as we remember it. The PDF did not download during this audit, so we did not recheck them.

## Sources

- [ComfyUI v0.43.0, comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_management.py)
- [ComfyUI v0.43.0, comfy/model_patcher.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_patcher.py)
- [ComfyUI v0.43.0, comfy/cli_args.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/cli_args.py)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [Podell et al. 2023. SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952)
