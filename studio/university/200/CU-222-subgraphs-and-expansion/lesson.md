# CU-222 - Sub-graphs and node expansion

**Objective.** Tell the two apart: one is a front-end packaging feature, the other lets a node create nodes while the prompt runs. Taught by Captain Graph.

## The idea

**A sub-graph** packages nodes into one reusable node on the canvas. The docs compare it to a folder. **Node expansion** lets a running node return new nodes for the engine to run. They look related and work in different places.

## The mechanism

**Sub-graphs.** A saved workflow keeps definitions in `definitions.subgraphs`, each with a UUID, its own nodes and links, and input and output lists. The blueprints folder of ComfyUI holds real examples. `SubgraphManager` in `app/subgraph_manager.py` serves such files, and that is its job. Inner nodes run under compound execution ids such as `1:2:3`, per the Subgraph Developer Guide.

The sub-graph node itself cannot reach the executor: `validate_prompt` rejects any `class_type` that is not in `NODE_CLASS_MAPPINGS`, and a UUID type is not there. So the front-end must flatten it first. We infer this from those two facts and did not read the front-end source.

**Expansion.** A node returns `{"result": ..., "expand": graph}`. V3 nodes use `io.NodeOutput(..., expand=graph)`, and the schema must flag the node as expandable. In `execute` in `execution.py`:

1. each new node goes into `dynprompt.add_ephemeral_node`, with this node as its parent
2. new output nodes and the links in the result are added to the `ExecutionList`
3. the node stores its pending result in `pending_subgraph_results` and returns PENDING
4. once the new nodes finish, the parent is visited again and resolves the links into values

`GraphBuilder` in `comfy_execution/graph_utils.py` writes such a graph, and prefixes ids with the parent id so that repeated runs stay unique. The name `pending_subgraph_results` is older than the front-end feature, which is a common source of confusion.

## Lab

```text
the server sees 4 nodes and no sub-graph node at all
```

The lab's flatten step turns one instance into its inner nodes with ids `5:2` and `5:3`, and rewires the links crossing the boundary. Then a node that expands:

```text
expansion: result 13  nodes after running: ['a', 'r', 'r.1', 'r.2', 'r.3']  parents: {'r.1': 'r', 'r.2': 'r', 'r.3': 'r'}
functions that ran: ['Const', 'AddOne', 'AddOne', 'AddOne']
the same node with times=50: result 50 , graph grew to 52 nodes
```

A graph has no loops, but a node can decide at run time how many steps to create, so loops can be written this way. The lab is a simplified copy, with recursion in place of the real list.

## Sources

- [ComfyUI docs: Subgraph](https://docs.comfy.org/interface/features/subgraph)
- [ComfyUI docs: Subgraph Developer Guide](https://docs.comfy.org/custom-nodes/js/subgraphs)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
- [ComfyUI v0.43.0, app/subgraph_manager.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/app/subgraph_manager.py)
