# CU-102 - Anatomy of a ComfyUI graph

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

Welcome aboard, cadets. I’m Captain Graph. You’ve seen the interface, you’ve dragged the boxes, and you’ve pulled the wires. But when you hit that "Queue Prompt" button, what actually happens? Does the computer just guess? No. It navigates. Today, we are going to look under the deck planks to see how the engine steers your workflow from a static map to a finished image.

## Why this matters

Many of you treat ComfyUI like a black box. You change a seed, you get a new face. You change a model, you get a new style. But if you don’t understand the execution graph, you are flying blind. You cannot optimize your workflow if you don’t know which nodes are being recalculated and which are being skipped. You cannot debug a broken wire if you don’t understand the dependency chain. This lesson teaches you the fundamental logic that allows ComfyUI to be fast, efficient, and deterministic. It is the difference between a sailor who just pushes the boat and a captain who reads the currents.

## The intuition

Think of your workflow as a ship’s rigging. Each node is a pulley. Each wire is a rope. The "Queue" button is the order to hoist the sails.

The computer cannot just run every node at once. Node C needs the output of Node A and Node B. If Node A hasn’t finished, Node C is stuck. We need a strict order. This is called **topological sorting**. Imagine a list of tasks where some tasks must be finished before others can start. We find the tasks with no prerequisites (the source nodes), do them, and then unlock the next layer of tasks.

But here is the real magic: **Caching**. If you change the seed in your KSampler, do you need to reload your model? No. The model file hasn’t changed. The input to the model loader is the same. So, the engine looks at the model loader, sees the inputs are identical to the last run, and says, "I already have this result. I will skip this node." This is how ComfyUI stays fast. It only does the work that is strictly necessary.

## Under the hood (the mechanism; math in plain text, define every symbol)

The core mechanism relies on two concepts: **Topological Sort** and **Dependency-based Caching**.

### 1. Topological Sort
We represent the graph as a set of nodes $N$ and directed edges $E$. An edge $(u, v)$ means node $u$ is an input to node $v$.
We calculate the **in-degree** $d_{in}(v)$ for each node $v$, which is the number of inputs it has.
*   If $d_{in}(v) = 0$, node $v$ is ready to execute immediately.
*   We execute $v$, then for every node $w$ that depends on $v$, we decrement $d_{in}(w)$ by 1.
*   If $d_{in}(w)$ becomes 0, $w$ is added to the ready queue.

This process continues until all nodes are processed. If we cannot process all nodes, there is a cycle (a loop), which is invalid in a standard execution graph.

### 2. Caching and Invalidation
The engine maintains a cache $C$. The key for each node $n$ is derived from its **input signature**.
Let $I(n)$ be the set of input values for node $n$.
*   **Hash**: We compute a hash $H(n) = \text{hash}(I(n))$.
*   **Check**: Before executing $n$, we check if $H(n)$ exists in $C$.
    *   If yes: We retrieve the cached output $O(n)$ and skip execution.
    *   If no: We execute $n$, store the output in $C[H(n)]$, and proceed.

**Invalidation**: When a node $x$ changes (e.g., a new seed), its output changes. This means any node $y$ that depends on $x$ (directly or indirectly) has a new input signature. We must invalidate the cache for $x$ and all its **descendants**.
*   Let $Desc(x)$ be the set of all nodes reachable from $x$ via directed edges.
*   When $x$ changes, we mark all nodes in $Desc(x)$ as "dirty" or requiring recomputation.
*   Nodes not in $Desc(x)$ retain their cached values.

## In ComfyUI

The evidence points to the `comfy_execution` folder as the heart of this process.
*   **`comfy_execution/graph.py`**: Contains `TopologicalSort` and `ExecutionList`. `TopologicalSort` determines the order. `ExecutionList` manages the staging of nodes.
*   **`comfy_execution/caching.py`**: Implements `BasicCache`, `HierarchicalCache`, and `LRUCache`. These classes store node outputs. The keys are derived from the node ID and input signatures.
*   **`comfy_execution/validation.py`**: Contains `validate_loops` and `validate_node_input`. This ensures the graph is acyclic and that data types match between connected nodes.
*   **`comfy_execution/progress.py`**: `ProgressRegistry` tracks which node is currently executing to update the UI.

When you press Queue, `ExecutionList` uses `TopologicalSort` to get the order. It iterates through this list. For each node, it checks the cache. If the cache is valid, it skips. If not, it runs the node's `fn` (function), stores the result, and updates the progress.

## Lab

We ran a small Python script to simulate this exact behavior. We built a graph with 7 nodes: A, B, C, D, E, F, G.
*   A and B are constants.
*   C = A + B
*   D = C * 2
*   E = D + 1
*   F = E * 3
*   G = F + B

We executed the graph fully, then changed the value of B and re-executed, using the previous results as a cache.

Here are the real `RESULT` lines from the lab output:

1.  `RESULT execution_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G']`
    *   **Proves**: The topological sort correctly identified that A and B must run first, followed by C, and so on. The order respects all dependencies.

2.  `RESULT recompute_count_full = 7`
    *   **Proves**: On the first run, with an empty cache, all 7 nodes had to be calculated.

3.  `RESULT G_value = 23`
    *   **Proves**: The math is correct. A=1, B=2 -> C=3, D=6, E=7, F=21, G=21+2=23.

4.  `RESULT recompute_count_changed_B = 6`
    *   **Proves**: This is the key insight. We changed B. The engine did **not** recompute A. It only recomputed B and its descendants (C, D, E, F, G). That is 6 nodes. A was skipped because its inputs didn't change.

5.  `RESULT G_value_after_B_change = 44`
    *   **Proves**: The new value is correct. B is now 5. C=1+5=6, D=12, E=13, F=39, G=39+5=44. The cache correctly propagated the change through the graph.

6.  `RESULT all_asserts_passed = True`
    *   **Proves**: The logic for invalidating only the necessary nodes (descendants of the changed node) works as intended.

## Common mistakes

1.  **Assuming all nodes run every time.** They don’t. If you change a seed, the model loader is skipped. If you change a prompt, the CLIP Text Encode is skipped if the prompt string is identical.
2.  **Creating loops.** ComfyUI will reject the graph if `validate_loops` finds a cycle. You cannot have a node that depends on its own output.
3.  **Ignoring input types.** If you connect a `FLOAT` output to a `STRING` input, `validate_node_input` will fail. The graph will not execute.
4.  **Thinking caching is permanent.** The cache is in memory. If you restart ComfyUI, the cache is cleared. Also, if you change a model file on disk, the hash of the input might change, invalidating the cache.

## Go deeper

The evidence provided does not cite specific arXiv papers for the topological sort or caching algorithms, as these are standard computer science concepts implemented in the `comfy_execution` module. However, the specific implementation details of `TopologicalSort` and `BasicCache` are found in the `comfy_execution/graph.py` and `comfy_execution/caching.py` files, respectively. For a deeper dive into the specific optimization strategies used in ComfyUI’s `HierarchicalCache`, you would need to examine the source code of `comfy_execution/caching.py` directly, as no external papers are referenced in the provided evidence.

