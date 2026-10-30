"""ParametricStudio - Modular Pipeline Subgraphs.

Wraps groups of pipeline stages into reusable, named subgraph blocks with
typed ports, so a complex video/image workflow can be collapsed into a
single node on the canvas while keeping per-stage testing possible.

Implemented core (torch / stdlib only):
  * PSN_SubgraphPort   - typed entry/exit point; validates data types and
                         passes values through unchanged (no in-place edits).
  * PSN_SubgraphWrapper - defines a subgraph boundary: registers named
                         input/output ports, routes values through a
                         registered pure-Python stage function, aggregates
                         outputs and reports execution status.

NOT implemented (needs the real ComfyUI execution engine / pydantic):
  * Actual interception of internal ComfyUI nodes (KSampler etc.) - the
    wrapper runs user-registered pure functions instead of a nested graph.
  * "Use Everywhere" auto-linking for MODEL/CLIP/VAE.
  * pydantic schema validation of input/output maps (lightweight manual
    validation is used instead).
"""

import torch

CAT = "ParametricStudio/Subgraphs"

# Canonical ComfyUI tensor types we know how to validate.
_TENSOR_TYPES = {
    "IMAGE": (4, "[B,H,W,C]"),   # float tensor, values in 0..1
    "MASK": (3, "[B,H,W]"),      # float tensor
    "LATENT": (4, "[B,C,H,W]"),  # dict {"samples": tensor}

}


def _is_image(x):
    return (
        isinstance(x, torch.Tensor)
        and x.dim() == 4
        and x.is_floating_point()
        and bool(((x >= 0.0) & (x <= 1.0)).all())
    )


def _is_mask(x):
    return isinstance(x, torch.Tensor) and x.dim() == 3 and x.is_floating_point()


def _is_latent(x):
    return (
        isinstance(x, dict)
        and "samples" in x
        and isinstance(x["samples"], torch.Tensor)
        and x["samples"].dim() == 4
    )


_VALIDATORS = {
    "IMAGE": _is_image,
    "MASK": _is_mask,
    "LATENT": _is_latent,
    "MODEL": lambda x: x is not None,
    "CLIP": lambda x: x is not None,
    "VAE": lambda x: x is not None,
    "STRING": lambda x: isinstance(x, str),
    "INT": lambda x: isinstance(x, int) and not isinstance(x, bool),
    "FLOAT": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    "DYNAMIC": lambda x: True,
}


def _validate(data_type, value):
    """Return (ok, message)."""
    fn = _VALIDATORS.get(data_type)
    if fn is None:
        return False, "unknown data type: %r" % (data_type,)
    if not fn(value):
        return False, "value does not match type %s" % (data_type,)
    return True, ""


