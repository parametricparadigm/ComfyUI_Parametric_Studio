# CU-203 - Score matching, Tweedie and the SDE view

**Objective.** Show that predicting noise, predicting the clean image and learning the score are one thing, and know when a sampler is solving an ODE and when an SDE. Taught by Dr. Denoise.

## The idea

The score of a density is the direction in which it rises fastest: s(x) = ∇ₓ log p(x). It needs no normalising constant, which is the hard part of density models. Hyvärinen (2005) showed that a score can be fitted without knowing the true score. Vincent (2011) made it practical by adding noise. Song and Ermon (2019) trained at many noise levels, and Song et al. (2020) unified everything as stochastic differential equations.

## The maths

Noise the data: x = x_0 + σε. Two exact results link the score of the noisy density p_σ to the denoiser.

**Tweedie's formula** (Efron 2011, who credits it to Tweedie through Robbins):

```
E[x_0 | x] = x + σ² · ∇ₓ log p_σ(x)
```

So the best possible denoiser D, the best noise estimate ε̂, and the score carry the same information:

```
D(x, σ) = x + σ² s(x)      ε̂(x, σ) = −σ s(x)      s(x) = (D(x, σ) − x) / σ²
```

**Vincent's identity.** For any function s, explicit and denoising score matching differ only by a constant that does not depend on s:

```
E_x ‖s(x) − ∇log p_σ(x)‖²  =  E_(x0,x) ‖s(x) − (x_0 − x)/σ²‖²  − C
```

The second form needs only pairs of clean and noisy samples, so a network can learn the true score without ever seeing it.

**The SDE view** (Song et al. 2020). A forward process dx = f dt + g dW has a reverse-time process (Anderson 1982), and also a deterministic probability-flow ODE with the same marginals at every t:

```
reverse SDE   dx = [ f − g² ∇log p_t(x) ] dt + g dW̄
PF-ODE        dx = [ f − ½ g² ∇log p_t(x) ] dt
```

With f = 0 and σ(t) = t, g² = 2t. The ODE becomes dx/dσ = −σ s(x) = (x − D(x, σ)) / σ. The SDE drift is twice that, plus fresh noise.

## In ComfyUI

`to_d` in `comfy/k_diffusion/sampling.py` is that derivative, (x − denoised) / σ, and `sample_euler` integrates it. CU-205 covers solvers and CU-207 covers samplers that add noise.

## Lab

The data is a Gaussian mixture, so the true score is known in closed form and needs no network.

```text
x     E[x0|x] measured   x + sigma^2 score(x)
-3.0  -2.0783            -2.0798
+0.0  +0.7392            +0.7366
```

A brute-force average over four million real pairs matches Tweedie's formula.

```text
model         ESM       DSM       DSM-ESM
s(x)=0        0.5197    1.0001    0.4804
s(x)=-x       2.4972    2.9774    0.4802
s(x)=exact    0.0000    0.4797    0.4797
```

Very different models, the same gap: Vincent's identity, measured. Minimising the right column minimises the left one.

```text
RMS(net - true score) after training on DSM only: 0.0268   (RMS of the score itself: 0.7199)
```

The network never saw the true score. Last, the two routes:

```text
Wasserstein-1 to data   ODE: 0.0471   SDE: 0.0209   floor (two real samples): 0.0163
same start, run twice   ODE RMS difference: 0.0000   SDE RMS difference: 2.3542
```

Both reach the data. The ODE is a function of its start. The SDE from one start lands somewhere different each time. Here the SDE is closer to the data at the same step count, which is one result on one toy, not a rule. See CU-207.

## Sources

- [Hyvärinen 2005. Estimation of Non-Normalized Statistical Models by Score Matching](https://www.jmlr.org/papers/v6/hyvarinen05a.html)
- [Vincent 2011. A Connection Between Score Matching and Denoising Autoencoders](https://doi.org/10.1162/NECO_a_00142)
- [Efron 2011. Tweedie's Formula and Selection Bias](https://doi.org/10.1198/jasa.2011.tm11181)
- [Anderson 1982. Reverse-time diffusion equation models](https://doi.org/10.1016/0304-4149%2882%2990051-5)
- [Song, Ermon 2019. Generative Modeling by Estimating Gradients of the Data Distribution](https://arxiv.org/abs/1907.05600)
- [Song et al. 2020. Score-Based Generative Modeling through Stochastic Differential Equations](https://arxiv.org/abs/2011.13456)
- [ComfyUI v0.43.0, comfy/k_diffusion/sampling.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy/k_diffusion/sampling.py)
