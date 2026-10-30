"""Hand a finished site to Dyad through the owner's headless bridge (dyad-bridge: create / write / scaffold / info / git). Only those subcommands are allowed: run (dev server), install (package manager, network) and delete are never issued from here.
The bridge location comes from $PSN_DYAD_BRIDGE or ~/bin/dyad-bridge; without it this reports 'not configured' instead of failing. Files go in one by one with fixed argument lists (no shell)."""
import os, re, subprocess
ALLOWED = {"create", "write", "info", "git", "list"}
def bridge_path(): p = os.environ.get("PSN_DYAD_BRIDGE") or os.path.expanduser("~/bin/dyad-bridge"); return p if os.path.isfile(p) and os.access(p, os.X_OK) or os.path.isfile(p) else None
def _call(bridge, *args, timeout=60):
    if args[0] not in ALLOWED: raise PermissionError(f"dyad bridge command '{args[0]}' is not allowed from the studio")
    return subprocess.run(["python3", bridge, *args] if bridge.endswith(".py") or not os.access(bridge, os.X_OK) else [bridge, *args], capture_output=True, text=True, timeout=timeout)
def export_to_dyad(site_dir, name, bridge=None, message="Site from Parametric Studio"):
    b = bridge or bridge_path()
    if not b: return {"ok": False, "status": "not configured: set PSN_DYAD_BRIDGE to the dyad-bridge script"}
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "site"
    r = _call(b, "create", name, "--slug", slug)
    if r.returncode: return {"ok": False, "status": "create failed: " + (r.stderr or r.stdout)[:200]}
    n = 0
    for dp, _, fs in os.walk(site_dir):
        for f in sorted(fs):
            p = os.path.join(dp, f); rel = os.path.relpath(p, site_dir)
            if os.path.getsize(p) > 1_000_000 or rel.startswith(".."): continue
            w = _call(b, "write", slug, "public/" + rel if False else rel, p)
            if w.returncode: return {"ok": False, "status": f"write failed at {rel}: " + (w.stderr or w.stdout)[:160], "files": n}
            n += 1
    g = _call(b, "git", slug, message); return {"ok": True, "slug": slug, "files": n, "git": g.returncode == 0}
