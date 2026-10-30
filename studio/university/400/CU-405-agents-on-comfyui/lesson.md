# CU-405 - Agents on ComfyUI: tools, verification, side-effect safety

> Draft. A local model wrote this lesson and it has not been checked line by line against its sources yet. The lab ran and its output is real; treat the explanation with care.

## Why this matters

Welcome back to the bridge, crew. In CU-401, we learned to steer the ship manually. Now, in CU-405, we are installing the autopilot. An "agent" in this context is a program that can look at a goal, decide which nodes to wire up, and execute the graph. But an autopilot that doesn't check its instruments is a liability. If your agent sends a malformed graph to the server, you don't just get an error; you get a broken state, wasted compute, or worse, a side-effect you didn't intend.

This lesson focuses on the **verification layer**. Before any wire is connected or any prompt is queued, we must prove the graph is structurally sound. We will build a verifier that checks for unknown nodes, missing inputs, broken links, and cycles. This is the safety net that allows agents to operate autonomously without sinking the ship.

## The intuition

Think of a ComfyUI graph as a nautical chart. Before you set sail, you check the chart for three things:
1.  **Known Waters:** Are all the landmarks (nodes) on your chart actually real? (Do the `class_type` values exist?)
2.  **Provisioning:** Does every ship (node) have the supplies it needs? (Are all `required_inputs` present?)
3.  **Course Correction:** Does the route make sense? (Do links point to existing nodes, and does the path loop back on itself?)

If you try to sail to a non-existent island (unknown node), you run aground. If you forget the water (missing input), you die of thirst. If you draw a circle on the map that never ends (cycle), you sail forever. Our verifier is the navigator who checks the chart before the engine starts.

## Under the hood (the mechanism; math in plain text, define every symbol)

We model the graph as a directed acyclic graph (DAG) where nodes are vertices and wires are edges. Let $G = (V, E)$ be the graph, where $V$ is the set of node IDs and $E$ is the set of directed edges.

We define a specification set $S$ containing valid node types. For each node type $t \in S$, we define:
*   $R(t)$: The set of required input names for type $t$.
*   $O(t)$: The set of optional input names for type $t$.

A node $n \in V$ has a type $type(n)$ and a set of inputs $I(n)$. An input $i \in I(n)$ is either a literal value or a link. A link is a tuple $(src, idx)$, where $src$ is the ID of the source node and $idx$ is the output index.

The verification function $Verify(G)$ returns a set of problems $P$. $P$ is empty if and only if $G$ is valid. The checks are:

1.  **Type Validity:** For all $n \in V$, $type(n)$ must be in $S$. If not, add "unknown class_type" to $P$.
2.  **Input Completeness:** For all $n \in V$ where $type(n) \in S$, for all $r \in R(type(n))$, $r$ must be in $I(n)$. If not, add "missing required input" to $P$.
3.  **Link Integrity:** For all $n \in V$, for all inputs $i \in I(n)$ that are links $(src, idx)$, $src$ must be in $V$. If not, add "links to non-existent node" to $P$.
4.  **Acyclicity:** The graph must not contain a cycle. We use Depth-First Search (DFS) to detect cycles. If a node is encountered again while it is still on the current recursion stack, a cycle exists. If a cycle is found, add "Graph contains a cycle" to $P$.

This is a static analysis. It does not execute the nodes; it only inspects the structure. This is crucial for safety: we verify before we act.

## In ComfyUI (name real nodes/files/classes ONLY if they appear in the evidence; otherwise say 'not covered in our sources')

In the ComfyUI ecosystem, the logic for making HTTP requests is separated from the data models. The `comfy_api_nodes/apis` folder contains the Python data models and request/response schemas. For example, `comfy_api_nodes/apis/bfl.py` defines `BFLFluxProGenerateRequest`, and `comfy_api_nodes/apis/kling.py` defines `KlingTaskQueryResponse`. These Pydantic models validate the payloads sent to external APIs.

However, the internal execution engine uses the `comfy_api/internal` folder. The `_ComfyNodeInternal` class is the base for all V3-based ComfyNode APIs. The `AsyncToSyncConverter` in `comfy_api/internal/async_to_sync.py` converts asynchronous node definitions into synchronous ones, ensuring the main UI thread is not blocked.

For programmatic interaction, the `script_examples` folder provides templates. The `queue_prompt(prompt, prompt_id)` function sends a prompt to the server. The `get_history(prompt_id)` function fetches the execution history and metadata, which is essential for verifying that the execution state matches our expectations. The `get_image(filename, subfolder, folder_type)` function retrieves the output.

Note: The specific implementation of a "graph verifier" node is not covered in our sources. The verification logic we are building in this lesson is a pre-execution check that an agent would perform before calling `queue_prompt`.

## Lab (explain what the lab does, then quote 3-6 of its real `RESULT` lines exactly as printed and say what each proves)

The lab implements the `verify_graph` function described above. It defines a `NODE_SPECS` dictionary with four node types: `KSampler`, `CheckpointLoader`, `VAEDecode`, and `CLIPTextEncode`. It then tests five graphs:
1.  `valid`: A correct chain of nodes.
2.  `unknown_class`: A node with a type not in `NODE_SPECS`.
3.  `missing_input`: A `KSampler` missing the `steps` input.
4.  `bad_link`: A link pointing to node ID `99`, which does not exist.
5.  `cycle`: Two nodes linking to each other.

The lab prints the results for each graph. Here are the key outputs:

`RESULT valid = VALID`
This proves that a correctly structured graph with all required inputs and valid links passes all checks. The verifier returns an empty problem list.

`RESULT unknown_class = Node 1 has unknown class_type: NonExistentNode`
This proves that the verifier catches nodes that are not defined in the specification. An agent cannot use a node it doesn't know about.

`RESULT missing_input = Node 1 (KSampler) missing required input: steps`
This proves that the verifier enforces input completeness. Even if the node type is known, missing a required parameter like `steps` will block execution.

`RESULT bad_link = Node 1 input model links to non-existent node: 99`
This proves that the verifier checks link integrity. A wire cannot connect to a node that isn't in the graph. This prevents "dangling wires" that would cause runtime errors.

`RESULT cycle = Graph contains a cycle`
This proves that the DFS-based cycle detection works. A graph where Node 1 depends on Node 2, and Node 2 depends on Node 1, is invalid because it can never be executed in a topological order.

## Common mistakes

1.  **Confusing Verification with Execution:** Verification is static. It does not run the model. Do not expect the verifier to tell you if the image will be good; it only tells you if the graph is structurally sound.
2.  **Ignoring Optional Inputs:** The verifier only checks `required_inputs`. If you omit an optional input like `cfg`, the graph is still valid, but the behavior might differ from your intent. Always document your assumptions about optional parameters.
3.  **Assuming Topological Order:** The verifier ensures there are no cycles, but it does not sort the nodes. When you execute the graph, you must still perform a topological sort to determine the execution order. The verifier is a prerequisite for topological sorting, not a replacement for it.
4.  **Hardcoding Node Specs:** In a real agent, `NODE_SPECS` should be dynamic, fetched from the ComfyUI server's API. Hardcoding them means your agent will break when new nodes are added or old ones are removed.

## Go deeper (the papers in the evidence, by arXiv id)

The evidence provided does not contain specific arXiv IDs for papers. The sources are internal ComfyUI code documentation and lab code. For further reading on graph verification in AI pipelines, look into research on "DAG validation for machine learning workflows" or "static analysis for neural network graphs." The principles here are standard graph theory applied to a specific domain.

