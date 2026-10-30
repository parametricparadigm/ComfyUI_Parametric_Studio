# CU-205 - Samplers are ODE solvers

**Objective.** Write Euler, Heun and DPM++ 2M from their formulas, measure their order of accuracy, and compare them fairly by model calls rather than by steps. Taught by Dr. Denoise.

## The idea

With a deterministic sampler, the image is decided the moment the starting noise is drawn. The probability-flow ODE (CU-203) maps noise to data, and a sampler is a numerical method for that ODE. Karras et al. (2022) set this out, and it turns a mysterious list of names into ordinary numerical analysis.

## The maths

The ODE, in terms of the denoiser D:

```
dx/dσ = (x − D(x, σ)) / σ
```

```
Euler     d = (x − D(x, σ_i)) / σ_i
          x ← x + d · (σ_(i+1) − σ_i)

Heun      x' = x + d · (σ_(i+1) − σ_i)
          d' = (x' − D(x', σ_(i+1))) / σ_(i+1)
          x ← x + (d + d')/2 · (σ_(i+1) − σ_i)        last step to σ = 0 uses Euler

DPM++ 2M  λ = −log σ,  h = λ_(i+1) − λ_i,  r = (λ_i − λ_(i−1)) / h
          D̄ = (1 + 1/(2r)) D_i − 1/(2r) D_(i−1)
          x ← (σ_(i+1)/σ_i) x − (e^(−h) − 1) D̄
```

Euler is first order: double the steps, halve the error. Heun is second order and costs two model calls per step. DPM++ 2M (Lu et al. 2022) is second order and costs one, because it reuses the previous D. It works on the denoised prediction and in log σ, which that paper shows is more stable under large guidance.

## In ComfyUI

These are `sample_euler`, `sample_heun` and `sample_dpmpp_2m` in `comfy/k_diffusion/sampling.py`, and the formulas above are read from that code. The names offered in the KSampler widget are `KSAMPLER_NAMES` in `comfy/samplers.py`, plus `ddim` and two UniPC variants.

Note: `heun` at 20 steps costs about 40 calls. Comparing it with `euler` at 20 steps is not a fair test.

## Lab

The lab swaps the network for the exact denoiser of a Gaussian mixture. So every error below is the solver's, and none is the model's.

```text
steps       euler NFE  wrong        heun NFE  wrong    dpmpp_2m NFE  wrong
10       0.151898 10   0.0328   0.150810 19   0.0003   0.215795 10   0.0053
40       0.036909 40   0.0055   0.004994 79   0.0005   0.006319 40   0.0000
160      0.009174 160  0.0003   0.000281 319  0.0000   0.000330 160  0.0000
```

Each sampler has three columns: median error, model calls, and the share of samples that landed in the wrong mode. Now the slope of the median error:

```text
sampler    10-40   40-160  160-640
euler      1.02    1.00    1.00
heun       2.46    2.07    2.03
dpmpp_2m   2.55    2.13    2.04
```

Those are the textbook orders, measured. Two more lessons are in this table. First, the "wrong" column. A few paths start near the boundary between modes, and a small step error sends them to a different mode: at 10 Euler steps 3.3 percent of samples ended on the other side. That is why a change of step count can change the composition of an image and not just its details. Second, the fair comparison, at the same budget:

```text
euler      20 steps   20 calls  W1 = 0.1205
heun       10 steps   19 calls  W1 = 0.1487
dpmpp_2m   20 steps   20 calls  W1 = 0.0384
```

## What is contested

Which sampler is best on real models has no general answer. Order describes behaviour as steps grow, while most users work at 10 to 30 steps with a network that has errors, and CFG changes the ODE (CU-208). This toy's ranking is a measurement of this toy.

## Sources

- [Karras, Aittala, Aila, Laine 2022. Elucidating the Design Space of Diffusion-Based Generative Models](https://arxiv.org/abs/2206.00364)
- [Lu et al. 2022. DPM-Solver++: Fast Solver for Guided Sampling of Diffusion Probabilistic Models](https://arxiv.org/abs/2211.01095)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
