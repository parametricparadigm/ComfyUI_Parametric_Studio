# CU-223 - App Mode: a graph with a form on top

**Objective.** Explain what App Mode does and does not change, and design a good set of inputs for one. Taught by Captain Graph.

## The idea

A finished workflow may have dozens of settings, and its user may need three. App Mode shows chosen inputs and outputs as a simple interface. The graph stays as it was.

## What the docs say

The official guide describes it as a way to define custom input and output interfaces, so workflows are easier to share and use without editing nodes. It is officially supported from front-end version 1.41.13. The builder has four steps: select inputs, select outputs, preview, and set the default view. Enter it from the top-left menu or from the breadcrumb.

## The mechanism, as a model

The docs do not describe the internals, and we did not read the front-end source, so what follows is a model of what any such form must do, not a description of its code:

1. A field names a node and an input, and holds a value, never a wire.
2. Filling in the form changes those values and nothing else.
3. The result is an ordinary prompt, so it should meet the same validation and the same cache as any other. This step is our inference.

## Lab

```text
the graph has 7 nodes and 13 widget values; the app shows 3 of them
values changed by the form: [('3', 'seed'), ('5', 'width'), ('6', 'text')]
wires changed by the form: 0
```

The default graph has 13 settings, and this app exposes 3. The lab confirms the form cannot alter the structure of the graph.

```text
width=768 valid: True   width=4 valid: False
```

A form does not remove the rules. If a field can take a value the node rejects, the user sees a validation error they may not understand. So choose fields with sensible ranges.

## Designing a good one

These are our recommendations, not rules from the docs:

- Expose what the user decides: the subject, the seed, the size. Hide what the author decided: sampler, schedule, model.
- Remember caching (CU-221): a field near the end of the graph reruns less than one near the start.
- If a setting only makes sense with another, expose neither until you have tested both together.

## Sources

- [ComfyUI docs: ComfyUI APP mode guide](https://docs.comfy.org/interface/app-mode)
- [ComfyUI v0.43.0, execution.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/execution.py)
