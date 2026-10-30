"""ComfyUI node for the website builder (original). Logic lives in psn/sitebuilder/."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class PSN_SiteBuilder:
    """Build a small, offline, SFW static website from a brief (JSON: name, tagline, about, pages, facts{email,phone,address,hours}, brand colour). The copy is written by the local model and checked by code (no invented contact details); the HTML and CSS are written by deterministic code from contrast-checked design tokens. Images start as placeholders plus a prompt list (images_todo.json) for a ComfyUI instance."""
    @classmethod
    def INPUT_TYPES(cls): return {"required": {"brief_json": ("STRING", {"multiline": True, "default": '{"name": "Harbor Light Bakery", "about": "A family bakery with sourdough and pastries.", "facts": {"email": "hello@example.org"}, "brand": "#b5651d"}'}), "output_name": ("STRING", {"default": "my-site"})},
                                  "optional": {"export_to_dyad": ("BOOLEAN", {"default": False})}}
    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING"); RETURN_NAMES = ("site_dir", "ok", "report_json"); FUNCTION = "run"; CATEGORY = "ParametricStudio/Sites"
    def run(self, brief_json, output_name, export_to_dyad=False):
        import re
        from psn.sitebuilder import build_site
        from psn.sitebuilder.export import export_to_dyad as to_dyad
        brief = json.loads(brief_json); base = os.environ.get("PSN_SITES_DIR") or os.path.expanduser("~/.local/state/parametric_studio/sites"); out = os.path.join(base, re.sub(r"[^a-z0-9-]+", "-", output_name.lower()).strip("-") or "site")
        rep = build_site(brief, out)
        if rep.get("ok") and export_to_dyad: rep["dyad"] = to_dyad(out, brief["name"])
        return (out if rep.get("ok") else "", bool(rep.get("ok")), json.dumps(rep))
NODE_CLASS_MAPPINGS = {"PSN_SiteBuilder": PSN_SiteBuilder}; NODE_DISPLAY_NAME_MAPPINGS = {"PSN_SiteBuilder": "PSN Website Builder"}
