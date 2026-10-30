# CU-413 - Prompt adherence evaluation

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the workshop. In CU-404, we built the pipeline. Now, in CU-413, we ask the hard question: *Did it actually listen?*

In generative AI, "prompt adherence" is not a binary switch. It is a geometric relationship. When you type "a red car," you are not just sending characters to a server; you are projecting a vector into a high-dimensional latent space. The diffusion model’s job is to denoise a random signal into an image that aligns with that vector. If the alignment is weak, the model hallucinates. If it is strong, the model obeys.

As engineers, we cannot rely on vibes. We need to measure the distance between the prompt embedding and the generated image’s latent representation. This lesson focuses on the mathematical foundation of **embedding space alignment**. We will look at why certain prompts fail to guide the diffusion process effectively by analyzing the geometry of the vectors involved. We will use cosine similarity as our primary metric for alignment, as it is invariant to the magnitude of the vectors, focusing purely on direction.

## The intuition

Imagine you are in a dark room with a flashlight (the prompt) and a wall (the latent space). The flashlight beam represents the direction of your intent. The wall has a texture (the noise). Your goal is to paint a specific shape on the wall.

If the flashlight is pointed exactly at the center of the target shape, the paint (the generated image) will be dense and clear. If the flashlight is pointed at a 90-degree angle to the target, the light barely touches the target area, and the paint will be sparse, noisy, or entirely in the wrong place.

In vector terms:
*   **Perfect Alignment:** The prompt vector and the image latent vector point in the exact same direction.
*   **Orthogonal Mismatch:** The prompt vector is perpendicular to the image latent vector. The prompt provides no directional guidance for that specific feature.
*   **Anti-Alignment:** The vectors point in opposite directions. The prompt actively suppresses that feature.

Most prompt failures are not "errors" in the traditional sense; they are **geometric misalignments**. The model is doing exactly what the math says it should do, but the math says the prompt vector is too far from the target concept vector.

## Under the hood (the mechanism; math in plain text, define every symbol)

To evaluate adherence, we must quantify the alignment between two vectors in the embedding space. Let $u$ be the prompt embedding vector and $v$ be the image latent feature vector. Both are $N$-dimensional vectors.

The standard metric for alignment is **Cosine Similarity**. It measures the cosine of the angle $\theta$ between the two vectors.

The formula is:

$$ \text{similarity}(u, v) = \frac{u \cdot v}{\|u\| \|v\|} $$

Where:
*   $u \cdot v$ is the **dot product** of the vectors. It is the sum of the products of their corresponding components: $\sum_{i=1}^{N} u_i v_i$.
*   $\|u\|$ is the **Euclidean norm** (magnitude) of vector $u$: $\sqrt{\sum_{i=1}^{N} u_i^2}$.
*   $\|v\|$ is the **Euclidean norm** of vector $v$.

The result is a scalar value in the range $[-1, 1]$.
*   **1.0**: The vectors are parallel and point in the same direction. Perfect adherence.
*   **0.0**: The vectors are orthogonal. No correlation. The prompt does not influence this specific latent dimension.
*   **-1.0**: The vectors are anti-parallel. The prompt actively contradicts the latent feature.

Why cosine and not Euclidean distance? In diffusion models, the *magnitude* of the embedding can vary based on the timestep or the specific encoder architecture (e.g., T5 vs. CLIP). However, the *direction* is what carries the semantic meaning. Cosine similarity normalizes out the magnitude, allowing us to measure pure semantic alignment.

In our lab, we simulate this in a 4-dimensional space to keep the math transparent. We define:
*   $vec\_a$: The image feature vector.
*   $vec\_b$: A prompt vector that perfectly matches $vec\_a$.
*   $vec\_c$: A prompt vector that is orthogonal to $vec\_a$.

## In ComfyUI

In ComfyUI, the text encoder is the first step in this geometric process. The `comfy/text_encoders` folder contains the implementations for various architectures. For example, `comfy/text_encoders/t5.py` contains the `T5` class, which converts text into a sequence of embeddings. These embeddings are then fed into the diffusion model.

