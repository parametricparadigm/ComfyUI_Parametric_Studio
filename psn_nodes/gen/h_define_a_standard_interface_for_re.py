"""Parametric Studio: standard interface for resolving per-tool Python interpreter paths.

The studio runs several isolated tool families (scrape, train, eval, ...) each in its
own virtualenv so that dependency conflicts (torch/cuda vs. local LLM stacks) cannot
leak between them.  This module defines a small, dependency-free *interface* for that
resolution:

* ``InterpreterSpec``  -- immutable description of one tool family's environment.
* ``InterpreterRegistry`` -- maps family names to specs and resolves interpreter paths
  with a documented, overridable search order.
* ``PSN_InterpreterResolve`` / ``PSN_InterpreterRegistryBuild`` -- ComfyUI nodes that
  expose the interface to the graph.

No filesystem access is performed here: paths are *computed* from the spec (root dir,
platform, family name) so the module stays pure and testable.  A real deployment would
plug a ``probe`` callable into the registry to verify the interpreter actually exists.
"""

from __future__ import annotations

import posixpath

CAT = "ParametricStudio/Environments"

# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------

#: canonical platform tags the studio supports
_PLATFORMS = ("linux", "darwin", "win32")


class InterpreterSpec:
    """Immutable description of one isolated tool environment.

    Attributes
    ----------
    family : str
        Tool family name, e.g. ``"scrape"``.
    root : str
        Directory that contains the per-family venv folders.
    platform : str
        One of ``_PLATFORMS``.
    venv_name : str
        Name of the venv directory inside ``root`` (default ``"venv"``).
    """

    __slots__ = ("family", "root", "platform", "venv_name")

    def __init__(self, family, root, platform="linux", venv_name="venv"):
        if not isinstance(family, str) or not family.strip():
            raise ValueError("family must be a non-empty string")
        if not isinstance(root, str) or not root.strip():
            raise ValueError("root must be a non-empty string")
        if platform not in _PLATFORMS:
            raise ValueError("platform must be one of %r" % (_PLATFORMS,))
        if not isinstance(venv_name, str) or not venv_name.strip():
            raise ValueError("venv_name must be a non-empty string")
        self.family = family.strip()
        self.root = root.strip().rstrip("/")
        self.platform = platform
        self.venv_name = venv_name.strip()

    # -- path computation (pure, no fs) ------------------------------------
    @property
    def venv_dir(self):
        """Absolute-ish path to the venv directory for this family."""
        return posixpath.join(self.root, self.family, self.venv_name)

    @property
    def bin_dir(self):
        """Directory holding the interpreter binary (bin/ on unix, Scripts/ on win)."""
        sub = "Scripts" if self.platform == "win32" else "bin"
        return posixpath.join(self.venv_dir, sub)

    @property
    def interpreter(self):
        """Path to the python interpreter inside this venv."""
        name = "python.exe" if self.platform == "win32" else "python"
        return posixpath.join(self.bin_dir, name)

    def to_dict(self):
        return {
            "family": self.family,
            "root": self.root,
            "platform": self.platform,
            "venv_name": self.venv_name,
            "venv_dir": self.venv_dir,
            "bin_dir": self.bin_dir,
            "interpreter": self.interpreter,
        }

    def __repr__(self):
        return "InterpreterSpec(family=%r, root=%r, platform=%r, venv_name=%r)" % (
            self.family, self.root, self.platform, self.venv_name,
        )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

