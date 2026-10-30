"""Deliver finished files to a watched folder for other tools (Eagle, DaVinci Resolve, Nuke, Krita...). Original. Writes only under configured roots, sanitised names, no overwrite, optional sidecar JSON."""
import json, os, re, time
from . import policy as P

def _clean(s, n=80): return re.sub(r"[^A-Za-z0-9._-]", "_", str(s))[:n].strip("._") or "file"

def deliver(cfg, files, subfolder="", meta=None):
    """files = [(name, bytes)]. -> list of written paths. Needs config 'deliver': {"enabled": true, "roots": ["/path/a"], "max_mb": 500}."""
    s = P.section(cfg, "deliver"); roots = [os.path.realpath(r) for r in s.get("roots", [])]
    if not roots: raise P.BridgeError("deliver.roots is empty")
    base = roots[0]; sub = "/".join(_clean(p) for p in re.split(r"[\\/]+", subfolder or "") if p and p != ".." and p != ".")
    d = os.path.realpath(os.path.join(base, sub))
    if not any(d == r or d.startswith(r + os.sep) for r in roots): raise P.BridgeError("target is outside the delivery roots")
    if sum(len(b) for _, b in files) > int(s.get("max_mb", 500)) * 1_000_000: raise P.BridgeError("delivery larger than max_mb")
    os.makedirs(d, exist_ok=True); out = []
    for name, data in files:
        stem, ext = os.path.splitext(_clean(name, 120)); ext = ext if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", ext) else ".bin"; p = os.path.join(d, stem + ext); i = 1
        while os.path.exists(p): p = os.path.join(d, f"{stem}_{i}{ext}"); i += 1
        with open(p, "xb") as f: f.write(data)
        if meta is not None:
            with open(p + ".json", "w") as f: json.dump({"file": os.path.basename(p), "delivered": time.strftime("%F %T"), **meta}, f, indent=1, default=str)
        out.append(p)
    return out