However, ComfyUI does not natively expose a "Prompt Adherence Score" node in the standard workflow. The alignment happens implicitly during the denoising steps. To measure it explicitly, we must extract the latent representations and the prompt embeddings.

The `script_examples` folder provides the infrastructure to automate this. Specifically, `queue_prompt(prompt)` sends the job to the server, and `get_history(prompt_id)` retrieves the execution metadata. While `get_history` gives us the output images, it does not directly give us the intermediate latent vectors or the prompt embeddings in a format ready for cosine similarity calculation without custom node development.

Therefore, for this lab, we are simulating the core mathematical operation that *would* occur if we had access to these vectors. We are not using a specific ComfyUI node for the calculation itself, as no standard node in the provided evidence performs this specific post-hoc alignment scoring. The mechanism is theoretical here, grounded in the vector operations that underpin the attention mechanisms in models like `T5` or `FluxClipModel`.

## Lab

The lab script simulates two 4-dimensional feature vectors. It calculates the cosine similarity between a "perfect match" pair and an "orthogonal mismatch" pair. This demonstrates the binary extremes of prompt adherence: total alignment and total irrelevance.

We run the script with a fixed seed to ensure reproducibility. The script defines `vec_a` as `[1.0, 0.0, 0.0, 0.0]`. It defines `vec_b` as identical to `vec_a`, and `vec_c` as `[0.0, 1.0, 0.0, 0.0]`.

Here are the results from the lab execution:

```
RESULT sim_match = 1
RESULT sim_mismatch = 0
```

**What each line proves:**

1.  `RESULT sim_match = 1`: This proves that when the prompt vector and the image latent vector are identical (parallel), the cosine similarity is exactly 1.0. This represents **perfect prompt adherence**. The prompt provides maximum directional guidance to the diffusion process. In a real scenario, this would mean the generated image contains the exact features described by the prompt with high fidelity.

2.  `RESULT sim_mismatch = 0`: This proves that when the prompt vector is orthogonal to the image latent vector, the cosine similarity is exactly 0.0. This represents **zero prompt adherence** for that specific feature dimension. The prompt provides no directional guidance. In a real scenario, this would mean the model is free to hallucinate any feature in that dimension, as the prompt does not constrain it. This is often where "prompt drift" or unexpected artifacts occur.

These two lines establish the baseline for our evaluation. Any real-world prompt adherence score will fall between these two extremes. A score of 0.8 indicates strong adherence, while a score of 0.2 indicates weak adherence, suggesting the prompt is not effectively guiding the diffusion process in that latent subspace.

## Common mistakes

1.  **Confusing Magnitude with Direction:** Using Euclidean distance instead of cosine similarity. If your prompt embedding has a large magnitude but points in the wrong direction, Euclidean distance might be small, but the semantic alignment is poor. Always normalize your vectors before comparing.
2.  **Ignoring the Timestep:** The latent representation changes as the diffusion process progresses. Measuring alignment at the final step (t=0) is different from measuring it at the initial step (t=T). The prompt's influence is strongest in the early steps. If you measure adherence only at the end, you might miss early-stage misalignments that cause the model to wander.
3.  **Assuming Global Alignment:** A prompt can have high alignment for "red" but low alignment for "car." You must decompose the prompt into individual concepts and measure alignment for each. A single global score is often misleading.
4.  **Forgetting the Encoder:** Different text encoders (e.g., CLIP vs. T5) produce embeddings in different spaces. You cannot compare a CLIP embedding to a T5 embedding directly. You must ensure you are comparing vectors from the same encoder architecture.

## Go deeper

To understand the theoretical basis for why text can guide image generation, we look at the foundational work on learning visual models from natural language supervision.

**arXiv:2103.00020** - *Learning Transferable Visual Models From Natural Language Supervision*

This paper demonstrates that by pre-training on 400 million (image, text) pairs, a model can learn to align text embeddings with visual features. The key insight is that the "alignment" we are measuring in this lab is the result of this massive pre-training process. The model has learned that the vector for "red car" should be close to the vector for images of red cars. When we measure cosine similarity, we are essentially checking how well the model has maintained this learned alignment during the generation process. If the similarity drops, it means the diffusion process has drifted away from the learned alignment, resulting in poor prompt adherence.

