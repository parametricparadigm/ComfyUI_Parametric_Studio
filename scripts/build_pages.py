#!/usr/bin/env python3
"""Builds the read-only demo for GitHub Pages: the real front end and real renders, with the server's answers saved as files. Browsing works; anything that would run a model says so and points at the install.
Usage: build_pages.py [--from http://127.0.0.1:8310] [--out site] [--repo https://github.com/owner/name]"""
import argparse, json, os, re, shutil, urllib.parse, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SHIM = """<script>/* read-only demo: GET /api/x comes from saved files, POST explains how to run it for real */
(() => { const real = window.fetch.bind(window), base = new URL("demo-api/", location.href).href, json = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json" } });
  window.fetch = async (u, o = {}) => { const m = String(u && u.url || u).match(/(?:^|\\/)api\\/(.*)$/); if (!m) return real(u, o);
    if ((o.method || "GET").toUpperCase() !== "GET") return json({ detail: "This is the read-only demo. Install Parametric Studio to run this on your own GPU." }, 403);
    const k = decodeURIComponent(m[1]).split("?")[0].replace(/[^\\w.-]+/g, "__"); const r = await real(base + k + ".json"); return r.ok ? r : json({ detail: "Not available in the read-only demo." }, 404); }; })();</script>"""
BANNER = """<a href="%s" style="position:fixed;left:50%%;bottom:10px;transform:translateX(-50%%);z-index:60;background:#f5c518;color:#141006;font:600 13px Inter,system-ui;padding:8px 14px;border-radius:10px;text-decoration:none;box-shadow:0 8px 24px rgba(0,0,0,.5);max-width:92vw;text-align:center">Read-only demo: real UI, real renders from one GPU. Get it and generate your own</a>"""

def clean(o):
    """No box paths in the published answers."""
    if isinstance(o, str): return re.sub(r"(?:~|/home/[^/\s]+|/mnt/[^/\s]+)/\S*", "your models folder", o)
    if isinstance(o, list): return [clean(x) for x in o]
    return {k: clean(v) for k, v in o.items()} if isinstance(o, dict) else o

def get(base, path):
    with urllib.request.urlopen(base + path, timeout=60) as r: return json.load(r)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="base", default="http://127.0.0.1:8310"); ap.add_argument("--out", default=os.path.join(ROOT, "site")); ap.add_argument("--repo", default="https://github.com/parametricparadigm/ComfyUI_Parametric_Studio"); a = ap.parse_args()
    shutil.rmtree(a.out, ignore_errors=True); shutil.copytree(os.path.join(ROOT, "studio", "web"), a.out, ignore=shutil.ignore_patterns("sw.js", "__pycache__")); d = os.path.join(a.out, "demo-api"); os.makedirs(d); open(os.path.join(a.out, ".nojekyll"), "w").close(); saved = 0
    def save(path, obj=None):
        nonlocal saved
        try: data = get(a.base, "/api/" + path) if obj is None else obj
        except Exception as e: print("  skipped", path, type(e).__name__); return None
        open(os.path.join(d, re.sub(r"[^\w.-]+", "__", path.split("?")[0]) + ".json"), "w").write(json.dumps(clean(data))); saved += 1; return data
    for p in ("goals", "atlas", "crew", "edits", "models", "models/readiness", "models3d", "packs", "apps", "processes", "recipes", "schedules", "calibrate", "voice", "user", "family-graphs"): save(p)
    save("health", {"comfy": True, "comfy_url": "read-only demo", "edition": "demo", "backend": {"backend": "local", "target": "local", "spends_credits": False}})
    show = json.load(open(os.path.join(ROOT, "studio", "web", "showcase", "showcase.json")))
    save("history", [{"job": x["id"], "goal": x["goal"], "prompt": x["prompt"], "options": x.get("options", {}), "seed": 11, "files": [{"filename": os.path.basename(x["src"]), "kind": x["kind"], "url": x["src"]}]} for x in show])
    for g in (save("graphs") or []): save("graphs/" + g["goal"])
    uni = save("university"); courses = (uni.get("courses") if isinstance(uni, dict) else uni) or []
    for c in courses:
        if isinstance(c, dict) and c.get("code"): save("university/" + c["code"])
    fams = save("families"); rows = (fams.get("families") if isinstance(fams, dict) else fams) or []
    for f in rows:
        if isinstance(f, dict) and f.get("slug"): save("families/" + f["slug"])
    packs = save("packs"); rows = (packs.get("packs") if isinstance(packs, dict) else packs) or []
    for x in (rows if isinstance(rows, list) else rows.values()):
        if isinstance(x, dict) and x.get("id"): save("packs/" + x["id"])
    procs = save("processes"); rows = (procs.get("processes") if isinstance(procs, dict) else procs) or []
    for x in rows:
        if isinstance(x, dict) and x.get("id") and x.get("doc", True): save(f"processes/{x['id']}/doc")
    import sys; sys.path.insert(0, ROOT)
    from studio.glb import knot_glb
    open(os.path.join(d, "sample.glb.json"), "wb").write(knot_glb())
    p = os.path.join(a.out, "index.html"); h = open(p).read(); h = h.replace('<script type="importmap">', SHIM + '\n<script type="importmap">', 1); h = re.sub(r'<script>if \("serviceWorker".*?</script>', "", h, flags=re.S); h = h.replace("</body>", (BANNER % a.repo) + "\n</body>", 1); open(p, "w").write(h)
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(a.out) for f in fs); print(f"site: {saved} saved answers, {size >> 20} MB at {a.out}")
main()
