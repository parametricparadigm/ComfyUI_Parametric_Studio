# CU-211 - Quantization: int8, FP8, 4-bit and GGUF

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back, students. I’m Bit Bandit, and I live in the noise floor of your GPU. You think you’re running a "model," but I’m the one deciding if that pixel is a shadow or a ghost. In CU-205, we looked at the architecture. Today, we look at the *numbers*.

Why care? Because VRAM is expensive, and bandwidth is slow. If you store every weight as a 32-bit float, you are paying for 28 bits of precision you don’t need. Quantization is the art of throwing away bits to save memory and speed up math. But if you throw them away carelessly, you don’t get a faster model; you get a hallucinating mess. We are here to learn exactly where the rounding bites.

## The intuition

Imagine you have a ruler that is 127 units long. You want to measure objects ranging from a grain of sand (0.01) to a giant tree (5.0).

If you use a **per-tensor** scale, you stretch that ruler to fit the tree. The grain of sand? It’s so small it rounds to zero. You’ve lost it.
If you use a **per-row** scale, you give each row its own ruler. The row with the tree gets a big ruler; the row with the sand gets a tiny ruler. Now you can measure both accurately.

This is the core tension of quantization: **Granularity vs. Overhead**. The more scales you keep (per-tensor, per-row, per-group), the more accurate you are, but the more memory you spend storing those scales.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s look at the math of symmetric quantization, which is what our lab uses.

We have a weight matrix $W$. We want to map it to integers $Q$.
The formula is:
$Q = \text{round}(W / \text{scale})$

To get back to float (dequantize):
$W_{\text{dequant}} = Q \times \text{scale}$

**Symbols:**
*   $W$: The original float weight.
*   $Q$: The integer weight (e.g., int8 or int4).
*   $\text{scale}$: A floating-point number that maps the integer range to the float range.
*   $\text{round}(\cdot)$: Nearest integer rounding.

**The Scale Calculation:**
For symmetric quantization (centered at 0), the scale is determined by the maximum absolute value in the group.
$\text{scale} = \max(|W_{\text{group}}|) / \text{max\_int}$

*   For **int8**, $\text{max\_int}$ is 127 (range -128 to 127, but we use 127 for symmetry to avoid the -128 edge case).
*   For **int4**, $\text{max\_int}$ is 7 (range -8 to 7).

**The Error:**
The error is the difference between the original and the dequantized weight:
$\text{Error} = W - (Q \times \text{scale})$

In our lab, we measure this using Mean Squared Error (MSE) and Max Error. MSE tells us the average "noise" we’re injecting. Max Error tells us the worst-case single-value deviation.

## In ComfyUI

ComfyUI handles this via the `comfy_quant` module. The codebase includes `QuantLinearFunc` in `comfy/ops.py`, which is a custom autograd function for quantized linear layers, supporting FP8 and other formats.

The system is smart about hardware. As seen in `tests-unit/comfy_quant/test_mixed_precision.py`, there is a test `test_int8_disabled_on_unsupported_device_falls_back_to_full_precision`. This means if your GPU doesn’t support INT8 compute (or if you’re on MPS with a None device), ComfyUI doesn’t crash; it silently falls back to full precision. It also handles `W4A4` (4-bit weights, 4-bit activations) formats, loading them into parameters via `test_convrot_w4a4_loads_into_params`.

## Lab

In this lab, we quantize a small $3 \times 8$ weight matrix $W$ with rows of vastly different magnitudes (small, large, medium). We compare three strategies:
1.  **Per-tensor int8**: One scale for the whole matrix.
2.  **Per-row int8**: One scale per row.
3.  **4-bit group32**: One scale per group (here, per row, since rows are smaller than 32).

We calculate the Weight MSE, Output MSE, and Bytes Saved.

Here are the results from the lab:

`RESULT per_tensor_int8_weight_mse = 0.000156597`
`RESULT per_row_int8_weight_mse = 4.58291e-05`
`RESULT int4_group32_weight_mse = 0.015774`
`RESULT per_tensor_int8_bytes_saved_pct = 70.8333`
`RESULT per_row_int8_bytes_saved_pct = 62.5`
`RESULT int4_group32_bytes_saved_pct = 75`

**What this proves:**
1.  **Per-row beats Per-tensor:** The per-row MSE ($4.58 \times 10^{-5}$) is significantly lower than per-tensor ($1.56 \times 10^{-4}$). Why? Because the per-tensor scale was dominated by the large values in Row 1, crushing the small values in Row 0. Per-row scaling preserved them.
2.  **4-bit is noisier:** The 4-bit MSE ($0.0157$) is two orders of magnitude higher than int8. You are throwing away more bits, so the "noise" I inject is much louder.
3.  **The Cost of Precision:** Per-tensor int8 saves 70.8% of bytes. Per-row int8 saves only 62.5%. Why? Because you have to store a scale for *every row*. That overhead eats into your savings. 4-bit saves 75%, but at the cost of much higher error.

## Common mistakes

1.  **Ignoring Outliers:** If one weight in a row is 100x larger than the rest, per-row scaling will still crush the other 99 weights. This is why **group quantization** (like GPTQ or GGUF) exists—to isolate outliers in small groups.
2.  **Assuming int8 is Always Faster:** On some older GPUs, int8 compute is slower than float16 because the hardware has to dequantize on the fly. Check your hardware support.
3.  **Confusing Weight Quantization with Activation Quantization:** We quantized weights here. Activations (the inputs $x$) change every step. Quantizing them is harder and often requires dynamic scaling, which is slower.

## Go deeper

If you want to see how this scales to massive models, look at these papers:

*   **arXiv:2210.17323 (GPTQ):** This paper introduced a one-shot weight quantization method using approximate second-order information. It allows quantizing 175B parameter models to 3 or 4 bits with negligible accuracy degradation. It’s the foundation for many modern 4-bit models.
*   **arXiv:2305.14314 (QLoRA):** This paper introduced **NF4** (NormalFloat 4-bit), a data type optimized for normally distributed weights. It also introduced **double quantization**, where you quantize the quantization scales themselves to save even more memory. This is how you finetune 65B models on a single 48GB GPU.

Now, go forth and break your models. I’ll be in the bits, watching.

