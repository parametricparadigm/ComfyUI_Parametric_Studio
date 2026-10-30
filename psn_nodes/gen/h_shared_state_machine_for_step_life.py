"""Shared state machine for step lifecycle management (ComfyUI custom node).

Models a small, deterministic state machine for pipeline steps with the
states ``pending -> running -> approved`` (plus ``rejected`` and
``invalidated``).  The node keeps a *shared* machine instance in a module
level registry so that multiple nodes in the same ComfyUI graph can
observe and mutate the same step states, and it automatically invalidates
downstream steps when an upstream step is edited.

Only pure Python + torch (CPU) are used.  No network, no subprocess, no
file I/O.
"""

import torch

CAT = "ParametricStudio/Pipelines"

# ---------------------------------------------------------------------------
# State machine core (plain Python, no tensors)
# ---------------------------------------------------------------------------

STATES = ("pending", "running", "approved", "rejected", "invalidated")

# legal transitions: state -> set of states it may move to
_TRANSITIONS = {
    "pending": {"running", "invalidated"},
    "running": {"approved", "rejected", "invalidated"},
    "approved": {"invalidated"},
    "rejected": {"pending", "invalidated"},
    "invalidated": {"pending"},
}


class StepStateMachine:
    """A shared, in-memory state machine for a set of named steps.

    Steps form a DAG via ``deps`` (each step lists the steps it depends on).
    When a step is *edited* (i.e. re-entered ``pending`` after being
    ``approved``), every transitive downstream step is automatically
    ``invalidated``.
    """

    def __init__(self):
        self._steps = {}   # name -> state
        self._deps = {}    # name -> frozenset(upstream names)
        self._log = []     # list of (step, old, new) tuples

    # -- construction -------------------------------------------------------
    def add_step(self, name, deps=()):
        if name in self._steps:
            raise ValueError("duplicate step: %s" % name)
        for d in deps:
            if d not in self._steps:
                raise ValueError("unknown dependency: %s" % d)
        self._steps[name] = "pending"
        self._deps[name] = frozenset(deps)
        self._log.append((name, None, "pending"))

    # -- queries ------------------------------------------------------------
    def state(self, name):
        if name not in self._steps:
            raise KeyError("unknown step: %s" % name)
        return self._steps[name]

    def all_states(self):
        return dict(self._steps)

    def log(self):
        return list(self._log)

    def downstream(self, name):
        """Return the set of transitive downstream steps of *name*."""
        if name not in self._steps:
            raise KeyError("unknown step: %s" % name)
        result = set()
        stack = [name]
        while stack:
            cur = stack.pop()
            for other, deps in self._deps.items():
                if cur in deps and other not in result:
                    result.add(other)
                    stack.append(other)
        return result

    # -- transitions --------------------------------------------------------
    def _move(self, name, new_state):
        old = self._steps[name]
        if new_state not in _TRANSITIONS.get(old, set()):
            raise ValueError(
                "illegal transition %s -> %s for step %s" % (old, new_state, name)
            )
        self._steps[name] = new_state
        self._log.append((name, old, new_state))

    def start(self, name):
        """pending -> running."""
        self._move(name, "running")

    def approve(self, name):
        """running -> approved."""
        self._move(name, "approved")

    def reject(self, name):
        """running -> rejected."""
        self._move(name, "rejected")

    def retry(self, name):
        """rejected -> pending (owner wants to try again)."""
        self._move(name, "pending")

    def invalidate(self, name):
        """Move *name* to ``invalidated`` (from any state that allows it)."""
        self._move(name, "invalidated")

    def reset(self, name):
        """invalidated -> pending."""
        self._move(name, "pending")

    def edit(self, name):
        """Simulate an owner edit on an approved step.

        The edited step goes back to ``pending`` and every transitive
downstream step is ``invalidated`` (if it is not already).
        Returns the list of downstream steps that were invalidated.
        """
        if self._steps[name] != "approved":
            raise ValueError("can only edit an approved step, got %s" % self._steps[name])
        # approved -> invalidated -> pending for the edited step itself
        self._move(name, "invalidated")
        self._move(name, "pending")
        invalidated = []
        for d in sorted(self.downstream(name)):
            if self._steps[d] != "invalidated":
                self._move(d, "invalidated")
                invalidated.append(d)
        return invalidated


# ---------------------------------------------------------------------------
# Shared registry so multiple nodes in one graph share the same machine
# ---------------------------------------------------------------------------

_REGISTRY = {}


