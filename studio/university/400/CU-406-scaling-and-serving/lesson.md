# CU-406 - Scaling: sharding, batching and serving

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the workshop. In CU-305, we learned how to build a single, robust pipeline. But in production, "single" is a bottleneck. If you are serving a public API or processing a dataset of 10,000 images, running them one by one is not just slow; it is wasteful.

Scaling is about two things: **amortization** and **parallelism**. Amortization means doing the expensive setup work once and reusing it for many items. Parallelism means splitting the work across multiple GPUs or processes. Today, we focus on the foundation of both: **batching**. If you cannot batch efficiently on a single device, sharding across multiple devices will just multiply your inefficiency.

We are going to measure the cost of batching. We are not going to guess. We are going to run a cost model, look at the numbers, and understand why your GPU utilization is likely sitting at 40% when it should be at 90%.

## The intuition

Imagine you are a chef in a kitchen. You have a fixed cost to preheat the oven (let's call this `FIXED_OVERHEAD`). You also have a variable cost to bake each cake (let's call this `PER_ITEM_COST`).

If you bake one cake, you pay the full oven preheat cost for just that one item. The oven is hot, but you only used it for a tiny fraction of its capacity.

If you bake 16 cakes at once, you pay the oven preheat cost once, and then you pay the baking cost for 16 cakes. The preheat cost is now spread out over 16 items. The "cost per cake" drops significantly.

In deep learning, the "oven preheat" is the kernel launch overhead, memory synchronization, and the time it takes for the GPU to switch contexts. The "baking" is the actual matrix multiplications (FLOPs).

The intuition is simple: **Throughput increases as batch size increases**, up to the point where you run out of memory. The goal of scaling is to find the largest batch size that fits in your VRAM, because that is where you get the best "cost per item."

## Under the hood (the mechanism; math in plain text, define every symbol)

Let's define the cost model we used in the lab.

We define the total cost to process a batch of size $B$ as:

$$Cost(B) = FIXED\_OVERHEAD + (PER\_ITEM\_COST \times B)$$

Where:
*   $FIXED\_OVERHEAD$ is the constant time cost incurred per batch, regardless of size (e.g., 1.0 unit in our lab).
*   $PER\_ITEM\_COST$ is the variable time cost per item (e.g., 0.1 unit in our lab).
*   $B$ is the batch size (number of items processed in one forward pass).

Throughput is defined as the number of items processed per unit of time:

$$Throughput(B) = \frac{B}{Cost(B)} = \frac{B}{FIXED\_OVERHEAD + (PER\_ITEM\_COST \times B)}$$

If we divide the numerator and denominator by $B$, we get:

$$Throughput(B) = \frac{1}{\frac{FIXED\_OVERHEAD}{B} + PER\_ITEM\_COST}$$

This equation tells us everything. As $B$ increases, the term $\frac{FIXED\_OVERHEAD}{B}$ gets smaller and smaller. It approaches zero. Therefore, the denominator approaches $PER\_ITEM\_COST$, and the throughput approaches $\frac{1}{PER\_ITEM\_COST}$.

This is an asymptotic limit. You never quite reach it, but you get very close. This is why batching is so powerful: it allows you to approach the theoretical maximum speed of your hardware, limited only by the raw compute speed of the FLOPs, not the overhead of launching kernels.

## In ComfyUI (name real nodes/files/classes ONLY if they appear in the evidence; otherwise say 'not covered in our sources')

In ComfyUI, batching is often handled implicitly by the execution engine or explicitly by nodes that accept lists of inputs. However, the specific implementation of dynamic batch sizing or sharding logic is **not covered in our sources**.

The evidence provided focuses on the *management* of jobs rather than the *computation* of batches. For instance, `tests-unit/jobs_cancel_test` shows how ComfyUI handles the lifecycle of jobs, including `interrupt_if_running` and `delete_queue_item`. This is critical for scaling: if you are batching 1000 images and the user cancels the job, the system must correctly identify which items are "running" (and thus need to be interrupted to free VRAM) versus "pending" (and thus can be simply dequeued).