class InterpreterRegistry:
    """Maps tool-family names to :class:`InterpreterSpec` objects.

    Resolution order for ``resolve(family)``:

    1. explicit spec registered under *family*;
    2. spec registered under the ``default`` alias;
    3. raise ``KeyError``.

    An optional ``probe`` callable ``(path) -> bool`` can be supplied to *verify*
    the interpreter path (e.g. an existence check).  When a probe is set and it
    rejects a path, ``resolve`` raises ``LookupError`` instead of returning a
    dangling path.
    """

    def __init__(self, probe=None):
        self._specs = {}
        self._probe = probe

    # -- registration -------------------------------------------------------
    def register(self, spec):
        """Register a spec under its family name (and optionally as default)."""
        if not isinstance(spec, InterpreterSpec):
            raise TypeError("spec must be an InterpreterSpec")
        self._specs[spec.family] = spec
        return self

    def set_default(self, family):
        """Alias *family* as the fallback for unknown families."""
        if family not in self._specs:
            raise KeyError("unknown family: %r" % (family,))
        self._specs["default"] = self._specs[family]
        return self

    # -- resolution ---------------------------------------------------------
    def resolve(self, family):
        """Return the interpreter path for *family* (str).

        Raises
        ------
        KeyError
            if no spec matches and no default is set.
        LookupError
            if a probe is configured and it rejects the computed path.
        """
        spec = self._specs.get(family, self._specs.get("default"))
        if spec is None:
            raise KeyError("no interpreter registered for family %r" % (family,))
        path = spec.interpreter
        if self._probe is not None and not self._probe(path):
            raise LookupError("probe rejected interpreter path: %s" % path)
        return path

    def spec(self, family):
        """Return the :class:`InterpreterSpec` for *family* (same fallback rules)."""
        spec = self._specs.get(family, self._specs.get("default"))
        if spec is None:
            raise KeyError("no interpreter registered for family %r" % (family,))
        return spec

    def families(self):
        """Sorted list of registered family names (excluding the ``default`` alias)."""
        return sorted(k for k in self._specs if k != "default")

    def __len__(self):
        return len(self.families())


# ---------------------------------------------------------------------------
# ComfyUI nodes
# ---------------------------------------------------------------------------

class PSN_InterpreterRegistryBuild:
    """Build an :class:`InterpreterRegistry` from a list of family specs.

    The node is a *factory*: it returns a registry object that downstream
    ``PSN_InterpreterResolve`` nodes can consume.  Because ComfyUI wires plain
    Python values between nodes, the registry is passed as an opaque object.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "root": ("STRING", {"default": "/opt/psn/tools", "multiline": False}),
                "platform": (list(_PLATFORMS), {"default": "linux"}),
                "families": ("STRING", {"default": "scrape,train", "multiline": False}),
                "venv_name": ("STRING", {"default": "venv", "multiline": False}),
                "default_family": ("STRING", {"default": "scrape", "multiline": False}),
            }
        }

    RETURN_TYPES = ("INTERPRETER_REGISTRY",)
    RETURN_NAMES = ("registry",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, root, platform, families, venv_name, default_family):
        reg = InterpreterRegistry()
        names = [f.strip() for f in families.split(",") if f.strip()]
        if not names:
            raise ValueError("families must contain at least one name")
        for name in names:
            reg.register(InterpreterSpec(name, root, platform, venv_name))
        df = default_family.strip()
        if df and df in names:
            reg.set_default(df)
        return (reg,)


class PSN_InterpreterResolve:
    """Resolve the interpreter path for a given tool family.

    Returns the path as a STRING plus a boolean ``found`` flag so the graph can
    branch on missing environments without crashing.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "registry": ("INTERPRETER_REGISTRY",),
                "family": ("STRING", {"default": "scrape", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("interpreter_path", "found")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, registry, family):
        if not isinstance(registry, InterpreterRegistry):
            raise TypeError("registry must be an InterpreterRegistry")
        name = family.strip()
        try:
            path = registry.resolve(name)
            return (path, True)
        except (KeyError, LookupError):
            return ("", False)


class PSN_InterpreterSpecInfo:
    """Return the full spec dict for a family as a JSON-ish string (for UI display)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "registry": ("INTERPRETER_REGISTRY",),
                "family": ("STRING", {"default": "scrape", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("spec_json",)
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, registry, family):
        if not isinstance(registry, InterpreterRegistry):
            raise TypeError("registry must be an InterpreterRegistry")
        name = family.strip()
        try:
            spec = registry.spec(name)
        except KeyError:
            return ("{}",)
        import json
        return (json.dumps(spec.to_dict(), indent=2, sort_keys=True),)


# ---------------------------------------------------------------------------
# module-level mappings (ComfyUI convention)
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "PSN_InterpreterRegistryBuild": PSN_InterpreterRegistryBuild,
    "PSN_InterpreterResolve": PSN_InterpreterResolve,
    "PSN_InterpreterSpecInfo": PSN_InterpreterSpecInfo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_InterpreterRegistryBuild": "Interpreter Registry Build",
    "PSN_InterpreterResolve": "Interpreter Resolve",
    "PSN_InterpreterSpecInfo": "Interpreter Spec Info",
}
