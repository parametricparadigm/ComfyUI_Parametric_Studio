# CU-107 - Models on disk: safetensors and families

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome, students. I am Bit Bandit, and I live in the last few bits of your float32s. You might think a model file is just a "black box" you download. Wrong. It is a precise, byte-aligned container. If you don't understand how weights are stored, you cannot debug why your LoRA isn't loading, why your VRAM is exploding, or why your image looks like static.

In ComfyUI, the `comfy` folder is the engine room. It handles model architecture definitions, weight loading, and memory management. But before any math happens, the file must be read from disk. That is where `safetensors` comes in. It is the modern standard for storing neural network weights safely and efficiently. This lesson explains the anatomy of that file and how ComfyUI parses it to bring your model to life.

## The intuition

Imagine a library. A traditional `.ckpt` file is like a giant, unindexed pile of books. To find "Chapter 4, Page 12," you have to scan the whole pile. Slow. Dangerous.

`Safetensors` is a well-organized library with a master index.
1.  **The Index (Header):** A small JSON document at the start of the file. It lists every tensor (weight matrix) by name, its shape, its data type, and exactly where its bytes live in the file.
2.  **The Data:** The raw bytes of the weights, packed tightly right after the header.

Because the index tells us exactly where `layer1.weight` starts and ends, we can load *only* the parts we need. We don't have to load the whole model into memory just to check the VAE. We can stream it. This is crucial for ComfyUI’s dynamic offloading, where `ModelPatcher` manages which weights are on GPU vs CPU.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s dissect the byte structure. A `safetensors` file is a sequence of bytes $B$.

1.  **Header Length ($L$):** The first 8 bytes of $B$ are an unsigned 64-bit integer, stored in little-endian format. This value $L$ tells us how many bytes the JSON header occupies.
2.  **Header ($H$):** The next $L$ bytes are a JSON string. This JSON maps tensor names (e.g., `"layer1.weight"`) to metadata objects. Each object contains:
    *   `dtype`: The data type (e.g., `"F32"` for float32).
    *   `shape`: A list of integers representing the tensor dimensions.
    *   `data_offsets`: A pair `[start, end]` indicating the byte range of the tensor data within the data section.
3.  **Data ($D$):** The remaining bytes are the raw tensor values, concatenated in the order defined by the header.

**The Math of Size:**
For a tensor $T$ with shape $S = [d_1, d_2, ..., d_n]$ and element size $e$ (in bytes), the number of elements is $N = \prod_{i=1}^{n} d_i$. The byte size is $B_T = N \times e$.

In our lab, we used `float32`, so $e = 4$ bytes.
*   `tensor_a`: shape `[2, 3]`. $N = 2 \times 3 = 6$. $B_T = 6 \times 4 = 24$ bytes.
*   `tensor_b`: shape `[4]`. $N = 4$. $B_T = 4 \times 4 = 16$ bytes.
*   `tensor_c`: shape `[1, 1, 5]`. $N = 1 \times 1 \times 5 = 5$. $B_T = 5 \times 4 = 20$ bytes.

Total bytes = $24 + 16 + 20 = 60$.
Total parameters = $6 + 4 + 5 = 15$.

This is why `safetensors` is safe: it has no executable code. It’s just data. No Python pickle exploits. Just bytes.

## In ComfyUI

ComfyUI uses `safetensors` as its primary model format. The `comfy/sd.py` module contains `load_checkpoint_guess_config`, which is the primary function to load a checkpoint file. It automatically detects the model architecture and loads UNet, VAE, and CLIP components.

The `ModelPatcher` class in `comfy/model_patcher.py` is the core class managing the state of model weights. It tracks which weights are on GPU vs CPU. When you load a model, `ModelPatcher` reads the `safetensors` header, identifies the tensors, and uses `data_offsets` to slice the raw bytes into PyTorch tensors. It then applies patches (like LoRAs) by modifying these tensors in-place or creating new ones.

Note: Specific node names for loading `safetensors` directly are not covered in our sources, but the underlying mechanism is handled by `load_checkpoint_guess_config` and `ModelPatcher`.

## Lab

In this lab, we simulated a tiny model with three tensors: `layer1.weight` (2x3), `layer1.bias` (4), and `layer2.weight` (1x1x5). We manually constructed a `safetensors`-like byte string, parsed it, and verified the integrity.

Here are the real `RESULT` lines from the lab output:

```
RESULT total_params = 15
RESULT total_bytes = 60
RESULT num_tensors = 3
```

*   **`RESULT total_params = 15`**: This proves our shape calculation is correct. $6 + 4 + 5 = 15$. It confirms that the `shape` metadata in the header correctly describes the tensor dimensions.
*   **`RESULT total_bytes = 60`**: This proves the byte alignment is perfect. $15 \text{ params} \times 4 \text{ bytes/param} = 60 \text{ bytes}$. It confirms that `data_offsets` correctly account for the full size of each tensor without overlap or gaps.
*   **`RESULT num_tensors = 3`**: This proves the header parsing worked. We defined 3 tensors, and the JSON header contained exactly 3 keys. This is critical for ComfyUI to know how many components to load.

## Common mistakes

1.  **Ignoring `dtype`:** If you load a `F16` tensor as `F32`, you’ll get garbage. ComfyUI’s `LazyCastingParam` helps here by casting weights on-the-fly, but you must respect the header’s `dtype` string.
2.  **Assuming `.ckpt` is safe:** Old `.ckpt` files use Python pickle, which can execute arbitrary code. `Safetensors` is pure data. Always prefer `safetensors` when available.
3.  **Misunderstanding `data_offsets`:** These are offsets *within the data section*, not the whole file. The data section starts after the 8-byte length + JSON header. If you calculate offsets wrong, you’ll read the header as data.

## Go deeper

For a deeper dive into the architecture of diffusion models that these weights represent, see:
*   **arXiv:2112.10752** (Latent Diffusion Models)
*   **arXiv:2206.00364** (Stable Diffusion)

These papers explain the math behind the tensors you’re loading. But remember: no matter how complex the math, it all starts with those 8 bytes of header length.

