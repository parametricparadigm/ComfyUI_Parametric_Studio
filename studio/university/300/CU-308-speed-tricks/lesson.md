# CU-308 - Speed: distillation, caching, compile, fewer steps

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

**Instructor:** Dr. Denoise
**Course:** CU-308 (Architecture: The Machinery Inside the Models)
**Prerequisites:** CU-203, CU-204

Welcome back to the lab. You’ve learned how the models work; now we ask the only question that matters in production: *how fast?*

In CU-203, we watched the noise level $\sigma$ decrease step by step. In CU-204, we looked at the attention mechanisms. Today, we look at the machinery that makes those steps cheaper. We are going to discuss four distinct levers: **Distillation** (changing the model), **Caching** (reusing computation), **Compile** (optimizing execution), and **Fewer Steps** (reducing iterations).

Be precise. In this course, we do not guess. We measure.

## Why this matters

A standard diffusion model might require 50 to 100 steps to generate a single image. Each step involves a full forward pass through a massive neural network. If you are generating a batch of 1,000 images, that is 50,000 to 100,000 forward passes. At current hardware speeds, this is slow.

Speed is not just about waiting less; it is about throughput. If you can halve the number of steps without losing perceptual quality, you double your throughput. If you can cache half the attention computations, you halve your memory bandwidth usage. These are architectural decisions, not just "settings."

## The intuition

Imagine you are walking down a long, winding path (the diffusion process).
1.  **Fewer Steps:** You take bigger strides. You cover the same distance in fewer moves. This is risky; if your stride is too big, you might miss the path (lose quality).
2.  **Distillation:** You hire a guide who has walked the path a thousand times. They teach you a shortcut. You don't walk the whole winding path; you take a direct route that approximates the final destination.
3.  **Caching:** You notice that the first half of the path is always the same. So, you memorize it (or write it down) and skip re-walking it every time you start a new journey.
4.  **Compile:** You pave the path. Instead of walking on dirt (interpreted code), you walk on asphalt (optimized machine code). The path is the same, but you move faster.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let's formalize the cost. The primary cost metric is **NFE** (Number of Function Evaluations).

### 1. The Cost of Steps and CFG
In a standard sampler, each step requires evaluating the model's velocity or noise prediction.
Let $S$ be the number of sampling steps.
Let $C$ be the Classifier-Free Guidance (CFG) factor.
If CFG is enabled, we typically run the model twice per step: once with the prompt, once without (unconditional).
Therefore, the total NFE is:
$$ \text{NFE} = S \times (1 + \text{CFG\_enabled}) $$
If CFG is enabled, $\text{CFG\_enabled} = 1$, so $\text{NFE} = 2S$.
If CFG is disabled, $\text{NFE} = S$.

*Example:* If $S=50$ and CFG is on, $\text{NFE} = 100$. If we reduce $S$ to 4, $\text{NFE} = 8$. This is a 12.5x reduction in compute.

### 2. Distillation: Progressive and Consistency
**Progressive Distillation** (arXiv:2202.00512) works by training a new model to match the output of a previous model, but with half the steps.
Let $M_{2k}$ be a model that takes $2k$ steps. We train $M_k$ such that:
$$ M_k(x_t, t) \approx M_{2k}(x_t, t) $$
We repeat this: $M_{2k} \to M_k \to M_{k/2}$.
The key insight is that the "noise level" $\sigma$ is halved in the target distribution. The model learns to jump from noise level $\sigma$ to $\sigma/2$ in one step, rather than two.

**Consistency Models** (arXiv:2303.01469) take this further. They learn a function $f(x_t, t)$ that maps any point on the probability flow ODE trajectory directly to the data manifold (the final image).
$$ f(x_t, t) = x_0 $$
This allows for **one-step** generation. The model learns the "consistency" that all points on the trajectory lead to the same $x_0$.

### 3. Caching: Prefix and Node
**Prefix Caching** (seen in `comfy/ldm/qwen_image21`) exploits the fact that in autoregressive or long-context generation, the beginning of the sequence (the "prefix") remains constant.
Let $K$ and $V$ be the Key and Value tensors in Attention.
For a sequence of length $L$, we split it into a prefix of length $L_p$ and a suffix of length $L_s$.
$$ \text{Attention}(Q, K, V) = \text{Softmax}\left(\frac{Q K^T}{\sqrt{d}}\right) V $$
If the prefix $K_p, V_p$ is unchanged, we compute:
$$ \text{Cache}(K_p, V_p) $$
Then, for the new suffix, we only compute attention for the new tokens against the cached prefix. This reduces the quadratic complexity of attention for the repeated parts.

