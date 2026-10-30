# CU-204 - Flow matching and rectified flow

**Objective.** Separate the velocity of one training pair, which is constant, from the field you integrate, which is not. Say what reflow changes. Taught by Dr. Denoise.

## The idea

Pick a data sample x_0 and a noise sample ε, and draw a straight line between them. Train a network to predict the direction of that line. Three groups published versions of this within weeks: Lipman et al. (flow matching), Liu et al. (rectified flow) and Albergo and Vanden-Eijnden (stochastic interpolants).

A common mistake, which an earlier draft of this very course made, is to conclude that sampling is a straight line and one Euler step is exact. It is not, and this lesson shows why.

## The maths

The path and the velocity of one pair:

```
x_t = (1−t) x_0 + t ε        d/dt x_t = ε − x_0     constant along the pair
```

But the network receives only x_t and t, not the pair. Many pairs pass through the same point, so least squares can only return their average:

```
u(x, t) = E[ ε − x_0 | x_t = x ] = ( x − E[x_0 | x_t = x] ) / t
```

Lipman et al. (2023, Theorem 2) prove that regressing on the per-pair target has identical gradients to regressing on u. Sampling integrates u from t = 1 to t = 0. As t falls, E[x_0 | x_t] changes from the data mean to one specific sample, so **u changes along the path**, and the path curves.

Rectified flow (Liu et al. 2022) uses this. Integrate the learned ODE to get pairs (x_1, x_0 = ODE(x_1)), then train a new network on straight lines between those pairs. The paper proves that this coupling does not increase any convex transport cost, and that repeating it straightens paths.

## In ComfyUI

The `CONST` class in `comfy/model_sampling.py` implements this: `noise_scaling` is σ·noise + (1−σ)·latent, with t written as σ, and `calculate_denoised` is x − σ·output, which is the formula above rearranged. So a flow model enters the same samplers as everything else, through a denoised estimate. `ModelSamplingDiscreteFlow` holds the shifted schedule (CU-206).

## Lab

Exact E[x_0 | x_t] is available for a Gaussian mixture, so this needs no trained network until the last step.

```text
t    x     E[e-x0 | x_t=x] measured   marginal u(x,t)
0.5  +0.0  -1.4784                    -1.4732
```

The average over real pairs is the field. Along one path it moves:

```text
along one marginal path, RMS change of velocity from t=1 to t=0: 2.610  (zero would be a straight line)
```

So Euler has real error, unless the data is a single point:

```text
steps  Euler RMS error   W1 to data   error if data were one point
1      1.6696            1.4806       4.4e-16
8      0.3168            0.1516       0.0e+00
64     0.0715            0.0186       0.0e+00
```

One point is the only case in which the per-pair picture is the whole truth. Now rectify:

```text
transport cost E|x1-x0|^2   independent pairs: 3.998   rectified pairs: 0.973   optimal (sorted, 1-D): 0.973
fraction of neighbouring paths that cross after rectification: 0.00000
one Euler step, W1 to data   flow matching net: 1.4143   rectified (reflow) net: 0.0327
```

In one dimension the rectified coupling is monotone, so it is optimal. A network trained on rectified pairs gets close to the data in a single step, and one trained on independent pairs does not.

## What is contested

Do not generalise "optimal" past one dimension: Liu et al. prove non-increasing cost, not optimal transport. Also, diffusion and flow are not rival physics. Both are ways to choose a path, and a Gaussian diffusion also has a deterministic ODE (CU-203). Which path needs fewest steps on real images is an empirical question.

## Sources

- [Lipman et al. 2022. Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747)
- [Liu, Gong, Liu 2022. Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow](https://arxiv.org/abs/2209.03003)
- [Albergo, Vanden-Eijnden 2022. Building Normalizing Flows with Stochastic Interpolants](https://arxiv.org/abs/2209.15571)
- [Esser et al. 2024. Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206)
- [ComfyUI v0.43.0, comfy/model_sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/model_sampling.py)
