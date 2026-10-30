# CU-505 - History 5: CLIP and contrastive learning

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back. You have spent the last few weeks staring at diffusion models, watching noise vanish into pixels. But you have ignored the most critical question: *how does the model know what "a cat" is?*

In traditional computer vision, we trained classifiers to predict from a fixed list of 1,000 categories. This is rigid. If you want to detect a "rusty bicycle," you need new labels. CLIP (Contrastive Language-Image Pre-training) shattered this paradigm. By training on 400 million (image, text) pairs from the internet, CLIP learned a shared vector space where images and text live side by side. It does not classify; it *matches*. This zero-shot capability is the backbone of modern generative AI. Without the geometric alignment of CLIP, your diffusion model is blind. It has no idea what your prompt means.

## The intuition

Imagine a vast, high-dimensional ballroom. On one side, we have images; on the other, text captions.

In a naive system, "a photo of a dog" and "a picture of a puppy" might be far apart, while "a photo of a dog" and "a photo of a cat" might be close. This is useless.

CLIP uses **contrastive learning**. The rule is simple:
1.  **Pull together** the embeddings of an image and its correct caption.
2.  **Push apart** the embeddings of an image and *every other* caption in the batch.

We do not tell the model "this is a dog." We tell it, "This image goes with *this* text, and *not* with *that* text." By repeating this millions of times, the model learns a geometry where semantic meaning is distance. If two vectors are close, they mean the same thing. If they are far, they do not.

## Under the hood (the mechanism; math in plain text, define every symbol)

The core of CLIP is the **InfoNCE loss**, a form of cross-entropy applied to similarity scores.

Let $N$ be the batch size. We have $N$ image embeddings $\mathbf{I}_i$ and $N$ text embeddings $\mathbf{T}_j$.

**Step 1: Normalization**
First, we normalize the vectors to unit length. This ensures we are comparing *direction* (semantic meaning) rather than *magnitude* (intensity).
$$ \hat{\mathbf{I}}_i = \frac{\mathbf{I}_i}{\|\mathbf{I}_i\|_2} $$
$$ \hat{\mathbf{T}}_j = \frac{\mathbf{T}_j}{\|\mathbf{T}_j\|_2} $$

**Step 2: Similarity Matrix**
We compute the cosine similarity between every image and every text in the batch. This creates an $N \times N$ matrix $S$.
$$ S_{ij} = \hat{\mathbf{I}}_i \cdot \hat{\mathbf{T}}_j $$
Here, $S_{ij}$ is the dot product of normalized image $i$ and text $j$. The diagonal elements $S_{ii}$ represent the "correct" pairs. The off-diagonal elements $S_{ij}$ (where $i \neq j$) represent "incorrect" pairs.

**Step 3: Temperature Scaling**
We divide by a temperature parameter $\tau$ (typically 0.07 in CLIP). This sharpens the probability distribution, making the model more confident in its distinctions.
$$ Z_{ij} = \frac{S_{ij}}{\tau} $$

**Step 4: Cross-Entropy Loss**
We treat this as a classification problem. For image $i$, the "correct" class is text $i$. The loss is the negative log-likelihood of the correct pair, normalized by the sum of exponentials of all pairs (the softmax denominator).

The total loss is the average of the image-to-text direction and the text-to-image direction:
$$ \mathcal{L} = \frac{1}{2} \left( \mathcal{L}_{I \to T} + \mathcal{L}_{T \to I} \right) $$

Where:
$$ \mathcal{L}_{I \to T} = -\frac{1}{N} \sum_{i=1}^{N} \log \frac{\exp(Z_{ii})}{\sum_{j=1}^{N} \exp(Z_{ij})} $$

Geometrically, this loss function minimizes the distance between matched pairs and maximizes the distance between unmatched pairs in the vector space.

## In ComfyUI

While CLIP is the foundation, ComfyUI implements the *encoders* that produce these embeddings.

*   **Text Encoders:** The `comfy/text_encoders` folder contains the logic to convert your prompt into the text embedding $\mathbf{T}$. For example, `FluxClipModel` in `flux.py` wraps the CLIP model used by Flux. `T5` in `t5.py` provides the T5 encoder. These modules take your string, tokenize it, and output the vector that will be compared against the image latent.
*   **Image Encoders:** The `comfy/image_encoders` folder contains vision transformers like `Dino2Encoder` in `dino2.py`. While DINOv2 is not CLIP itself, it uses similar attention mechanisms to extract semantic features from images, often used for conditioning or control.

Note: The specific CLIP training code is not in ComfyUI; ComfyUI uses the *pre-trained weights* of these encoders. We do not train CLIP in ComfyUI; we *use* its geometry.

## Lab

In this lab, we simulate a mini-CLIP training step with a batch size of 4. We create 4 image vectors and 4 text vectors. The "correct" pairs are on the diagonal (img0-text0, img1-text1, etc.). We normalize them, compute the similarity matrix, and calculate the InfoNCE loss.

Here are the real `RESULT` lines from the lab output:

```
RESULT sim_matrix = [[0.9950371384620667, 0.09950371831655502, 0.0, 0.7432941198348999], [0.09950371831655502, 0.9950371384620667, 0.09950371831655502, 0.668964684009552], [0.0, 0.0, 0.9950371384620667, 0.0], [0.7739572525024414, 0.7739572525024414, 0.07035975158214569, 0.9986177682876587]]
RESULT diag_sims = [0.9950371384620667, 0.9950371384620667, 0.9950371384620667, 0.9986177682876587]
RESULT loss_it = 0.028542419895529747
RESULT loss_ti = 0.029429947957396507
RESULT clip_loss = 0.028986183926463127
RESULT all_assertions_passed = True
```

**What each proves:**
1.  **`sim_matrix`**: The diagonal values (top-left to bottom-right) are the highest in their respective rows and columns. For example, in row 0, `0.995` is much higher than `0.099` or `0.743`. This proves the geometric alignment: correct pairs are closer.
2.  **`diag_sims`**: These are the similarities of the correct pairs. They are all very high (>0.99), indicating strong alignment.
3.  **`loss_it` / `loss_ti`**: These are the cross-entropy losses for image-to-text and text-to-image directions. They are low (~0.028), indicating the model has successfully distinguished correct pairs from incorrect ones.
4.  **`clip_loss`**: The average of the two directions. This is the final scalar value the optimizer would minimize during training.
5.  **`all_assertions_passed`**: The code verified that for every image, its correct text had the highest similarity, and vice versa. This confirms the core mechanism of contrastive learning works.

## Common mistakes

1.  **Forgetting Normalization:** If you compute dot products on unnormalized vectors, you are measuring magnitude as well as direction. A "loud" image (high norm) will match everything. Always normalize to unit length.
2.  **Ignoring Temperature:** The temperature $\tau$ is not just a hyperparameter; it controls the sharpness of the attention. If $\tau$ is too high, the model is too "soft" and cannot distinguish between similar concepts. If too low, it becomes brittle.
3.  **Assuming Symmetry:** While the loss is symmetric in calculation, the image and text encoders are different architectures. The geometry is shared, but the paths to get there are not.

## Go deeper

*   **arXiv:2103.00020**: "Learning Transferable Visual Models From Natural Language Supervision" (Radford et al.). This is the original CLIP paper. Read the section on "Contrastive Pre-training" to see the exact loss formulation we used in the lab.