The `FakePromptQueue` class in the tests simulates this state. It ensures that when a batch is cancelled, the VRAM is freed promptly. If your batching strategy is flawed, you might hold onto VRAM for a cancelled job, causing Out-Of-Memory (OOM) errors for subsequent jobs. This is a common failure mode in scaled deployments: the math says you should batch 32, but the cancellation logic fails to release the memory, so the next batch fails.

## Lab (explain what the lab does, then quote 3-6 of its real `RESULT` lines exactly as printed and say what each proves)

The lab simulates a cost model to compare the throughput of different batch sizes. It defines a `FIXED_OVERHEAD` of 1.0 and a `PER_ITEM_COST` of 0.1. It calculates the throughput for batch sizes 1, 4, and 16, and then finds the optimal batch size given a `MEMORY_CAP` of 32.

Here are the results:

```
RESULT throughput_bs_1 = 0.909091
RESULT throughput_bs_4 = 2.85714
RESULT throughput_bs_16 = 6.10501
RESULT optimal_batch_size = 32
RESULT max_throughput = 7.61905
RESULT cost_bs_16 = 2.6
```

*   `RESULT throughput_bs_1 = 0.909091`: This proves that processing items one by one is inefficient. The throughput is less than 1 item per unit time because the fixed overhead (1.0) is almost as large as the item cost (0.1).
*   `RESULT throughput_bs_4 = 2.85714`: This shows a 3x improvement over batch size 1. The fixed overhead is now amortized over 4 items, significantly reducing the per-item cost.
*   `RESULT throughput_bs_16 = 6.10501`: This shows a further 2x improvement over batch size 4. We are getting closer to the asymptotic limit.
*   `RESULT optimal_batch_size = 32`: This confirms that, within our memory cap, the largest possible batch size yields the highest throughput. Since the cost model is linear, there is no "sweet spot" below the cap; the bigger the batch, the better.
*   `RESULT max_throughput = 7.61905`: This is the theoretical maximum throughput for this hardware configuration. Note that it is close to $1 / PER\_ITEM\_COST = 1 / 0.1 = 10$. The gap is due to the remaining fixed overhead.
*   `RESULT cost_bs_16 = 2.6`: This shows the total cost for a batch of 16. It is $1.0 + (0.1 \times 16) = 2.6$. This low total cost for 16 items is why the throughput is high.

## Common mistakes

1.  **Assuming larger batches are always better.** They are better for throughput, but they increase latency. If you are serving real-time requests, a batch size of 32 might take too long to process, causing timeouts. You need to balance throughput (batch size) against latency (time to first token/image).
2.  **Ignoring memory fragmentation.** The lab assumes a simple `MEMORY_CAP`. In reality, PyTorch's memory allocator can fragment VRAM. A batch size that fits in theory might fail in practice due to fragmentation. Always monitor actual VRAM usage, not just theoretical calculations.
3.  **Forgetting to cancel properly.** As seen in the `jobs_cancel_test` evidence, if you don't correctly interrupt running jobs, you leak VRAM. In a scaled environment, this leads to cascading OOM errors. Ensure your cancellation logic distinguishes between "running" and "pending" jobs.
4.  **Not measuring.** Don't guess your optimal batch size. Run a lab like the one above with your actual model and hardware. The `FIXED_OVERHEAD` and `PER_ITEM_COST` vary wildly between models (e.g., SDXL vs. Flux) and hardware (e.g., A100 vs. RTX 4090).

## Go deeper (the papers in the evidence, by arXiv id)

The evidence provided does not contain any arXiv paper IDs. The sources are internal ComfyUI code tests and a custom lab script. For deeper reading on batching and sharding in deep learning, I recommend looking into papers on "Data Parallelism" and "Model Parallelism" in distributed training, as well as "Kernel Launch Overhead" in GPU computing. However, per the instructions, I cannot cite specific papers not present in the evidence.

