# CU-311 - Mixed precision: where accumulation hides

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. I am Bit Bandit, and I live in the last few bits of your floating-point numbers. You think you are running "half precision" to save VRAM? Cute. But you are ignoring where I actually bite.

In ComfyUI, inference is a one-way street. You push pixels through the network, get an image, and discard the intermediate states. In that context, `fp16` is often safe. The error is small, and the final image looks fine. But the moment you step into training, fine-tuning, or even complex loss accumulation, the rules change. If you accumulate gradients or loss values in `fp16`, you are letting me eat your signal.

This lesson explains why `fp16` is a trap for accumulation. We will look at how rounding errors hide in the mantissa, why `fp32` is non-negotiable for gradient updates, and how ComfyUI’s architecture handles these precision boundaries.

## The intuition

Imagine you are counting pennies. You have a jar with $1,000,000$ pennies. If I add 1 penny to that jar, the total is $1,000,001$. But if your scale only has a resolution of 100 pennies, the scale still reads $1,000,000$. The penny didn't disappear; it just wasn't significant enough to change the reading.

`fp16` is that scale. It has a 10-bit mantissa. This means it can only represent about 15-16 significant decimal digits. When you add a very small number to a very large number, the small number often falls below the "resolution" of the large number. In `fp32`, with its 23-bit mantissa, that penny is visible. In `fp16`, it vanishes.

This is not a bug; it is the nature of fixed-width floating point. But in training, those "vanished pennies" are your gradients. If you lose them, your model stops learning.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let $x$ be a large value and $\epsilon$ be a small value. In floating point, the result of $x + \epsilon$ is determined by the precision of the format.

For `fp16`:
- Exponent bits: 5
- Mantissa bits: 10
- Smallest positive normal number: $\approx 6.1 \times 10^{-5}$
- Machine epsilon ($\epsilon_{mach}$): $\approx 9.8 \times 10^{-4}$

If $x = 1.0$ and $\epsilon = 0.0001$, the relative size of $\epsilon$ to $x$ is $10^{-4}$. This is comparable to $\epsilon_{mach}$. Depending on the rounding mode, $1.0 + 0.0001$ may round back to $1.0$.

For `fp32`:
- Exponent bits: 8
- Mantissa bits: 23
- Machine epsilon ($\epsilon_{mach}$): $\approx 1.2 \times 10^{-7}$

Here, $10^{-4}$ is much larger than $\epsilon_{mach}$. The addition is preserved.

In training, we compute gradients $g_i$ for each mini-batch. We accumulate them:
$$ G = \sum_{i=1}^{N} g_i $$

If $G$ is stored in `fp16`, and the individual $g_i$ are small relative to the running sum, the later terms may be lost. This is **catastrophic cancellation** in reverse: not subtracting close numbers, but adding small numbers to large ones until the small ones no longer register.

## In ComfyUI

ComfyUI is primarily an inference engine, but it supports fine-tuning and complex pipelines. The evidence shows that ComfyUI is aware of these precision traps.

In `comfy/ldm/seedvr/vae.py`, the `InflatedCausalConv3d` layer explicitly supports **fp16 accumulation**. This is a specific optimization for video restoration where the temporal convolution requires careful memory management. However, note the function `_fp16_accumulate_wanted`. This checks if the current tensor and device *support* the optimization. This implies that not all operations are safe in `fp16` accumulation, and the system must verify hardware and tensor compatibility.

In `comfy/ops.py`, we see `QuantLinearFunc` and `cast_bias_weight`. These utilities handle casting weights and biases to specific dtypes. The presence of `LazyCastingParam` in `comfy/model_patcher.py` allows weights to be cast on-the-fly. This is crucial: it means ComfyUI can keep weights in `fp16` for storage (saving VRAM) but cast them to `fp32` for computation if necessary, or vice versa.

The unit tests in `tests-unit/comfy_quant/test_mixed_precision.py` verify that `test_linear_input_act_respects_full_precision_mm_fallback`. This test ensures that when a linear layer is used, the system respects the full-precision matrix multiplication fallback. This is the safety net: if the hardware or the operation is not safe in `fp16`, ComfyUI falls back to `fp32`.

**Crucial Point:** While inference can safely run in `fp16`, **training and loss accumulation must upcast to `fp32`**. The evidence does not show a specific "training loop" in ComfyUI core (as it is an inference UI), but the presence of `comfy_quant` tests and the `seedvr` accumulation logic confirms that the architecture is built to handle mixed precision carefully. If you are using ComfyUI for fine-tuning (via external scripts or nodes that hook into the model), you **must** ensure that gradient accumulation happens in `fp32`.

## Lab

We ran a lab to demonstrate this. The lab code performs three steps:
1.  Adds a small number to a large number in `fp16` vs `fp32`.
2.  Sums 1000 small values in `fp16` vs `fp32`.
3.  Simulates gradient accumulation over 10 batches in `fp16` vs `fp32`.

Here are the real `RESULT` lines from the lab output:

```
RESULT fp16_sum = 1
RESULT fp32_sum = 1.0001
```
*Proof:* In `fp16`, $1.0 + 0.0001$ rounds to $1.0$. The small value is lost. In `fp32`, it is preserved. This is the fundamental rounding error.

```
RESULT fp32_accumulated = 0.1
RESULT fp16_accumulated = 0.100037
```
*Proof:* When summing 1000 values of $0.0001$, the true sum is $0.1$. `fp32` gets it exactly right (within floating point limits). `fp16` gets $0.100037$. The error is small here, but it is non-zero.

```
RESULT fp16_error = 3.66211e-05
RESULT fp32_error = 2.83122e-08
```
*Proof:* The error in `fp16` is roughly $1000\times$ larger than in `fp32`. This is the "hidden" error.

```
RESULT grad_accum_diff = 0.121216
```
*Proof:* When we simulate gradient accumulation over 10 batches, the difference between the `fp16` accumulated gradient and the `fp32` accumulated gradient is $0.121216$. This is a **massive** error for a gradient. If your learning rate is $10^{-4}$, this error is $1000\times$ larger than your update step. Your model will not learn correctly.

## Common mistakes

1.  **Assuming `fp16` is safe for all operations.** It is safe for inference. It is **not** safe for accumulation.
2.  **Forgetting to upcast gradients.** If you are fine-tuning, ensure that `grad_acc` is in `fp32`.
3.  **Ignoring hardware fallbacks.** Some GPUs (like MPS on Mac) may not support `INT8` or certain `fp16` optimizations. ComfyUI handles this via `test_int8_disabled_on_unsupported_device_falls_back_to_full_precision`, but you must ensure your custom training loops do the same.
4.  **Confusing storage precision with computation precision.** Weights can be stored in `fp16` to save VRAM, but they should be cast to `fp32` for matrix multiplications if accuracy is critical.

## Go deeper

For a deeper understanding of how lower-precision formats are designed to mitigate these issues, read:

*   **arXiv:2209.05433** - "FP8 Formats for Deep Learning". This paper discusses how 8-bit floating point formats (E4M3 and E5M2) are designed to balance range and precision, allowing for training that matches 16-bit quality. It highlights that even with 8-bit formats, careful scaling and accumulation strategies are required to prevent the precision loss we discussed.

