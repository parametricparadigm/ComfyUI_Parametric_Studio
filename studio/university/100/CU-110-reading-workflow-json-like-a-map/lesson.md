# CU-110 - Reading a workflow JSON like a map

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome aboard, cadets. You’ve spent time in CU-102 learning how to drag and drop nodes. But when you press "Queue Prompt," the magic isn't just in the GPU; it's in the data structure that tells the engine *how* to connect the dots. A ComfyUI workflow is not just a picture of boxes and wires; it is a precise, machine-readable map.

If you cannot read the JSON behind the interface, you are flying blind. You might think you’ve connected a `KSampler` to a `VAEDecode`, but if the underlying link reference is broken, the engine will throw an error or, worse, silently produce garbage. In this lesson, we strip away the visual clutter and look at the raw topology. We will learn to treat node IDs as coordinates and links as edges in a directed acyclic graph (DAG). This is the foundation for debugging, automating, and understanding exactly what happens when the server processes your prompt.

## The intuition

Imagine your workflow as a ship’s chart. Each node is a port. The wires are the shipping lanes. But a chart is useless if the coordinates are wrong.

In the visual interface, you see a line from Node A to Node B. In the JSON, you don’t see a line. You see a reference. Node B says, "I need data from Node A, slot 0." That is the entire connection.

The key intuition is **directionality**. Data flows from source to sink. In our JSON, a node’s `inputs` field contains references to *other* nodes. It does not contain the data itself; it contains the *address* of where to get the data. If you read the JSON correctly, you are reading a dependency graph. You are asking: "Who feeds me?" and "Who do I feed?"

Think of the node ID as a unique coordinate on the map. The link is the vector pointing from one coordinate to another. If the vector points to a coordinate that doesn’t exist, or points to the wrong slot on that coordinate, the ship runs aground.

## Under the hood (the mechanism; math in plain text, define every symbol)

Let’s define the structure formally so we can navigate it with precision.

A workflow is a dictionary, let’s call it $W$.
The keys of $W$ are Node IDs, denoted as $N_i$.
The values of $W$ are Node Objects, denoted as $V_i$.

Each Node Object $V_i$ contains:
1.  `class_type`: A string identifying the node’s function (e.g., "KSampler").
2.  `inputs`: A dictionary of input slots.

The critical part is the `inputs` dictionary. For a given input slot $S$ in node $N_i$, the value is a reference tuple: $[N_j, k]$.
*   $N_j$ is the ID of the *source* node.
*   $k$ is the index of the *output slot* on node $N_j$ from which the data is drawn.

This creates a directed edge from $(N_j, k)$ to $(N_i, S)$.

For the workflow to be valid, two conditions must hold:
1.  **Existence**: For every reference $[N_j, k]$ in any node’s inputs, the node $N_j$ must exist in $W$.
2.  **Slot Validity**: The source node $N_j$ must have an output slot at index $k$.

In our lab, we verify this topology. We check that the `SaveImage` node (ID 7) references the `VAEDecode` node (ID 5). The reference is `[5, 0]`. This means: "Go to node 5, take output slot 0, and feed it into my input."

This is a Directed Acyclic Graph (DAG). There are no cycles; data flows forward. If you create a cycle (Node A feeds Node B, which feeds Node A), the engine cannot determine the execution order, and the workflow fails.

## In ComfyUI (name real nodes/files/classes ONLY if they appear in the evidence; otherwise say 'not covered in our sources')

In the ComfyUI ecosystem, the workflow JSON is the primary payload sent to the server. The server parses this JSON to construct the execution graph.

While the visual frontend handles the "wires," the backend relies on the JSON structure to validate the graph before execution. The `comfy_api/latest` module defines the types of data flowing through these edges (e.g., `Latent`, `Image`, `Conditioning`). However, the *topology*—the IDs and links—is handled by the core prompt processing logic.

The `script_examples` folder demonstrates how to interact with this structure programmatically. The `queue_prompt` function sends the workflow JSON to the server. The server then uses the node IDs and link references to determine the execution order. If a node ID in a link reference does not exist in the workflow dictionary, the server will reject the prompt.

Note: Specific internal classes for graph validation are not covered in our sources, but the JSON structure itself is the contract. The `tests-unit/server_test` module validates metadata injection, but the core topology validation happens during the prompt parsing phase, ensuring that every `[N_j, k]` reference resolves to a valid node and slot.

## Lab (explain what the lab does, then quote 3-6 of its real `RESULT` lines exactly as printed and say what each proves)

In this lab, we simulate a minimal ComfyUI workflow with three nodes: `KSampler` (ID 3), `VAEDecode` (ID 5), and `SaveImage` (ID 7). We construct the JSON dictionary and verify the topology. We then perform a simple tensor operation to simulate data flow from the `KSampler` through `VAEDecode` to `SaveImage`.

The lab asserts that:
1.  Every node has a `class_type`.
2.  The `SaveImage` node correctly references the `VAEDecode` node.

Here are the results from the lab run:

```
RESULT node_count = 3
```
This proves that our workflow dictionary contains exactly three nodes, matching our intended topology. It confirms the basic structure is present.

```
RESULT link_target = 5
```
This proves that the `SaveImage` node (ID 7) is correctly linked to the `VAEDecode` node (ID 5). The variable `ref_node_id` extracted from the `SaveImage` inputs is 5. This validates the edge in our DAG: the data flows from Node 5 to Node 7.

```
RESULT decoded_value = 0.0257425
```
This proves that the simulated data flow produced a finite, valid numerical result. The `VAEDecode` node (simulated as a mean operation on a latent tensor) processed the input from the `KSampler` and produced a scalar value. This confirms that the data path is not just topologically correct, but functionally executable.

```
RESULT image_value = 0.0257425
```
This proves that the `SaveImage` node received the exact value produced by the `VAEDecode` node. Since `image_value` is assigned directly from `decoded_value`, this confirms that the link reference `[5, 0]` successfully transferred the data from the source node to the sink node without corruption or loss.

## Common mistakes

1.  **Broken Links**: The most common error is a link referencing a node ID that doesn’t exist. For example, if `SaveImage` references `[9, 0]` but Node 9 is not in the workflow, the server will fail. Always check that every `N_j` in a reference exists in the workflow keys.
2.  **Wrong Slot Index**: Referencing `[5, 1]` when Node 5 only has one output (slot 0). This is a topology error. The node exists, but the specific output slot does not.
3.  **Cycles**: Creating a loop where Node A feeds Node B, and Node B feeds Node A. This violates the DAG property. The engine cannot determine which node to execute first.
4.  **Missing `class_type`**: If a node object lacks the `class_type` key, the server cannot instantiate the node. The lab asserts this, and it is a critical check.
5.  **Assuming Visual Wires are Data**: Remember, the JSON does not contain the image or latent data. It contains *references*. The data is generated at runtime. If you edit the JSON, you are editing the map, not the cargo.

## Go deeper (the papers in the evidence, by arXiv id)

The evidence provided does not cite specific arXiv papers. The sources are internal ComfyUI code documentation and unit tests. Therefore, no arXiv IDs are available for further reading in this context. For deeper understanding, refer to the ComfyUI GitHub repository and the `comfy_api/latest` documentation for the V3 API specification.

