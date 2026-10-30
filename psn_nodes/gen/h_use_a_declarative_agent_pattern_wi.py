"""Declarative agent pattern with strict output schemas for specialized pipeline stages.

This module implements a lightweight, declarative agent system for ComfyUI.
Each agent is defined by an identity (name, role, description) and a strict
output schema (required keys with expected types).  A pipeline is a list of
agents; execution walks the handoff chain, validates each stage's output
against its schema, and passes validated payloads to the next stage.

The ComfyUI node exposes the pipeline as a string (one agent per line) and
returns the final validated payload plus a per-stage trace.
"""

import torch

CAT = "ParametricStudio/Agents"

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

# Allowed primitive type tags used in schemas.
_TYPE_TAGS = ("int", "float", "str", "bool", "list", "dict", "tensor")


def _type_ok(value, tag):
    """Return True if *value* matches the primitive type tag *tag*."""
    if tag == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if tag == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if tag == "str":
        return isinstance(value, str)
    if tag == "bool":
        return isinstance(value, bool)
    if tag == "list":
        return isinstance(value, (list, tuple))
    if tag == "dict":
        return isinstance(value, dict)
    if tag == "tensor":
        return isinstance(value, torch.Tensor)
    return False


def validate_payload(payload, schema):
    """Validate *payload* (dict) against *schema* (dict of key -> type tag).

    Returns (ok, errors) where errors is a list of human-readable strings.
    """
    errors = []
    if not isinstance(payload, dict):
        return False, ["payload is not a dict"]
    for key, tag in schema.items():
        if key not in payload:
            errors.append("missing key: %s" % key)
            continue
        if not _type_ok(payload[key], tag):
            errors.append("key %s: expected %s, got %s" % (key, tag, type(payload[key]).__name__))
    return (len(errors) == 0), errors


# ---------------------------------------------------------------------------
# Declarative Agent
# ---------------------------------------------------------------------------

class Agent:
    """Declarative agent identity + strict output schema.

    Attributes
    ----------
    name : str
        Unique agent identifier.
    role : str
        Short role description (e.g. "upscaler", "style_transfer").
    description : str
        Longer human-readable description.
    output_schema : dict
        Mapping of required output key -> type tag string.
    handoff : str or None
        Name of the next agent in the pipeline (None = terminal).
    """

    def __init__(self, name, role, description, output_schema, handoff=None):
        if not isinstance(name, str) or not name:
            raise ValueError("agent name must be a non-empty string")
        if not isinstance(output_schema, dict):
            raise ValueError("output_schema must be a dict")
        for k, v in output_schema.items():
            if v not in _TYPE_TAGS:
                raise ValueError("unknown type tag %r for key %r" % (v, k))
        self.name = name
        self.role = role
        self.description = description
        self.output_schema = dict(output_schema)
        self.handoff = handoff

    def validate(self, payload):
        """Validate a payload against this agent's output schema."""
        return validate_payload(payload, self.output_schema)


# ---------------------------------------------------------------------------
# Pipeline execution (run_spec)
# ---------------------------------------------------------------------------

def run_spec(agents, initial_payload, max_steps=32):
    """Execute a declarative agent pipeline.

    Parameters
    ----------
    agents : list[Agent]
        Ordered list of agents.  The first agent receives *initial_payload*.
    initial_payload : dict
        Input to the first agent.
    max_steps : int
        Safety bound on pipeline length.

    Returns
    -------
    (final_payload, trace)
        final_payload : dict – validated output of the last agent.
        trace : list[dict] – one entry per stage with keys
            ``agent``, ``ok``, ``errors``, ``payload``.
    """
    if not agents:
        raise ValueError("pipeline must contain at least one agent")
    if len(agents) > max_steps:
        raise ValueError("pipeline too long (%d > %d)" % (len(agents), max_steps))

    # Build name -> agent lookup for handoff resolution.
    by_name = {a.name: a for a in agents}

    current = agents[0]
    payload = dict(initial_payload)  # never mutate the caller's dict
    trace = []

    for _ in range(max_steps):
        ok, errors = current.validate(payload)
        entry = {"agent": current.name, "ok": ok, "errors": errors, "payload": dict(payload)}
        trace.append(entry)
        if not ok:
            return payload, trace
        # Follow handoff.
        nxt = current.handoff
        if nxt is None:
            return payload, trace
        if nxt not in by_name:
            raise ValueError("handoff target %r not found in pipeline" % nxt)
        current = by_name[nxt]

    raise ValueError("pipeline did not terminate within max_steps")