**Node Caching** (in `comfy_execution/caching.py`) is simpler. If a node's inputs have not changed, its output is identical.
$$ \text{Output} = f(\text{Inputs}) $$
If $\text{Inputs}_{new} == \text{Inputs}_{old}$, then $\text{Output}_{new} = \text{Output}_{old}$. We skip $f$.

## In ComfyUI

ComfyUI implements these mechanisms at different levels.

1.  **Node Caching:** The `comfy_execution` module uses `BasicCache`, `LRUCache`, and `HierarchicalCache`. When you run a workflow, ComfyUI checks if a node's inputs have changed. If not, it retrieves the output from the cache. This is crucial for iterative workflows where you tweak one parameter (e.g., a prompt) but keep the rest of the graph static.
2.  **Prefix Caching:** In the `comfy/ldm/qwen_image21` model, we see `PrefixCache`, `prefix_cached_attention`, and `KVCacheModel`. This is specific to the Qwen Image 2.1 architecture. It allows the model to reuse Key-Value pairs across steps or sequences, significantly speeding up long-context or multi-step generation.
3.  **Compile:** ComfyUI supports PyTorch's `torch.compile`. This is not a node you drag in; it is a backend optimization. It traces the graph and compiles it into optimized CUDA kernels. You enable this via settings or environment variables. It reduces overhead from Python loops and small kernel launches.
4.  **Distillation:** This is a model property, not a ComfyUI feature. You must load a distilled model (e.g., a 4-step SDXL Turbo or a Consistency Model). ComfyUI simply runs the model. The "speed" comes from the model architecture itself.

## Lab

We ran a simulation to quantify the trade-offs. We simulated a sampler with different step counts and CFG settings, and we solved a toy ODE to measure error vs. steps.

Here are the results:

```
RESULT nfe_steps_50_no_cfg = 50
RESULT nfe_steps_4_no_cfg = 4
RESULT speedup_steps_4_no_cfg = 12.5
RESULT nfe_steps_4_with_cfg = 8
RESULT speedup_steps_4_with_cfg = 6.25
RESULT error_1step_ode = 0.702404
RESULT error_4step_ode = 0.0909041
RESULT error_reduction_factor = 7.72686
```

**What this proves:**
1.  `RESULT nfe_steps_50_no_cfg = 50` vs `RESULT nfe_steps_4_no_cfg = 4`: Reducing steps from 50 to 4 reduces the number of function evaluations by a factor of 12.5.
2.  `RESULT speedup_steps_4_no_cfg = 12.5`: This confirms the linear relationship between steps and NFE when CFG is off.
3.  `RESULT nfe_steps_4_with_cfg = 8`: When CFG is on, the NFE doubles. 4 steps become 8 evaluations.
4.  `RESULT speedup_steps_4_with_cfg = 6.25`: The speedup is halved compared to no CFG. CFG is expensive.
5.  `RESULT error_1step_ode = 0.702404` vs `RESULT error_4step_ode = 0.0909041`: A 1-step solve has a much higher error than a 4-step solve.
6.  `RESULT error_reduction_factor = 7.72686`: Going from 1 step to 4 steps reduces the error by a factor of ~7.7. This is the "quality cost" of speed. You trade error for speed.

## Common mistakes

1.  **Confusing "Fewer Steps" with "Distillation":** You can reduce steps in a standard model, but quality degrades rapidly. Distilled models are *trained* to work with fewer steps. Do not expect a standard SDXL model to look good at 4 steps. Use a distilled model.
2.  **Ignoring CFG Cost:** If you use CFG, your NFE doubles. If you are trying to speed up generation, consider lowering the CFG scale or using a model that doesn't require CFG (like some Consistency Models).
3.  **Assuming Caching is Free:** Node caching saves compute, but it uses memory. If your cache is too large, you might run out of VRAM. Monitor your memory usage.
4.  **Compile Overhead:** `torch.compile` has a first-run overhead. It compiles the graph on the first run. Subsequent runs are faster. Do not judge performance on the first run.

## Go deeper

*   **arXiv:2202.00512**: *Progressive Distillation for Fast Sampling of Diffusion Models*. This paper introduces the method of halving steps iteratively.
*   **arXiv:2303.01469**: *Consistency Models*. This paper introduces the concept of mapping noise directly to data, enabling one-step generation.

Now, go back to your workflow. Check your step count. Check if you are using CFG. Check if your model is distilled. And ask yourself: *what is the noise level at this step?*

Class dismissed.

