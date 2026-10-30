# CU-401 lab: the V3 contract, on a tiny stand-in for comfy_api.latest.io, so it runs without ComfyUI. Copy the node class into a real pack and only the import changes.
# Run: python lab.py  (CPU only, a few seconds to import torch).
import torch
from dataclasses import dataclass, field
torch.manual_seed(0); torch.set_num_threads(1)
class io:                                             # the smallest part of comfy_api.latest.io needed to run this node
    @dataclass
    class Input: id: str; type: str; default: object = None; min: float = None; max: float = None; lazy: bool = False; optional: bool = False
    class Latent:
        Input = staticmethod(lambda id, **k: io.Input(id, "LATENT", **k)); Output = staticmethod(lambda **k: ("LATENT", k))
    class Float:
        Input = staticmethod(lambda id, **k: io.Input(id, "FLOAT", **k))
    class Int:
        Input = staticmethod(lambda id, **k: io.Input(id, "INT", **k))
    @dataclass
    class Schema: node_id: str; category: str; inputs: list; outputs: list; display_name: str = ""; description: str = ""; is_output_node: bool = False; not_idempotent: bool = False
    class NodeOutput:
        def __init__(self, *a, ui=None): self.args, self.ui = a, ui
    class ComfyNode:
        @classmethod
        def fingerprint_inputs(cls, **k): return None
        @classmethod
        def validate_inputs(cls, **k): return True
        @classmethod
        def check_lazy_status(cls, **k): return []

# ---------- the node: this is the part that goes in a pack ----------
class LatentContrast(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="LatentContrast", display_name="Latent Contrast", category="latent/adjust", description="Scales a latent around its mean.",
                         inputs=[io.Latent.Input("samples"), io.Float.Input("amount", default=1.0, min=0.0, max=4.0), io.Latent.Input("fallback", optional=True, lazy=True)],
                         outputs=[io.Latent.Output(display_name="samples")])
    @classmethod
    def validate_inputs(cls, amount, **_): return True if amount >= 0 else "amount must not be negative"
    @classmethod
    def check_lazy_status(cls, amount, fallback=None, **_): return ["fallback"] if amount == 0 and fallback is None else []     # ask for the wire only when it is needed
    @classmethod
    def execute(cls, samples, amount, fallback=None) -> io.NodeOutput:
        if amount == 0 and fallback is not None: return io.NodeOutput(fallback)
        s = samples["samples"]; m = s.mean(dim=(-1, -2), keepdim=True)
        return io.NodeOutput({**samples, "samples": m + (s - m) * amount})          # new dict and new tensor: never modify an input in place

# ---------- what the engine does with it, reduced ----------
def to_input_types(schema):                           # V3 schemas become the classic INPUT_TYPES shape on the way to the front-end and validator
    out = {"required": {}, "optional": {}}
    for i in schema.inputs: out["optional" if i.optional else "required"][i.id] = (i.type, {k: getattr(i, k) for k in ("default", "min", "max", "lazy") if getattr(i, k) not in (None, False)})
    return out
print(to_input_types(LatentContrast.define_schema()))
latent = {"samples": torch.randn(1, 4, 8, 8)}; print("input std:", round(latent["samples"].std().item(), 4))
r = LatentContrast.execute(samples=latent, amount=2.0); out = r.args[0]["samples"]
print("output std at amount=2:", round(out.std().item(), 4), " input tensor untouched:", bool((latent["samples"] == latent["samples"].clone()).all()) and out is not latent["samples"])
assert abs(out.std().item() / latent["samples"].std().item() - 2) < .05 and r.args[0] is not latent
print("validate amount=-1:", LatentContrast.validate_inputs(amount=-1), "| amount=1:", LatentContrast.validate_inputs(amount=1))
print("lazy, amount=1:", LatentContrast.check_lazy_status(amount=1), "| amount=0, wire not computed yet:", LatentContrast.check_lazy_status(amount=0), "| amount=0, computed:", LatentContrast.check_lazy_status(amount=0, fallback=latent))
assert LatentContrast.check_lazy_status(amount=1) == [] and LatentContrast.check_lazy_status(amount=0) == ["fallback"]
print("classmethods: called on the class, no instance. Attributes you set on cls are shared by every copy of the node in every run.")
class Bad(io.ComfyNode):
    calls = 0
    @classmethod
    def execute(cls, x): cls.calls += 1; return io.NodeOutput(x + cls.calls)      # hidden state: same inputs, different outputs
print("a node with hidden state, same input twice:", Bad.execute(1).args[0], Bad.execute(1).args[0], " the cache cannot see this, so do not do it")
assert Bad.calls == 2
