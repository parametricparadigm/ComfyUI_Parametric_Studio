# CU-201 - Latent space and the VAE

**Objective.** Derive the VAE loss, explain the scale factor ComfyUI applies, and see what a regular latent space buys and costs. Taught by Professor Latent.

## The idea

Diffusion on a 1024×1024 RGB image handles three million numbers per step. A VAE trades that for a much smaller grid of latents, and the diffusion model works there. Rombach et al. (2021) built Stable Diffusion on this idea.

## The maths

A VAE (Kingma and Welling 2013, Rezende et al. 2014) has an encoder q(z|x) that outputs a mean μ and a variance σ², and a decoder p(x|z). It maximises a lower bound on log p(x):

```
log p(x) ≥ E_q [ log p(x|z) ] − KL( q(z|x) ‖ N(0, I) )
              reconstruction      keep latents near the prior
```

For a Gaussian q the KL has a closed form, summed over latent dimensions, and sampling is made differentiable by moving the noise outside:

```
KL = ½ Σ ( μ² + σ² − 1 − log σ² )        z = μ + σ · ε,   ε ~ N(0, I)
```

The weight on the KL term decides the trade. A high weight gives a smooth latent space and blurred reconstructions, and a low weight does the reverse.

## In ComfyUI

`VAEEncode` and `VAEDecode` in `nodes.py` call `VAE` in `comfy/sd.py`. A latent is `{"samples": [B, C, H/8, W/8]}`. The factor 8 and the channel count depend on the family, and `comfy/latent_formats.py` holds the constants:

| Format | scale_factor | shift_factor |
|---|---|---|
| SD 1.x | 0.18215 | none |
| SDXL | 0.13025 | none |
| SD3 | 1.5305 | 0.0609 |
| FLUX.1 | 0.3611 | 0.1159 |

Why a scale factor? Samplers assume latents with variance about 1, for example the √(1+σ²) in CU-206, and a VAE's raw output need not have that. Dividing by the measured spread fixes it.

The same file holds `latent_rgb_factors`, a plain linear map used for previews. That such a simple map gives a recognisable preview tells you these latents are still very image-like.

## Lab

A tiny VAE learns 8×8 images of one soft bar, whose position is the only true degree of freedom. First the KL formula is checked against brute force:

```text
KL(N(1.2,0.6^2) || N(0,1))  closed form 0.9108   Monte Carlo 0.9102
```

Then the trade, as the KL weight β rises:

```text
beta    reconstruction MSE per image   KL per image   latent std
0.0     0.0002                         18.562         2.909
0.001   0.0019                         9.058          1.459
0.05    0.0058                         4.102          1.063
1.0     0.0497                         1.704          0.690
```

```text
latent std per channel with a weak KL: 1.524 1.381   scale factor 1/std: 0.6853   std after scaling: 1.000
```

The second block is where a scale factor comes from. Now the classic demonstration: halfway between a bar on the left and a bar on the right.

```text
pixel midpoint           0.05 0.39 0.39 0.05 0.05 0.39 0.39 0.05
true bar at the middle   0.00 0.00 0.10 0.77 0.77 0.10 0.00 0.00
latent midpoint, beta 0.001 0.05 0.34 0.33 0.14 0.11 0.26 0.45 0.11
latent midpoint, beta 1.0   -0.00 -0.00 0.12 0.72 0.77 0.15 0.01 0.01
distance from a real bar at the middle:  pixel midpoint 12.115   beta 0.001: 9.762   beta 0.05: 12.322   beta 1.0: 0.047
```

The pixel midpoint is a double exposure. With β = 1 the latent midpoint is one bar in the right place, so the space has learned what "position" means. With a weak KL it does not work: the midpoint falls in a hole. So a smooth latent space has to be paid for, and the cost is the reconstruction error in the table above: 0.0497 against 0.0019.

## What is contested

Do not carry this picture over to Stable Diffusion unchanged. Rombach et al. describe their KL variant as imposing only a slight penalty, because reconstruction matters more for them, and they rely on diffusion to model the latents. So a straight line between two SD latents is not promised to be meaningful, and this toy, with one degree of freedom, cannot settle how meaningful it is. The VAE is also lossy: encode then decode does not return the same image.

## Sources

- [Kingma, Welling 2013. Auto-Encoding Variational Bayes](https://arxiv.org/abs/1312.6114)
- [Rezende, Mohamed, Wierstra 2014. Stochastic Backpropagation and Approximate Inference in Deep Generative Models](https://arxiv.org/abs/1401.4082)
- [Rombach et al. 2021. High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752)
- [ComfyUI v0.43.0, comfy/latent_formats.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/latent_formats.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
