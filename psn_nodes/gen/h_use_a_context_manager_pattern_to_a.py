"""ParametricStudio: sidecar-aware generation node.

Implements the *context manager* pattern for external sidecar services
(audio synthesis, model loaders, ...): a small registry of named sidecars
plus a ``Sidecar`` context manager that guarantees a sidecar is "up" for
the duration of a dependent task and is torn down afterwards (unless the
sidecar is shared/persistent).

The ComfyUI node itself is a pure-torch *dependent task*: it takes an
IMAGE tensor, a sidecar name and a prompt, runs the task inside the
``Sidecar`` context, and returns the processed image plus a small
``SIDECAR_REPORT`` dict describing what the context manager did
(started / already running / stopped, task duration, etc.).

No network, no subprocesses: the sidecar lifecycle is simulated with
plain Python state so the pattern can be exercised and unit-tested on
CPU with tiny tensors.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

import torch

CAT = "ParametricStudio/Sidecar"

# ---------------------------------------------------------------------------
# Sidecar registry (simulated external services)
# ---------------------------------------------------------------------------


@dataclass
class SidecarSpec:
    """Static description of a sidecar service."""

    name: str
    port: int
    startup_cost: float = 0.05  # simulated seconds to boot
    persistent: bool = False    # if True, never auto-stopped on exit


@dataclass
class SidecarState:
    """Runtime state of one sidecar instance."""

    spec: SidecarSpec
    running: bool = False
    started_at: Optional[float] = None
    stop_count: int = 0
    start_count: int = 0


class SidecarRegistry:
    """Process-wide registry of known sidecars and their live state."""

    def __init__(self) -> None:
        self._specs: Dict[str, SidecarSpec] = {}
        self._states: Dict[str, SidecarState] = {}

    # -- registration ------------------------------------------------------
    def register(self, name: str, port: int, startup_cost: float = 0.05,
                 persistent: bool = False) -> SidecarSpec:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("sidecar name must be a non-empty string")
        if not isinstance(port, int) or not (0 < port < 65536):
            raise ValueError(f"invalid port for sidecar {name!r}: {port!r}")
        if startup_cost < 0:
            raise ValueError(f"startup_cost must be >= 0 for {name!r}")
        spec = SidecarSpec(name=name, port=port, startup_cost=startup_cost,
                           persistent=persistent)
        self._specs[name] = spec
        self._states[name] = SidecarState(spec=spec)
        return spec

    def known(self) -> List[str]:
        return sorted(self._specs)

    def state(self, name: str) -> SidecarState:
        if name not in self._states:
            raise KeyError(f"unknown sidecar: {name!r}")
        return self._states[name]

    def reset(self) -> None:
        """Stop everything and clear state (used by tests)."""
        for st in self._states.values():
            if st.running:
                st.running = False
                st.started_at = None
                st.stop_count += 1
        self._states.clear()
        self._specs.clear()


# The module-level registry: the studio's default sidecars.
REGISTRY = SidecarRegistry()
REGISTRY.register("foley", port=8192, startup_cost=0.02)
REGISTRY.register("prism", port=8193, startup_cost=0.03, persistent=True)


# ---------------------------------------------------------------------------
# The context manager itself
# ---------------------------------------------------------------------------


class Sidecar:
    """Context manager that guarantees a sidecar is up inside the block.

    Usage::

        with Sidecar("foley") as report:
            ... do dependent work ...

    On entry the sidecar is started if it is not already running; on exit
    it is stopped again *unless* it is marked persistent or it was already
    running before the block (i.e. we did not start it, so we do not own
    its lifetime).  Any exception raised inside the block still triggers
    the teardown, which is the whole point of the pattern.
    """

    def __init__(self, name: str, registry: Optional[SidecarRegistry] = None,
                 clock=time.monotonic) -> None:
        self.name = name
        self.registry = registry if registry is not None else REGISTRY
        self._clock = clock
        self._we_started = False
        self._t0: Optional[float] = None
        self._t1: Optional[float] = None
        self._task_ms: float = 0.0
        self._error: Optional[str] = None

    # -- context protocol --------------------------------------------------
    def __enter__(self) -> Dict[str, Any]:
        st = self.registry.state(self.name)  # raises KeyError if unknown
        self._t0 = self._clock()
        if not st.running:
            # simulated boot cost
            time.sleep(st.spec.startup_cost)
            st.running = True
            st.started_at = self._clock()
            st.start_count += 1
            self._we_started = True
        return {"name": self.name, "port": st.spec.port,
                "started_by_us": self._we_started}

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._t1 = self._clock()
        self._task_ms = (self._t1 - self._t0) * 1000.0
        st = self.registry.state(self.name)
        if self._we_started and not st.spec.persistent:
            st.running = False
            st.started_at = None
            st.stop_count += 1
        if exc_type is not None:
            self._error = f"{exc_type.__name__}: {exc}"
        return False  # never swallow exceptions

    # -- reporting ---------------------------------------------------------
    def report(self) -> Dict[str, Any]:
        st = self.registry.state(self.name)
        return {
            "name": self.name,
            "port": st.spec.port,
            "started_by_us": self._we_started,
            "still_running": st.running,
            "task_ms": round(self._task_ms, 3),
            "start_count": st.start_count,
            "stop_count": st.stop_count,
            "error": self._error,
        }


@contextmanager
def sidecar(name: str, registry: Optional[SidecarRegistry] = None) -> Iterator[Dict[str, Any]]:
    """Functional flavour of :class:`Sidecar` for use in plain code."""
    cm = Sidecar(name, registry=registry)
    info = cm.__enter__()
    try:
        yield info
    finally:
        cm.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# The dependent task (pure torch, CPU)
# ---------------------------------------------------------------------------


def _as_image(image: Any) -> torch.Tensor:
    """Validate and clone an IMAGE tensor [B,H,W,C] in 0..1."""
    if not isinstance(image, torch.Tensor):
        raise TypeError("image must be a torch.Tensor")
    if image.dim() != 4:
        raise ValueError(f"image must be 4D [B,H,W,C], got {image.dim()}D")
    if image.shape[-1] not in (1, 3, 4):
        raise ValueError(f"image channels must be 1/3/4, got {image.shape[-1]}")
    if not torch.isfinite(image).all():
        raise ValueError("image contains non-finite values")
    if image.min() < -1e-6 or image.max() > 1 + 1e-6:
        raise ValueError("image values must be in 0..1")
    return image.detach().clone().float().cpu()


def _dependent_task(image: torch.Tensor, prompt: str,
                    info: Dict[str, Any]) -> torch.Tensor:
    """Simulated audio-driven image enhancement.

    The 'sidecar' (e.g. a foley model) would normally produce an audio
    track; here we deterministically derive a per-pixel gain from the
    prompt so the output depends on both the image and the sidecar task,
    without any external service.
    """
    # deterministic pseudo-energy from the prompt (plain python, no hash()
    # because it is salted per-process)
    energy = 0
    for ch in prompt.encode("utf-8"):
        energy = (energy * 31 + ch) % 1000
    gain = 1.0 + (energy % 100) / 100.0  # 1.0 .. 1.99
    # spatial ramp so the result is not a trivial scalar multiply
    h, w = image.shape[1], image.shape[2]
    ramp = torch.linspace(0.0, 1.0, w, device=image.device).view(1, 1, w, 1)
    out = image * (gain * (0.5 + 0.5 * ramp))
    return out.clamp_(0.0, 1.0)


# ---------------------------------------------------------------------------
# ComfyUI node
# ---------------------------------------------------------------------------


class PSN_SidecarGuardedTask:
    """Run a dependent generation task inside a Sidecar context manager.

    Guarantees the named sidecar service is up for the duration of the
    task and tears it down afterwards (unless it is persistent or was
    already running).  Returns the processed image and a report dict.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "sidecar": (sorted(REGISTRY.known()),),
                "prompt": ("STRING", {"default": "a bird sings in a forest",
                                      "multiline": True}),
            },
            "optional": {
                "ensure_running": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "SIDECAR_REPORT")
    RETURN_NAMES = ("image", "report")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, image: torch.Tensor, sidecar: str, prompt: str,
            ensure_running: bool = True) -> Tuple[torch.Tensor, Dict[str, Any]]:
        img = _as_image(image)
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if sidecar not in REGISTRY.known():
            raise ValueError(f"unknown sidecar: {sidecar!r}")

        if ensure_running:
            cm = Sidecar(sidecar)
            info = cm.__enter__()
            try:
                out = _dependent_task(img, prompt, info)
            finally:
                cm.__exit__(None, None, None)
            report = cm.report()
        else:
            # no guard: task runs, but we still record a minimal report
            st = REGISTRY.state(sidecar)
            out = _dependent_task(img, prompt, {"name": sidecar, "port": st.spec.port})
            report = {"name": sidecar, "port": st.spec.port,
                      "started_by_us": False, "still_running": st.running,
                      "task_ms": 0.0, "start_count": st.start_count,
                      "stop_count": st.stop_count, "error": None,
                      "guarded": False}
        return (out, report)


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_SidecarGuardedTask": PSN_SidecarGuardedTask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_SidecarGuardedTask": "Sidecar Guarded Task (context manager)",
}
