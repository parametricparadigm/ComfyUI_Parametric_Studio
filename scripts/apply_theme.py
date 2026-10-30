#!/usr/bin/env python3
"""Apply the Parametric black/gold/green palette to ComfyUI instance(s): merges Comfy.CustomColorPalettes + Comfy.ColorPalette into <instance>/user/default/comfy.settings.json (other settings kept).
Usage: apply_theme.py DIR [DIR ...]   (an instance dir, or a folder of instance dirs with --all)"""
import json, os, sys
from pathlib import Path
PAL = json.load(open(Path(__file__).resolve().parent.parent / "studio" / "theme" / "parametric_palette.json"))
def apply(inst):
    f = Path(inst) / "user" / "default" / "comfy.settings.json"; f.parent.mkdir(parents=True, exist_ok=True)
    cur = json.load(open(f)) if f.exists() else {}
    cur.setdefault("Comfy.CustomColorPalettes", {})["parametric"] = PAL; cur["Comfy.ColorPalette"] = "custom_parametric"
    tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(cur, indent=2)); os.replace(tmp, f); return f
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--all"]; dirs = []
    for a in args:
        p = Path(a)
        dirs += [d for d in sorted(p.iterdir()) if (d / "instance.json").exists() or (d / "custom_nodes").exists()] if "--all" in sys.argv else [p]
    for d in dirs: apply(d)
    print("themed", len(dirs), "instance(s)")
