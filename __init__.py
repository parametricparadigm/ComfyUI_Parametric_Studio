"""ComfyUI_Parametric_Studio custom nodes (PSN_*). Original code, AGPL-3.0-or-later. See PROVENANCE.md."""
from .psn_nodes import logic as _logic, bridges as _bridges, subagents as _subagents, gen as _gen, sitebuilder as _site, quality as _quality, prompts as _prompts
NODE_CLASS_MAPPINGS = {**_logic.NODE_CLASS_MAPPINGS, **_bridges.NODE_CLASS_MAPPINGS, **_subagents.NODE_CLASS_MAPPINGS, **_site.NODE_CLASS_MAPPINGS, **_quality.NODE_CLASS_MAPPINGS, **_prompts.NODE_CLASS_MAPPINGS}
try:                                   # real tensor latent ops need torch (always present inside ComfyUI)
    from .psn_nodes import latent as _latent, loaders as _loaders
    NODE_CLASS_MAPPINGS.update(_latent.NODE_CLASS_MAPPINGS); NODE_CLASS_MAPPINGS.update(_loaders.NODE_CLASS_MAPPINGS)
except ImportError:
    _latent = _loaders = None
try:                                   # the V3 flagship pack needs comfy_api (present inside ComfyUI). V3 classes go in this mapping too: load_custom_node only reads comfy_entrypoint when NODE_CLASS_MAPPINGS is absent
    from .psn_nodes import flagship as _flagship
    NODE_CLASS_MAPPINGS.update(_flagship.NODE_CLASS_MAPPINGS)
except ImportError:
    _flagship = None
NODE_CLASS_MAPPINGS.update({k: v for k, v in _gen.load(taken=set(NODE_CLASS_MAPPINGS)).items()})
NODE_DISPLAY_NAME_MAPPINGS = {**_logic.NODE_DISPLAY_NAME_MAPPINGS, **_bridges.NODE_DISPLAY_NAME_MAPPINGS, **_subagents.NODE_DISPLAY_NAME_MAPPINGS, **_site.NODE_DISPLAY_NAME_MAPPINGS, **_quality.NODE_DISPLAY_NAME_MAPPINGS, **_prompts.NODE_DISPLAY_NAME_MAPPINGS, **_gen.NODE_DISPLAY_NAME_MAPPINGS, **(_latent.NODE_DISPLAY_NAME_MAPPINGS if _latent else {}), **(_loaders.NODE_DISPLAY_NAME_MAPPINGS if _loaders else {}), **(_flagship.NODE_DISPLAY_NAME_MAPPINGS if _flagship else {})}
from .psn_nodes.tidy import tidy as _tidy
_tidy(NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS)   # one category tree, names, descriptions and tooltips; ids and inputs stay as they are
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
