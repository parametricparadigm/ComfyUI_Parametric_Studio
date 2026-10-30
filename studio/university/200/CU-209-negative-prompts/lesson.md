# CU-209 - Negative prompts and cfg 1.0

**Objective.** Say what a negative prompt does in the formula, why it does nothing at cfg 1, and what it costs. Taught by Dr. Denoise.

## The idea

A negative prompt is not a list of things to subtract. It is whatever you put in the second branch of CFG (CU-208).

## The maths

```
D = D_neg + (D_pos − D_neg) · cfg
```

This has the same form as CFG with the unconditional branch replaced. At cfg = 1 it reduces to D_pos and the negative cancels out, so it has no effect at all. That also explains why models distilled for cfg 1 have no working negative prompt without extra tricks.

If positive and negative are the same, D_pos − D_neg = 0, so cfg has nothing to amplify. The guidance is the difference, and the size of the cfg number means nothing on its own.

## In ComfyUI

`KSampler` takes `positive` and `negative`. `sampling_function` in `comfy/samplers.py` passes both to `calc_cond_batch`, then `cfg_function` applies the line above. When cfg is close to 1, `sampling_function` sets the second conditioning to None, so the negative is not evaluated at all. The `ConditioningZeroOut` node in `nodes.py` is the usual way to feed an all-zeros branch, which is not the same as encoding an empty prompt.

## Lab

Three classes at the corners of a triangle, with exact denoisers. Each row gives the share of samples nearest each class, and the median distance from the origin. The data sits at distance 3.

```text
settings                                 cat    dog    fox    distance
cfg 1, positive any, no negative         0.335  0.328  0.336  3.02
cfg 1, positive any, negative fox        0.335  0.328  0.336  3.02
cfg 3, positive any, negative any        0.335  0.328  0.336  3.02
cfg 1.5, positive any, negative fox      0.427  0.418  0.156  5.00
cfg 3, positive any, negative fox        0.494  0.490  0.016  12.39
cfg 7, positive any, negative fox        0.502  0.498  0.000  32.54
```

The first three rows are identical to every digit, and the lab asserts this. Then a real effect appears: the fox share drops from a third to 1.6 percent at cfg 3. But look at the last column. By cfg 3 the samples are four times further out than the data. The negative moves everything away from fox, including the samples that were never going to be foxes.

```text
cfg 3, positive dog, negative any        0.000  1.000  0.000  3.63
cfg 3, positive dog, negative fox        0.000  1.000  0.000  13.00
```

Same positive, same cfg: a specific negative pushes more than a neutral one, because the difference between dog and fox is larger than between dog and everything. That is a reason a long negative prompt can change the look of an image, not just remove things from it.

A 1-D or 2-D toy overstates the distance, since real images have many other directions to absorb the push, and real pipelines keep the result in range through the VAE. Read the direction of the effect, not its size.

## What is contested

The derivation of guidance by Ho and Salimans (2022) concerns conditional and unconditional models. A negative prompt is a practical extension with no equivalent derivation in that paper. Lin et al. (2023) use different negative prompts in some of their published examples. How much a given negative helps is an empirical matter for each model.

## Sources

- [Ho, Salimans 2022. Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598)
- [Lin, Liu, Li, Yang 2023. Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/abs/2305.08891)
- [ComfyUI v0.43.0, comfy/samplers.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/samplers.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
