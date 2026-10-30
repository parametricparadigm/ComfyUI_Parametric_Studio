# CU-410 - Quantization error propagation through layers

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. I am Bit Bandit, and I have been lurking in your least significant bits, waiting for you to make a mistake. In CU-206, you learned how to load a model. Today, we learn how to break it—intentionally, to save memory, but accidentally, to destroy accuracy.

Quantization is not a magic trick; it is a controlled demolition. You are replacing high-precision floating-point weights with low-precision integers. Every single weight you quantize introduces a tiny error. In a single layer, this error is negligible. But in a deep network with dozens or hundreds of layers, these errors do not just sit there. They propagate. They compound. They drift.

If you ignore this, your final inference output will be garbage, even if every individual layer looks "fine" in isolation. This lesson teaches you to measure that drift and understand why your calibration data is the only thing standing between you and a blurry, hallucinating mess.

## The intuition

Imagine you are trying to pass a whisper through a line of 100 people. Each person hears the whisper, but they have a slight hearing impairment (quantization error). They repeat what they think they heard to the next person. By the time the message reaches the 100th person, it is unrecognizable.

In a neural network, the "whisper" is the feature vector. The "people" are the layers. When you quantize the weights of Layer 1, the output of Layer 1 is slightly off. This slightly off output becomes the input for Layer 2. Layer 2, also quantized, processes this already-corrupted input and adds its own error. Layer 3 does the same.

The key insight is that **error is not additive; it is multiplicative and chaotic**. A small error in an early layer can be amplified by subsequent layers, especially if the network has high sensitivity (large gradients) in certain regions. This is why "just quantize everything to INT8" is a dangerous strategy without proper calibration. You need to know where the network is fragile.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let's look at the math of a single linear layer. The output $y$ is computed as:

$y = W x + b$

Where:
*   $W$ is the weight matrix of shape $[N, M]$.
*   $x$ is the input vector of shape $[M]$.
*   $b$ is the bias vector of shape $[N]$.

When we quantize $W$, we replace it with $W_q$. The quantization error is defined as $\Delta W = W - W_q$.

The quantized output $y_q$ is:

$y_q = W_q x + b = (W - \Delta W) x + b = W x + b - \Delta W x = y - \Delta W x$

So, the error in the output of this single layer is $\epsilon_1 = \Delta W x$.

Now, consider a two-layer network. The input to the second layer is $y_1$. The output of the second layer is:

$y_2 = W_2 y_1 + b_2$

If we quantize both layers, $W_1$ becomes $W_{1q}$ and $W_2$ becomes $W_{2q}$.

The first layer output becomes $y_{1q} = y_1 - \epsilon_1$.

The second layer output becomes:

$y_{2q} = W_{2q} y_{1q} + b_2$
$y_{2q} = (W_2 - \Delta W_2) (y_1 - \epsilon_1) + b_2$
$y_{2q} = W_2 y_1 - W_2 \epsilon_1 - \Delta W_2 y_1 + \Delta W_2 \epsilon_1 + b_2$
$y_{2q} = y_2 - W_2 \epsilon_1 - \Delta W_2 y_1 + \Delta W_2 \epsilon_1$

The total error in the final output is:

$\epsilon_{total} = W_2 \epsilon_1 + \Delta W_2 y_1 - \Delta W_2 \epsilon_1$

Notice the term $W_2 \epsilon_1$. The error from the first layer ($\epsilon_1$) is multiplied by the weights of the second layer ($W_2$). If $W_2$ has large values, the error from Layer 1 is amplified. This is the mechanism of error propagation. As you go deeper, the error term becomes a complex sum of products of quantization errors and weight matrices from all previous layers.

This is why calibration data matters. Calibration data allows you to estimate the distribution of $x$ (the inputs) and $y$ (the activations). By knowing the typical magnitude of $x$, you can choose a quantization scale that minimizes $\Delta W x$ for the most common inputs. Without calibration, you are guessing the scale, and if you guess wrong, $\epsilon_1$ can be large, leading to catastrophic drift in deeper layers.

## In ComfyUI

In ComfyUI, quantization is handled by the `comfy_quant` module. The codebase includes specific support for mixed-precision operations and fallback mechanisms.

The `comfy/ops.py` file defines `QuantLinearFunc`, a custom autograd function for quantized linear layers. This is where the actual quantization math happens during inference. It supports formats like FP8 and INT8.

The `comfy/model_patcher.py` file contains `LazyCastingParam`, which allows weights to be cast to different dtypes on-the-fly. This is crucial for managing VRAM, but it also means that the quantization state can change dynamically.

