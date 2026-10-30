# CU-220 - The execution model: what runs, and in what order

**Objective.** Predict which nodes run and in what order, and read a validation error by its type. Taught by Captain Graph.

## The idea

A graph is not run from left to right. ComfyUI starts at the output nodes and works backwards through the links, so a node nothing depends on is never run. Data flows forward, but the demand for data flows backward.

## The mechanism

These steps are read from `execution.py` and `comfy_execution/graph.py` at v0.43.0.

1. **Validate.** `validate_prompt` checks every `class_type` is known and collects the nodes marked as outputs. No outputs means `prompt_no_outputs`. It then walks back from each output and checks required inputs, link types, value ranges and cycles.
2. **Partial success is allowed.** An output whose ancestors are invalid is dropped, and the rest still runs. The prompt only fails if no output survives.
3. **Build the list.** `ExecutionList` extends `TopologicalSort`. Each pending node has a count of the nodes still blocking it.
4. **Dissolve.** Take a node with count 0, run it, and subtract 1 from everything it blocks.
5. **Pick kindly.** `ux_friendly_pick_node` prefers an output or an async node, then something feeding an output directly, then one link away, so previews appear early. The comment there says this does not change total time.

**Lazy inputs** change the shape of this. A lazy input creates no link at first. The node is staged, `check_lazy_status` returns the names it now needs, `make_input_strong_link` adds those as blockers, and the node goes back in the list (`ExecutionResult.PENDING`). So a node may be visited twice, and a branch nobody asks for never runs.

## Lab

A small copy of the scheduler, in plain Python.

```text
order: ['1', '2', '3', '4']  ran: ['Load', 'Text<a fox>', 'Sample', 'Save']
```

Node 9 exists in the graph and did not run, because it feeds nothing. The validation errors have the same names the server uses:

```text
no output node: prompt_no_outputs
wrong type on a link: return_type_mismatch: node 4 input latent wants LATENT, got COND
cycle: dependency_cycle: 4 -> 1 -> 2 -> 1
unknown class: missing_node_type: Nope
```

Now a switch with two expensive branches:

```text
lazy switch, use_a=True  order: ['7?', '1', '2', '3', '7', '8']
lazy switch, use_a=False order: ['7?', '1', '5', '6', '7', '8']
the same graph without lazy inputs: ['1', '2', '3', '5', '6', '7', '8'] (2 sampler runs)
```

`7?` marks the first visit, where the switch asks for its branch and goes back into the list. Lazy inputs save one full sampler run here.

The lab leaves out caching (CU-221), async nodes and `ExecutionBlocker`, which silently or loudly stops whatever depends on it. Its docstring recommends lazy inputs where they can do the job.

## Sources

- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
- [ComfyUI v0.43.0, comfy_execution/graph.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph.py)
- [ComfyUI v0.43.0, comfy_execution/graph_utils.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_execution/graph_utils.py)