def _clone(value):
    """Deep-copy tensor-bearing values so inputs are never mutated."""
    if isinstance(value, torch.Tensor):
        return value.clone()
    if isinstance(value, dict):
        return {k: _clone(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clone(v) for v in value]
    return value


class PSN_SubgraphPort:
    """Typed entry/exit point for a subgraph.

    Validates that the incoming value matches the declared data type and
    passes a copy through, guaranteeing type safety between the parent
    graph and the subgraph.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "port_name": ("STRING", {"default": "in_0"}),
                "data_type": (
                    sorted(_VALIDATORS.keys()),
                    {"default": "DYNAMIC"},
                ),
                "value": ("DYNAMIC",),
            }
        }

    RETURN_TYPES = ("DYNAMIC", "STRING")
    RETURN_NAMES = ("port_value", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, port_name, data_type, value):
        if not isinstance(port_name, str) or not port_name.strip():
            return (_clone(value), "error: port_name must be a non-empty string")
        ok, msg = _validate(data_type, value)
        if not ok:
            return (_clone(value), "error: %s" % msg)
        return (_clone(value), "ok")


class PSN_SubgraphWrapper:
    """Boundary around a set of pipeline stages.

    `input_map`  : {external_name: (internal_name, data_type)}
    `output_map` : {external_name: (internal_name, data_type)}

    A pure-Python stage function can be registered per subgraph_id via
    `register_stage(subgraph_id, fn)`. The stage receives a dict of
    validated inputs and returns a dict of outputs; the wrapper validates
    every output against the declared types and reports a status string.
    """

    _stages = {}

    @classmethod
    def register_stage(cls, subgraph_id, fn):
        """Register the internal stage function for a subgraph id."""
        if not callable(fn):
            raise TypeError("stage must be callable")
        cls._stages[subgraph_id] = fn

    @classmethod
    def clear_stages(cls):
        cls._stages.clear()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "subgraph_id": ("STRING", {"default": "sg_0"}),
                "input_map": ("DICT", {"default": {}}),
                "output_map": ("DICT", {"default": {}}),
                "inputs": ("DYNAMIC",),
            }
        }

    RETURN_TYPES = ("DYNAMIC", "STRING")
    RETURN_NAMES = ("subgraph_handle", "status")
    FUNCTION = "run"
    CATEGORY = CAT

    @staticmethod
    def _parse_map(raw, kind):
        """Accept {name: (internal, type)} or {name: type} or {name: internal}."""
        if not isinstance(raw, dict):
            raise ValueError("%s map must be a dict" % kind)
        parsed = {}
        for name, spec in raw.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("%s map keys must be non-empty strings" % kind)
            if isinstance(spec, str):
                parsed[name] = (name, spec)
            elif isinstance(spec, (list, tuple)) and len(spec) == 2:
                internal, dtype = spec
                if not isinstance(internal, str) or not isinstance(dtype, str):
                    raise ValueError("%s map values must be (name, type) pairs" % kind)
                parsed[name] = (internal, dtype)
            else:
                raise ValueError("%s map values must be a type string or (name, type)" % kind)
        return parsed

    def run(self, subgraph_id, input_map, output_map, inputs):
        if not isinstance(subgraph_id, str) or not subgraph_id.strip():
            return ({}, "error: subgraph_id must be a non-empty string")
        try:
            in_spec = self._parse_map(input_map, "input")
            out_spec = self._parse_map(output_map, "output")
        except ValueError as exc:
            return ({}, "error: %s" % exc)

        if not isinstance(inputs, dict):
            return ({}, "error: inputs must be a dict")

        # Validate and route inputs.
        routed = {}
        for ext, (internal, dtype) in in_spec.items():
            if ext not in inputs:
                return ({}, "error: missing input %r" % ext)
            ok, msg = _validate(dtype, inputs[ext])
            if not ok:
                return ({}, "error: input %r: %s" % (ext, msg))
            routed[internal] = _clone(inputs[ext])

        fn = self._stages.get(subgraph_id)
        def _wrap(v, dtype):
            if dtype == "LATENT" and not isinstance(v, dict):
                return {"samples": v}
            return v

        if fn is None:
            # No stage registered: pass routed inputs straight through to
            # outputs that share a name, so the wrapper is still useful as
            # a pure routing block.
            def fn(routed_inputs):
                return dict(routed_inputs)

        try:
            raw_out = fn(routed)
        except Exception as exc:  # noqa: BLE001 - report, don't crash canvas
            return ({}, "error: stage raised %s: %s" % (type(exc).__name__, exc))

        if not isinstance(raw_out, dict):
            return ({}, "error: stage must return a dict")

        handle = {}
        for ext, (internal, dtype) in out_spec.items():
            if internal not in raw_out:
                return ({}, "error: stage did not produce output %r" % internal)
            ok, msg = _validate(dtype, _wrap(raw_out[internal], dtype))
            if not ok:
                return ({}, "error: output %r: %s" % (ext, msg))
            handle[ext] = _clone(_wrap(raw_out[internal], dtype))

        return (handle, "ok")


NODE_CLASS_MAPPINGS = {
    "PSN_SubgraphPort": PSN_SubgraphPort,
    "PSN_SubgraphWrapper": PSN_SubgraphWrapper,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SubgraphPort": "Subgraph Port",
    "PSN_SubgraphWrapper": "Subgraph Wrapper",
}
