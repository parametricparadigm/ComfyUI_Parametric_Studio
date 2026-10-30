# CU-401 - Writing a custom node with the V3 API

**Objective.** Write, register and reason about a V3 node, and avoid the mistakes the engine cannot see. Taught by Captain Graph.

## The idea

A V3 node is a class with classmethods. `define_schema` says what it is, and `execute` does the work. The engine calls them on the class, without making an instance you could keep state on.

## The mechanism

This is read from `comfy_api/latest/_io.py` and real nodes in `comfy_extras/`:

```
class LatentContrast(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="LatentContrast", category="latent/adjust",
            inputs=[io.Latent.Input("samples"), io.Float.Input("amount", default=1.0, min=0.0, max=4.0)],
            outputs=[io.Latent.Output(display_name="samples")])
    @classmethod
    def execute(cls, samples, amount) -> io.NodeOutput:
        ...
        return io.NodeOutput(result)

class MyExtension(ComfyExtension):
    async def get_node_list(self): return [LatentContrast]

async def comfy_entrypoint(): return MyExtension()
```

`nodes.py` looks for `comfy_entrypoint` in a pack's module, and calls `get_node_list`. Optional classmethods connect to the lessons before this one:

| Method | Old name | Role |
|---|---|---|
| `fingerprint_inputs` | `IS_CHANGED` | Extra value in the cache key (CU-221) |
| `validate_inputs` | `VALIDATE_INPUTS` | Return True or an error string, runs at queue time |
| `check_lazy_status` | `check_lazy_status` | Names the lazy inputs now needed (CU-220) |

`io.Schema` also has flags such as `is_output_node` and `not_idempotent`. For the full list, read the class.

## Rules the engine cannot enforce

1. **Do not change your inputs in place.** The cache hands the same object to every node using that output.
2. **Do not hide state.** The cache key cannot see it. A value that matters must be an input or be in the fingerprint.
3. **Do not read a file without a fingerprint.** Otherwise an edit on disk does not rerun the node.

## Lab

The lab has a tiny stand-in for `io`, so it runs without ComfyUI. Copy the node class to a pack, and only the import changes. The stand-in is not the real library, and the real one has many more types.

```text
input std: 0.9407
output std at amount=2: 1.8784  input tensor untouched: True
validate amount=-1: amount must not be negative | amount=1: True
lazy, amount=1: [] | amount=0, wire not computed yet: ['fallback'] | amount=0, computed: []
```

The third line shows `validate_inputs` returning an error string. The last shows lazy status: the node asks for its fallback only when it needs it, and stops asking once it has it.

```text
a node with hidden state, same input twice: 2 3  the cache cannot see this, so do not do it
```

## Sources

- [ComfyUI docs: V3 Migration](https://docs.comfy.org/custom-nodes/v3_migration)
- [ComfyUI v0.43.0, comfy_api/latest/_io.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_api/latest/_io.py)
- [ComfyUI v0.43.0, comfy_extras/nodes_lotus.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/comfy_extras/nodes_lotus.py)
- [ComfyUI v0.43.0, nodes.py](https://github.com/Comfy-Org/ComfyUI/blob/v0.43.0/nodes.py)
