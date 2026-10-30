# CU-403 - Model merging: weighted, SLERP, task arithmetic

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the workshop. In CU-207, we learned how to fine-tune a model to specialize it for a specific task. But here is the honest truth: fine-tuning is expensive, and often, a single fine-tuned model is brittle. It might get better at "cyberpunk portraits" but worse at "realistic landscapes."

In this lesson, we stop treating models as black boxes and start treating them as vectors in a high-dimensional space. We are going to merge them. Why? Because, as the research shows, averaging the weights of multiple fine-tuned models often improves accuracy and robustness without increasing inference time. We call these "model soups." Unlike an ensemble, where you run multiple models and average the outputs (doubling your VRAM and compute), a merged model is a single checkpoint. You pay the cost once, at merge time, and then you just run one model.

This is engineering, not magic. We are manipulating the geometry of weight space. If you do it wrong, you get a model that hallucinates or produces gray noise. If you do it right, you get a model that is smoother, more robust, and capable of handling multiple tasks simultaneously.

## The intuition

Imagine you have a base model, let's call it $W_{base}$. You fine-tune it for Task A, getting $W_A$. You fine-tune the same base for Task B, getting $W_B$.

**Weighted Averaging** is the simplest approach. You just take a weighted average of the weights. If you want a 50/50 mix, you calculate $0.5 \cdot W_A + 0.5 \cdot W_B$. It’s like mixing two paints. Simple, but it assumes the "distance" between weights is linear.

**SLERP (Spherical Linear Interpolation)** is more sophisticated. It assumes that the "best" path between two points in weight space is along the surface of a sphere, not a straight line through the center. This preserves the "magnitude" or norm of the weights better than linear interpolation. Think of it as walking along the surface of a globe rather than digging a tunnel through the earth.

**Task Arithmetic** is the most powerful concept here. Instead of merging the full models, we extract the "task vector." A task vector is the difference between the fine-tuned model and the base model: $V_A = W_A - W_{base}$. This vector points in the direction of "Task A." We can then add these vectors together: $W_{new} = W_{base} + V_A + V_B$. This allows us to combine tasks, or even subtract them (negation) to remove a bias or a style.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let's define our symbols clearly.
*   $W$: A vector of model weights.
*   $\|W\|$: The L2 norm (magnitude) of the vector.
*   $\alpha$: A scalar weight between 0 and 1.

**1. Linear Interpolation (Lerp)**
The formula is:
$$W_{lerp} = \alpha \cdot W_1 + (1 - \alpha) \cdot W_2$$
This is a straight line. The problem? If $W_1$ and $W_2$ are not parallel, the resulting vector $W_{lerp}$ will have a smaller norm than the average of the input norms. It "shrinks" toward the origin. In neural networks, shrinking weights can lead to underfitting or loss of information.

**2. SLERP**
SLERP operates on the directions of the vectors. First, we normalize the vectors to get unit vectors:
$$\hat{W}_1 = W_1 / \|W_1\|$$
$$\hat{W}_2 = W_2 / \|W_2\|$$
We calculate the angle $\theta$ between them using the dot product:
$$\cos(\theta) = \hat{W}_1 \cdot \hat{W}_2$$
$$\theta = \arccos(\cos(\theta))$$
The SLERP formula is:
$$W_{slerp} = \frac{\sin((1-\alpha)\theta) \cdot \hat{W}_1 + \sin(\alpha\theta) \cdot \hat{W}_2}{\sin(\theta)}$$
This result is a unit vector. To make it comparable to the original weights, we scale it by the average norm of the inputs:
$$W_{final} = W_{slerp} \cdot \frac{\|W_1\| + \|W_2\|}{2}$$
This preserves the magnitude of the weights while interpolating the direction.

