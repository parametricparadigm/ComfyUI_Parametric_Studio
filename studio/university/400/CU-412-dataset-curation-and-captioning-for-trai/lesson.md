# CU-412 - Dataset curation and captioning for training

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

In generative AI, the model does not just learn "what a car looks like"; it learns the statistical relationship between a specific text string and a visual concept. If your dataset is biased, your model will be biased. Specifically, if one caption appears far more frequently than others, the model will overfit to that specific phrasing. It will become rigid, failing to generalize to new prompts that describe the same concept differently.

As a workshop tinkerer, I have seen models that can only generate "a red car" but fail completely on "a crimson automobile." This is not a model architecture problem; it is a data curation problem. In this lesson, we move from intuition to measurement. We will build a frequency analysis pipeline to identify these imbalances before they ruin your training run. We will measure the distribution of your captions, normalize them into a probability space, and apply balancing strategies to ensure your model learns concepts, not just specific strings.

## The intuition

Think of your dataset as a library. If you have 100 books titled "The Red Car" and only 1 book titled "The Blue Sky," a librarian (your model) will become an expert on "The Red Car" but will know almost nothing about "The Blue Sky." Worse, they might start associating the *concept* of a car exclusively with the specific title "The Red Car."

Frequency analysis is the act of counting how often each "title" appears. If one title dominates, you have a skewed distribution. To fix this, you can either:
1.  **Downsample:** Remove excess copies of the dominant caption.
2.  **Upsample:** Duplicate the rare captions (risky, can cause artifacts).
3.  **Weight:** Adjust the loss function during training to penalize the dominant caption more heavily.

In this lesson, we focus on the first step: **measurement**. You cannot balance what you have not measured. We will calculate the raw counts, identify the maximum frequency, and normalize these counts into a probability distribution. This normalized distribution tells you exactly how much "weight" each caption carries in your current dataset.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let $C$ be the set of unique captions in your dataset. Let $N$ be the total number of images (samples) in the dataset.

For each caption $c \in C$, we define its raw frequency count as $f(c)$:
$$ f(c) = \sum_{i=1}^{N} \mathbb{I}(caption_i = c) $$
where $\mathbb{I}$ is the indicator function, which equals 1 if the condition is true and 0 otherwise.

The maximum frequency in the dataset is:
$$ f_{max} = \max_{c \in C} f(c) $$

To understand the relative dominance of each caption, we normalize the frequencies to create a probability distribution $P(c)$:
$$ P(c) = \frac{f(c)}{\sum_{k \in C} f(k)} $$

Note that $\sum_{k \in C} f(k) = N$, so:
$$ P(c) = \frac{f(c)}{N} $$

The sum of all probabilities must equal 1:
$$ \sum_{c \in C} P(c) = 1 $$

If $P(c)$ is significantly higher than $1/|C|$ (where $|C|$ is the number of unique captions), that caption is over-represented. In our lab, we will compute $P(c)$ for each caption and verify that the sum is approximately 1. This normalized value is critical because it allows you to compare datasets of different sizes and to calculate the "entropy" of your caption distribution, which is a measure of how "balanced" your data is.

## In ComfyUI

The specific nodes or files for dataset curation and captioning frequency analysis are **not covered in our sources**. The provided evidence focuses on server infrastructure, text encoder architectures (Llama, Qwen, T5, etc.), and the Cosmos video model. While ComfyUI has nodes for loading datasets and training, the specific logic for *frequency analysis* and *balancing* is typically handled in external Python scripts or custom nodes not detailed in the provided codebase. Therefore, we will implement the logic in pure Python/PyTorch as demonstrated in the lab.

## Lab

This lab simulates a small dataset of 5 images with 3 unique captions. It performs the following steps:
1.  Counts the raw frequency of each caption.
2.  Identifies the most frequent caption.
3.  Normalizes the frequencies into a probability distribution.
4.  Generates a balanced sample by selecting unique captions without replacement.

We run the script twice to ensure reproducibility. The output is identical both times.

**Lab Output:**

```
Original counts: {'a red car': 3, 'a blue sky': 1, 'a green tree': 1}
Most frequent caption: a red car with count 3
RESULT norm_freq_a_red_car = 0.6
RESULT norm_freq_a_blue_sky = 0.2
RESULT norm_freq_a_green_tree = 0.2
RESULT balanced_sample = ['a blue sky', 'a red car', 'a green tree']
```

**Analysis of Results:**

1.  `RESULT norm_freq_a_red_car = 0.6`
    This proves that "a red car" accounts for 60% of the dataset's caption weight. This is a severe imbalance. In a balanced dataset with 3 unique captions, each would ideally have a norm_freq of ~0.333. The value 0.6 indicates that the model will be heavily biased toward this specific caption.

2.  `RESULT norm_freq_a_blue_sky = 0.2`
    This proves that "a blue sky" accounts for 20% of the dataset. It is under-represented compared to the dominant caption.

3.  `RESULT norm_freq_a_green_tree = 0.2`
    This proves that "a green tree" also accounts for 20% of the dataset. It shares the same under-representation as "a blue sky."

4.  `RESULT balanced_sample = ['a blue sky', 'a red car', 'a green tree']`
    This proves that a simple balancing strategy (selecting unique captions) can create a sample where each concept is represented exactly once. This sample has a uniform distribution (1/3 each), which is the ideal target for training stability.

## Common mistakes

1.  **Ignoring the "Long Tail":** Many datasets have a few very frequent captions and many rare ones. Focusing only on the top 5 captions misses the fact that the "tail" of rare captions can cause the model to hallucinate or fail on niche prompts. Always analyze the full distribution.
2.  **Balancing by Image Count, Not Caption Frequency:** If you have 100 images of "a red car" but 50 unique captions describing them, and 10 images of "a blue sky" with 10 unique captions, balancing by image count is misleading. You must balance by *caption string* frequency if you want to prevent overfitting to specific text.
3.  **Forgetting to Normalize:** Raw counts are not comparable across datasets of different sizes. Always normalize to a probability distribution ($P(c)$) before comparing or applying weighting schemes.
4.  **Assuming Balancing is Automatic:** ComfyUI does not automatically balance your dataset. If you feed it a skewed dataset, it will train on a skewed distribution. You must curate and balance your data *before* training.

## Go deeper

The provided evidence does not contain specific arXiv paper IDs related to dataset curation or captioning frequency analysis. The papers referenced in the evidence are related to model architectures (Llama, Qwen, T5, Cosmos) and server infrastructure. For further reading on dataset balancing and captioning strategies, I recommend looking into papers on "Data Pruning for Diffusion Models" or "Captioning for Text-to-Image Generation," but these are not included in the current evidence base.