# ---------------------------------------------------------------------------
# Pipeline parser (string -> list[Agent])
# ---------------------------------------------------------------------------

def parse_pipeline(text):
    """Parse a simple line-based pipeline definition.

    Format (one agent per line, fields separated by ``|``):

        name | role | description | key:type,key:type | handoff_name

    The last field may be omitted (terminal agent).
    Type tags: int, float, str, bool, list, dict, tensor.
    """
    agents = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            raise ValueError("bad agent line (need >= 4 fields): %r" % line)
        name, role, description, schema_field = parts[0], parts[1], parts[2], parts[3]
        handoff = parts[4] if len(parts) > 4 and parts[4] else None
        schema = {}
        for kv in schema_field.split(","):
            kv = kv.strip()
            if not kv:
                continue
            if ":" not in kv:
                raise ValueError("bad schema entry %r (need key:type)" % kv)
            k, t = kv.split(":", 1)
            k, t = k.strip(), t.strip()
            if t not in _TYPE_TAGS:
                raise ValueError("unknown type tag %r" % t)
            schema[k] = t
        agents.append(Agent(name, role, description, schema, handoff))
    if not agents:
        raise ValueError("pipeline definition is empty")
    return agents


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

def _s(x):
    """Extract the samples tensor from a LATENT dict."""
    if isinstance(x, dict) and "samples" in x:
        return x["samples"]
    raise TypeError("expected LATENT dict with 'samples'")


def _out(latent, samples):
    """Wrap samples back into a LATENT dict (new dict, never mutate input)."""
    return {"samples": samples}


class PSN_DeclarativeAgentPipeline:
    """Run a declarative agent pipeline with strict output schemas.

    The pipeline is defined as a multi-line string.  Each line declares one
    agent: ``name | role | description | key:type,key:type | handoff``.

    The node takes a LATENT (used as the initial payload's ``image`` tensor),
    runs the pipeline, and returns the final LATENT plus a trace string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "pipeline": ("STRING", {
                    "multiline": True,
                    "default": (
                        "upscaler | upscaling | doubles resolution | "
                        "image:tensor,log:str | style_transfer\n"
                        "style_transfer | style | applies style | "
                        "image:tensor,style:str |"
                    ),
                }),
            },
            "optional": {
                "style": ("STRING", {"default": "none"}),
            },
        }

    RETURN_TYPES = ("LATENT", "STRING")
    RETURN_NAMES = ("latent", "trace")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, latent, pipeline, style="none"):
        agents = parse_pipeline(pipeline)
        samples = _s(latent)
        # Build initial payload: the image tensor plus a style tag.
        initial = {"image": samples, "style": style, "log": ""}
        final_payload, trace = run_spec(agents, initial)

        # The final payload's 'image' tensor becomes the output latent.
        out_samples = final_payload.get("image", samples)
        if not isinstance(out_samples, torch.Tensor):
            out_samples = samples

        # Build a human-readable trace string.
        lines = []
        for i, entry in enumerate(trace):
            status = "OK" if entry["ok"] else "FAIL"
            lines.append("[%d] %s (%s): %s" % (i, entry["agent"], entry["agent"], status))
            for err in entry["errors"]:
                lines.append("    error: %s" % err)
        trace_str = "\n".join(lines)

        return (_out(latent, out_samples), trace_str)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_DeclarativeAgentPipeline": PSN_DeclarativeAgentPipeline,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_DeclarativeAgentPipeline": "Declarative Agent Pipeline",
}