**3. Task Arithmetic**
We define the task vector $V$ as:
$$V = W_{fine} - W_{base}$$
To merge two tasks, we add their vectors to the base:
$$W_{merged} = W_{base} + \alpha \cdot V_A + \beta \cdot V_B$$
Here, $\alpha$ and $\beta$ are scaling factors. If $\alpha = 0.5$ and $\beta = 0.5$, we are blending the two tasks equally. This is linear in the task vector space, which is often more stable than merging the full weights directly.

## In ComfyUI

Our sources do not cover specific ComfyUI nodes for model merging. The ComfyUI codebase includes utility functions for JSON merging (`merge_json_recursive`) and configuration loading, but these are for data structures, not weight tensors. For actual model merging, you will typically use external tools like `sd-scripts` or custom nodes that implement the math described above. In this course, we focus on the underlying mechanism so you can verify any node's output.

## Lab

In this lab, we simulate a small weight vector to test the geometric properties of these merging strategies. We create a base vector and two fine-tuned versions with small perturbations. We then compute the linear interpolation, SLERP, and task arithmetic results, measuring their norms and cosine similarities to the parents.

Here are the results from our run:

```text
RESULT norm_base = 3.49403
RESULT norm_t1 = 3.61211
RESULT norm_t2 = 3.38031
RESULT norm_lin_interp = 3.49382
RESULT norm_slerp = 3.49621
RESULT norm_task_arith = 3.49382
RESULT cos_lin_t1 = 0.999361
RESULT cos_lin_t2 = 0.99927
RESULT cos_slerp_t1 = 0.999316
RESULT cos_slerp_t2 = 0.999316
RESULT cos_task_t1 = 0.999361
RESULT cos_task_t2 = 0.99927
```

Let's analyze what these numbers prove:

1.  **`RESULT norm_lin_interp = 3.49382`**: The average of the parent norms is $(3.61211 + 3.38031) / 2 = 3.49621$. The linear interpolation norm is slightly lower ($3.49382$). This confirms the "shrinkage" effect. Linear interpolation pulls the vector toward the origin.
2.  **`RESULT norm_slerp = 3.49621`**: This is exactly the average of the parent norms. SLERP, when scaled to the average norm, perfectly preserves the magnitude. This is why SLERP is often preferred for merging models where weight magnitude carries semantic meaning.
3.  **`RESULT norm_task_arith = 3.49382`**: Task arithmetic with $\alpha=0.5, \beta=0.5$ is mathematically equivalent to linear interpolation in this specific setup (since $W_{base} + 0.5(W_1-W_{base}) + 0.5(W_2-W_{base}) = 0.5W_1 + 0.5W_2$). The norm matches the linear interpolation result exactly.
4.  **`RESULT cos_slerp_t1 = 0.999316`**: The cosine similarity is high, indicating the merged vector is very close in direction to the parents. SLERP produces a symmetric result (both cosines are identical), whereas linear interpolation is slightly asymmetric due to the different magnitudes of the parents.

## Common mistakes

1.  **Ignoring Norm Shrinkage**: If you use linear interpolation on models with different weight magnitudes, you will shrink the model. This can lead to washed-out images. Always check the norm of your merged model against the parents.
2.  **Assuming Task Vectors are Additive for All Tasks**: Task arithmetic works best when tasks are related or orthogonal. If you try to add a "cartoon" task vector to a "photorealistic" task vector, you might get a muddy mess. Measure the cosine similarity between task vectors before merging. If they are highly correlated, you are just amplifying one task. If they are orthogonal, you are creating a new hybrid.
3.  **Forgetting to Scale**: When using SLERP, the raw output is a unit vector. If you forget to scale it back to the average norm, your model will have near-zero weights and produce black images.

## Go deeper

*   **arXiv:2203.05482**: "Model soups: averaging weights of multiple fine-tuned models improves accuracy without increasing inference time." This paper establishes the foundation for why simple averaging works and introduces the concept of "model soups."
*   **arXiv:2212.04089**: "Editing Models with Task Arithmetic." This paper formalizes the task vector concept and shows how arithmetic operations on these vectors can steer model behavior, including negation and analogy.

