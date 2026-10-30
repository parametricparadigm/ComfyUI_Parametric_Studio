# CU-314 - Flow-matching losses and velocity targets

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

Welcome back to the lab. I am Dr. Denoise. You have spent the last few weeks staring at UNets and VAEs, trying to understand how we coax structure out of static. In CU-202, you learned that diffusion models predict noise. Today, we are going to look under the hood of a different, arguably more elegant, paradigm: Flow Matching.

I have watched ten thousand images emerge from static. I have seen the pixels settle. But I have also seen the math break. And I have seen it fix itself. The key to that fix is understanding what the model is actually trying to predict. Is it the noise? Or is it the direction?

## Why this matters

Traditional diffusion models are often described as "denoising." You add noise to an image, and the model learns to subtract it. This works, but it is a bit like trying to drive a car by constantly checking how far you are from the destination and guessing the steering angle. It is effective, but it is not the most direct path.

Flow Matching (FM) changes the question. Instead of asking "how much noise is there?", we ask "what is the instantaneous velocity required to move from the noise distribution to the data distribution?"

This matters for three reasons:
1.  **Stability:** The evidence suggests that Flow Matching provides a "more robust and stable alternative for training diffusion models."
2.  **Efficiency:** By using Optimal Transport (OT) displacement interpolation, we can define paths that are "more efficient than diffusion paths," leading to faster sampling.
3.  **Geometric Clarity:** We are no longer fighting against a stochastic process; we are following a deterministic vector field.

## The intuition

Imagine you have a cloud of points representing pure noise, and a tight cluster of points representing real data (say, faces).

In a standard diffusion model, you might imagine a random walk. You take a step, add some randomness, take another step. It is messy.

In Flow Matching, we imagine a straight line connecting each noise point to its corresponding data point. We define a path $x_t$ that moves linearly from the noise $x_1$ to the data $x_0$ as time $t$ goes from 1 to 0 (or vice versa, depending on convention).

The "velocity" is simply the direction and speed of this movement. If you are at point $x_t$, the velocity tells you exactly where to go next to stay on the path to the data. It is the instantaneous direction of the probability flow.

This is distinct from score-based approaches. The score function points you toward the high-density regions of the data distribution (the gradient of the log-probability). It is a local guide. The velocity field in Flow Matching is a global guide for the specific path you are on. It is the derivative of the interpolation path.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let us define the symbols clearly.

*   $x_0$: A sample from the data distribution (the clean image).
*   $x_1$: A sample from the noise distribution (pure Gaussian noise).
*   $t$: A scalar timestep, typically in the range $[0, 1]$.
*   $x_t$: The interpolated point at time $t$.

In the simplest case, using linear interpolation (which is a specific instance of Gaussian probability paths), the path is defined as:

$x_t = (1 - t) * x_0 + t * x_1$

Note: In some conventions, $t=0$ is noise and $t=1$ is data. In our lab code, we will follow the convention where $t=0$ is data and $t=1$ is noise, or vice versa. Let us look at the lab code to see the specific convention used. The code defines `x_t = (1 - t) * data + t * noise`. This implies that at $t=0$, $x_t = data$, and at $t=1$, $x_t = noise$.

The velocity target $v$ is the derivative of this path with respect to $t$:

$v = \frac{d}{dt} x_t = \frac{d}{dt} [(1 - t) * x_0 + t * x_1] = -x_0 + x_1 = x_1 - x_0$

So, the velocity target is simply the difference between the noise and the data.

The model $v_\theta(x_t, t)$ is a neural network (often a Diffusion Transformer or UNet) that takes the current state $x_t$ and the timestep $t$ as input and predicts the velocity $v$.

The loss function is the Mean Squared Error (MSE) between the predicted velocity and the target velocity:

$L = \frac{1}{N} \sum_{i=1}^{N} || v_\theta(x_t, t) - (x_1 - x_0) ||^2$

This is a regression problem. We are regressing the vector field.

## In ComfyUI

ComfyUI is built to handle various sampling strategies. The `comfy/k_diffusion` folder contains the core mathematical implementations.

While the primary focus of `comfy/k_diffusion/sampling.py` is on samplers like `sample_euler` and `sample_heun` which implement algorithms from Karras et al. (2022), these samplers operate on the noise schedule $\sigma$. The distinction between "noise prediction" and "velocity prediction" is often handled in the model's output interpretation or the specific scheduler configuration.

The evidence highlights `comfy/k_diffusion/sampling.py` containing `get_sigmas_karras`, `get_sigmas_exponential`, and others. These define the noise schedule. The actual flow-matching loss calculation is typically part of the training loop, not the sampling loop. However, the architecture supports the necessary components.

For example, `comfy/ldm/hunyuan3dv2_1/hunyuandit.py` defines `HunYuanDiTPlain`, which returns the "predicted noise or velocity field." This indicates that the model architecture is agnostic to whether it is predicting noise or velocity; it is the training objective that defines the target.

Specific nodes for "Flow Matching Loss" are not covered in our sources. The mechanism is embedded in the training utilities and the model forward pass.

## Lab

Let us run a simple 1D experiment to see the numbers. We have three data points and three noise points. We pick a timestep $t=0.5$.

The lab code computes the interpolated point $x_t$ and the velocity target $v_{target}$. It then simulates a model prediction that is slightly off from the target, and calculates the loss.

Here are the results from the lab:

`RESULT x_t = [0.75, 0.5, 1.600000023841858]`
This proves that the interpolated point lies between the data and the noise. For the first point, data is 1.0 and noise is 0.5. At $t=0.5$, $x_t = 0.5*1.0 + 0.5*0.5 = 0.75$. The math checks out.

`RESULT v_target = [-0.5, -3.0, -2.799999952316284]`
This proves that the velocity target is indeed `noise - data`. For the first point, $0.5 - 1.0 = -0.5$. For the second, $-1.0 - 2.0 = -3.0$. The direction is from data to noise (since $t$ goes from 0 to 1 in this convention).

`RESULT model_pred = [-0.24590039253234863, -2.4293429851531982, -2.457879066467285]`
This is the simulated model output. It is close to the target but not exact, due to the added random noise in the simulation.

`RESULT loss = 0.169088`
This is the MSE loss. It quantifies how far the model's predicted velocity is from the true velocity. A lower loss means the model is better at predicting the direction of the flow.

## Common mistakes

1.  **Confusing Score and Velocity:** The score is the gradient of the log-density. The velocity is the time derivative of the path. They are related, but they are not the same. In Flow Matching, we regress the velocity.
2.  **Ignoring the Timestep:** The velocity field depends on $t$. A model that ignores $t$ will fail because the direction of the flow changes as you move along the path.
3.  **Wrong Interpolation Path:** Not all paths are created equal. Linear interpolation is simple, but Optimal Transport paths can be more efficient. Using the wrong path can lead to slower convergence or lower quality samples.
4.  **Assuming Determinism:** While the path is deterministic, the sampling process can still involve stochasticity if you use ancestral samplers. However, the core FM training is deterministic regression.

## Go deeper

To understand the theoretical underpinnings, you should read the foundational paper:

*   **arXiv:2210.02747**: "Flow Matching for Generative Modeling" by Lipman et al. This paper introduces the notion of Flow Matching, a simulation-free approach for training CNFs based on regressing vector fields of fixed conditional probability paths. It demonstrates that FM with diffusion paths is a robust alternative to standard diffusion training, and that using OT displacement interpolation leads to faster training and sampling.

Now, go back to your lab. What is the noise level at this step? It is not a question of magnitude, but of direction. Find the vector. Follow the flow.

