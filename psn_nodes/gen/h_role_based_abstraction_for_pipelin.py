"""Role-based abstraction for pipeline steps.

A pipeline step can declare an *abstract* requirement (a role id such as
``img:best_photo``) instead of a concrete studio entry.  This module keeps a
small in-memory catalogue of concrete studio entries, each tagged with the
roles it fulfils, and resolves role ids to concrete entries with settings.

Two ComfyUI nodes are provided:

* ``PSN_RoleCatalogue`` -- builds a role catalogue from a JSON-ish string
  description of studio entries and returns it as a ``ROLE_CATALOGUE``
  (a plain dict) plus a human readable summary string.
* ``PSN_RoleResolve`` -- given a catalogue and a role id (with optional
  overrides), resolves the concrete studio entry and returns the entry id,
  its settings as a string, and a boolean flag indicating success.

The module is pure Python + torch (torch is only used to validate that a
``LATENT`` input, when supplied, is a well-formed latent dict so that the
node can be wired into a real pipeline).  No network, no file IO, no
subprocess.
"""

import json

import torch

CAT = "ParametricStudio/Pipelines"

ROLE_CATALOGUE = ("ROLE_CATALOGUE",)


def _parse_catalogue_text(text):
    """Parse a JSON string describing studio entries into a catalogue dict.

    Expected shape::

        {
          "entries": [
            {"id": "photo_a", "roles": ["img:best_photo"],
             "settings": {"model": "sd_xl", "steps": 30}},
            ...
          ]
        }

    Returns a dict mapping role id -> list of entry ids (in catalogue order)
    plus an ``"entries"`` key holding the entry records.  Raises ``ValueError``
    on malformed input.
    """
    if not isinstance(text, str):
        raise ValueError("catalogue text must be a string")
    data = json.loads(text)
    if not isinstance(data, dict) or "entries" not in data:
        raise ValueError("catalogue must be an object with an 'entries' list")
    entries = data["entries"]
    if not isinstance(entries, list):
        raise ValueError("'entries' must be a list")
    role_map = {}
    clean_entries = []
    seen_ids = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ValueError("each entry must be an object")
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            raise ValueError("entry %d: 'id' must be a non-empty string" % i)
        if eid in seen_ids:
            raise ValueError("duplicate entry id: %s" % eid)
        seen_ids.add(eid)
        roles = e.get("roles", [])
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise ValueError("entry %s: 'roles' must be a list of strings" % eid)
        settings = e.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError("entry %s: 'settings' must be an object" % eid)
        clean_entries.append({"id": eid, "roles": list(roles), "settings": dict(settings)})
        for r in roles:
            role_map.setdefault(r, []).append(eid)
    return {"entries": clean_entries, "roles": role_map}


def _resolve_role(catalogue, role_id, overrides=None):
    """Resolve a role id to a concrete entry id and merged settings.

    ``overrides`` is an optional dict of settings to merge on top of the
    entry's own settings (override wins).  Returns ``(entry_id, settings,
    ok)`` where ``ok`` is False when the role is unknown.
    """
    if not isinstance(catalogue, dict) or "roles" not in catalogue:
        raise ValueError("catalogue must be a dict produced by PSN_RoleCatalogue")
    if not isinstance(role_id, str) or not role_id:
        raise ValueError("role_id must be a non-empty string")
    candidates = catalogue["roles"].get(role_id)
    if not candidates:
        return ("", {}, False)
    entry_id = candidates[0]
    entry = next(e for e in catalogue["entries"] if e["id"] == entry_id)
    settings = dict(entry["settings"])
    if overrides:
        if not isinstance(overrides, dict):
            raise ValueError("overrides must be a dict")
        for k, v in overrides.items():
            settings[k] = v
    return (entry_id, settings, True)


def _check_latent(latent):
    """Validate a LATENT dict without modifying it.  Returns the samples tensor."""
    if not isinstance(latent, dict) or "samples" not in latent:
        raise ValueError("latent must be a dict with a 'samples' tensor")
    s = latent["samples"]
    if not isinstance(s, torch.Tensor):
        raise ValueError("latent['samples'] must be a torch tensor")
    if s.dim() != 4:
        raise ValueError("latent['samples'] must be [B, C, H, W]")
    return s


class PSN_RoleCatalogue:
    """Build a role catalogue from a JSON description of studio entries."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "catalogue_json": ("STRING", {"multiline": True, "default": "{}"}),
            }
        }

    RETURN_TYPES = ("ROLE_CATALOGUE", "STRING")
    RETURN_NAMES = ("catalogue", "summary")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, catalogue_json):
        cat = _parse_catalogue_text(catalogue_json)
        n_entries = len(cat["entries"])
        n_roles = len(cat["roles"])
        summary = "catalogue: %d entries, %d roles" % (n_entries, n_roles)
        return (cat, summary)


class PSN_RoleResolve:
    """Resolve an abstract role id to a concrete studio entry + settings."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "catalogue": ("ROLE_CATALOGUE",),
                "role_id": ("STRING", {"default": "img:best_photo"}),
            },
            "optional": {
                "overrides_json": ("STRING", {"multiline": True, "default": "{}"}),
                "latent": ("LATENT",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("entry_id", "settings_json", "resolved")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, catalogue, role_id, overrides_json="{}", latent=None):
        if latent is not None:
            _check_latent(latent)
        overrides = None
        if overrides_json and overrides_json.strip() and overrides_json.strip() != "{}":
            overrides = json.loads(overrides_json)
            if not isinstance(overrides, dict):
                raise ValueError("overrides_json must decode to an object")
        entry_id, settings, ok = _resolve_role(catalogue, role_id, overrides)
        settings_json = json.dumps(settings, sort_keys=True)
        return (entry_id, settings_json, ok)


NODE_CLASS_MAPPINGS = {
    "PSN_RoleCatalogue": PSN_RoleCatalogue,
    "PSN_RoleResolve": PSN_RoleResolve,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_RoleCatalogue": "Role Catalogue (build)",
    "PSN_RoleResolve": "Role Resolve (pipeline step)",
}