def _get_machine(machine_id):
    if machine_id not in _REGISTRY:
        _REGISTRY[machine_id] = StepStateMachine()
    return _REGISTRY[machine_id]


def _clear_registry():
    _REGISTRY.clear()


# ---------------------------------------------------------------------------
# Tensor helpers (never mutate inputs)
# ---------------------------------------------------------------------------

_STATE_TO_INT = {"pending": 0, "running": 1, "approved": 2, "rejected": 3, "invalidated": 4}
_INT_TO_STATE = {v: k for k, v in _STATE_TO_INT.items()}


def _state_tensor(states):
    """Convert a list of state strings to a [1, N, 1] float tensor in 0..4."""
    vals = torch.tensor([_STATE_TO_INT[s] for s in states], dtype=torch.float32)
    return vals.reshape(1, -1, 1)


def _state_names(tensor):
    """Convert a [1, N, 1] float tensor back to a list of state names."""
    flat = tensor.flatten().tolist()
    return [_INT_TO_STATE[int(round(v))] for v in flat]


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------

class PSN_StepLifecycleMachine:
    """Shared state machine for step lifecycle management.

    Build a small DAG of steps, drive them through
    pending -> running -> approved (or rejected), and observe automatic
downstream invalidation when an approved step is edited.

    The node is *stateless* across calls in the ComfyUI sense: every call
    rebuilds the machine from the ``steps`` / ``deps`` strings, applies the
    requested ``action`` to ``target_step``, and returns the resulting
    state tensor plus a summary string.  A ``machine_id`` lets you keep a
    persistent shared instance in the module-level registry if you want to
    chain multiple nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "machine_id": ("STRING", {"default": "default", "multiline": False}),
                "steps": ("STRING", {"default": "a,b,c", "multiline": False}),
                "deps": ("STRING", {"default": "a:;b:a;c:b", "multiline": False}),
                "action": ("start|approve|reject|retry|edit|invalidate|reset|noop", {"default": "noop"}),
                "target_step": ("STRING", {"default": "a", "multiline": False}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("MASK", "STRING")
    RETURN_NAMES = ("state_map", "summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, machine_id, steps, deps, action, target_step):
        # --- parse step names ---
        step_names = [s.strip() for s in steps.split(",") if s.strip()]
        if not step_names:
            raise ValueError("at least one step name is required")
        if len(set(step_names)) != len(step_names):
            raise ValueError("duplicate step names")

        # --- parse deps: "a:;b:a;c:b" ---
        dep_map = {}
        for part in deps.split(";"):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                name, dep_str = part.split(":", 1)
            else:
                name, dep_str = part, ""
            name = name.strip()
            d_list = [d.strip() for d in dep_str.split(",") if d.strip()]
            dep_map[name] = d_list

        # --- build (or fetch) the shared machine ---
        use_shared = machine_id != ""
        if use_shared:
            machine = _get_machine(machine_id)
            # If the machine already has steps, verify they match; otherwise
            # (re)build.  For simplicity we rebuild when the step set differs.
            existing = set(machine.all_states().keys())
            if existing != set(step_names):
                # fresh build
                machine = StepStateMachine()
                _REGISTRY[machine_id] = machine
        else:
            machine = StepStateMachine()

        if not use_shared or not machine.all_states():
            for s in step_names:
                machine.add_step(s, dep_map.get(s, ()))

        # --- apply action ---
        target = target_step.strip()
        if action == "start":
            machine.start(target)
        elif action == "approve":
            machine.approve(target)
        elif action == "reject":
            machine.reject(target)
        elif action == "retry":
            machine.retry(target)
        elif action == "edit":
            invalidated = machine.edit(target)
        elif action == "invalidate":
            machine.invalidate(target)
        elif action == "reset":
            machine.reset(target)
        elif action == "noop":
            pass
        else:
            raise ValueError("unknown action: %s" % action)

        # --- build outputs ---
        states = [machine.state(s) for s in step_names]
        state_map = _state_tensor(states)  # [1, N, 1] float, MASK-compatible
        summary = " | ".join("%s=%s" % (s, st) for s, st in zip(step_names, states))
        if action == "edit":
            summary += " | invalidated: " + (", ".join(invalidated) if invalidated else "none")

        return (state_map, summary)


# ---------------------------------------------------------------------------
# Node mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_StepLifecycleMachine": PSN_StepLifecycleMachine,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_StepLifecycleMachine": "Step Lifecycle State Machine",
}