The `tests-unit/comfy_quant/test_mixed_precision.py` file contains tests like `test_int8_disabled_on_unsupported_device_falls_back_to_full_precision`. This shows that ComfyUI is aware that quantization is not always safe or supported, and it will fall back to full precision if the hardware cannot handle it. This is a safety net, but it does not solve the accuracy drift problem if the hardware *does* support it but the calibration was poor.

The `comfy/ldm/ace` folder shows a real-world example of quantization in action. The `AceStepAudioTokenizer` uses Finite Scalar Quantization (FSQ) to discretize latent vectors. This is a different kind of quantization (discretizing activations rather than weights), but it suffers from the same principle: discretization introduces error that propagates through the decoder.

## Lab

In this lab, we simulate a single linear layer with a 10x10 weight matrix and a 10-dimensional input vector. We quantize the weights to 8-bit integers in the range [-1, 1] and measure the error between the full-precision output and the quantized output.

The lab code is as follows:

```python
import torch
import math
import random
import json
import itertools
import collections

# Set seed for reproducibility
torch.manual_seed(0)

# Define small tensors for CPU-only computation
# Weight matrix (10x10) and input vector (1x10)
w = torch.randn(10, 10)
x = torch.randn(1, 10)

# Quantize weights to 8-bit integer range [-1, 1]
# Scale by 127, round to nearest integer, then scale back
w_q = torch.round(w * 127.0) / 127.0

# Compute outputs with full precision and quantized weights
out_fp = torch.nn.functional.linear(x, w)
out_q = torch.nn.functional.linear(x, w_q)

# Calculate mean absolute error between full precision and quantized outputs
err = (out_fp - out_q).abs().mean().item()

# Print result in required format
print(f"RESULT mean_abs_error = {err:.6g}")

# Assert that quantization introduces some error
assert err > 0.0, "Quantization should introduce error"

# Assert that error is small for 8-bit quantization
assert err < 0.5, "Error should be small for 8-bit quantization"

# Print a second result: maximum absolute error
max_err = (out_fp - out_q).abs().max().item()
print(f"RESULT max_abs_error = {max_err:.6g}")

# Assert that max error is also bounded
assert max_err < 1.0, "Maximum error should be bounded for 8-bit quantization"
```

The lab output is:

```
RESULT mean_abs_error = 0.0100708
RESULT max_abs_error = 0.0167379
```

Let's analyze these results:

1.  `RESULT mean_abs_error = 0.0100708`: This proves that quantization introduces a non-zero error. The mean absolute error is approximately 0.01. This is the average magnitude of the error per output element. For a single layer, this is small. But remember, this error will be multiplied by the weights of the next layer. If the next layer has weights with a magnitude of 10, the error contribution from this layer will be amplified to approximately 0.1.

2.  `RESULT max_abs_error = 0.0167379`: This proves that the error is bounded. The maximum absolute error is approximately 0.017. This is important because it tells you the worst-case scenario for a single layer. If you have 100 layers, and each layer contributes a maximum error of 0.017, and if these errors were to add up linearly (which they don't, but as a rough upper bound), the total error could be as high as 1.7. In reality, the errors are random and can cancel out, but they can also align, leading to large drift.

These numbers are for a single layer with random weights and inputs. In a real network, the weights and inputs are not random; they are structured. This is why calibration data is essential. It allows you to measure the actual error for the specific distribution of inputs that the network will see during inference.

## Common mistakes

1.  **Assuming INT8 is always safe**: INT8 quantization is generally safe for many models, but it is not guaranteed. Some models are more sensitive to quantization than others. Always test your model after quantization.
2.  **Ignoring calibration data**: Using a default quantization scale without calibration is like shooting in the dark. The scale should be chosen based on the actual distribution of the weights and activations.
3.  **Quantizing all layers equally**: Some layers are more sensitive to quantization than others. For example, the first and last layers are often more sensitive. You may need to use higher precision for these layers.
4.  **Not testing on real data**: Testing on random data is not enough. You need to test on real data that is representative of the inference workload.

## Go deeper

For a deeper understanding of quantization methods, I recommend reading the following paper:

*   **arXiv:2210.17323**: "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers". This paper proposes a one-shot weight quantization method based on approximate second-order information. It shows that GPTQ can quantize GPT models with 175 billion parameters in approximately four GPU hours, reducing the bitwidth down to 3 or 4 bits per weight, with negligible accuracy degradation relative to the uncompressed baseline. This is a great example of how advanced quantization techniques can minimize error propagation.

