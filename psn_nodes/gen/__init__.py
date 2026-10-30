"""Nodes written by the Qwen node factory from the knowledge-base specs, reviewed before they were merged (see PROVENANCE.md). Each module is imported on its own: one that fails to import
is skipped and recorded in LOAD_ERRORS instead of taking the rest down, and a node name that is already taken is never overridden."""
import importlib, os, pkgutil

NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS, LOAD_ERRORS = {}, {}, {}
EXTENDED_ONLY = {"psn_gemini_prompt_crafter"}      # prepares requests for a closed paid API: not registered in the open edition (EDITIONS.md)

def load(taken=()):
    for m in sorted(pkgutil.iter_modules([os.path.dirname(__file__)]), key=lambda m: m.name):
        if m.name.startswith("_") or (m.name in EXTENDED_ONLY and os.environ.get("PSN_EDITION", "open") != "extended"): continue
        try: mod = importlib.import_module(f"{__name__}.{m.name}")
        except Exception as e: LOAD_ERRORS[m.name] = f"{type(e).__name__}: {str(e)[:160]}"; continue
        for k, v in getattr(mod, "NODE_CLASS_MAPPINGS", {}).items():
            if k in NODE_CLASS_MAPPINGS or k in taken: LOAD_ERRORS[f"{m.name}:{k}"] = "name already taken, skipped"; continue
            NODE_CLASS_MAPPINGS[k] = v; NODE_DISPLAY_NAME_MAPPINGS[k] = getattr(mod, "NODE_DISPLAY_NAME_MAPPINGS", {}).get(k, k)
    return NODE_CLASS_MAPPINGS
