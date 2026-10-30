"""The local sorting agent. Give it folders; it splits them into models (a model = a directory that directly holds weights, or a diffusers-style repo kept whole), gathers evidence for each, asks the verified `model_sorter` subagent to place it in a family and
function group, and (with --apply) adds symlinks under _complete_pipelines/<Family>/ and writes an undo manifest. Nothing is moved, changed or deleted; undo removes exactly the symlinks it made. Original code.
CLI: python3 -m psn.modelsort_agent FOLDER [FOLDER...] [--apply] [--workers 8]    undo: python3 -m psn.modelsort_agent --undo MANIFEST.json"""
import collections, json, os, re, sys, time
from psn import modelsort as MS, instances, paths
from psn.subagents import run_subagent, fan_out
SKIP = {"NODES", "KB", "packs", ".cache", "__pycache__", ".git", "node_modules"}; DOCS = ("MODEL.md", "README_MODEL_NOTES.md", "README.md", "readme.md", "CHATTERBOX.md", "config.yaml", "config.json", "model_index.json")
COMFY_GROUPS = {"image", "video", "3d", "control", "upscale-restore", "text-encoder"}
def _models_in(d, deep=False):
    out = []
    for dp, ds, fs in os.walk(d):
        ds[:] = [x for x in ds if x not in SKIP]
        for f in fs:
            p = os.path.join(dp, f)
            if f.lower().endswith(MS.EXT) and os.path.exists(p) and os.path.getsize(p) > 1_000_000: out.append(p)
        if not deep: break
    return out
def find_units(folder):
    """[{name, path, files}]. A directory with model_index.json is one unit (whole tree); otherwise each directory that directly holds weights is a unit; loose weights in `folder` are one unit each."""
    units, folder = [], folder.rstrip("/")
    def walk(d):
        if os.path.isfile(os.path.join(d, "model_index.json")):
            f = _models_in(d, deep=True)
            if f: units.append({"name": os.path.relpath(d, os.path.dirname(folder)), "path": d, "files": f}); return
        direct = _models_in(d)
        if direct and d != folder: units.append({"name": os.path.relpath(d, os.path.dirname(folder)), "path": d, "files": direct})
        elif direct: [units.append({"name": os.path.relpath(f, os.path.dirname(folder)), "path": f, "files": [f]}) for f in direct]
        for e in sorted(os.listdir(d)):
            if e not in SKIP and os.path.isdir(os.path.join(d, e)) and not os.path.islink(os.path.join(d, e)): walk(os.path.join(d, e))
    walk(folder); return units
def evidence(u, index):
    big = sorted(u["files"], key=lambda p: -os.path.getsize(p))[:5]; facts, cands = [], []
    tree = [f"{os.path.relpath(p, u['path']) if os.path.isdir(u['path']) else os.path.basename(p)}  {os.path.getsize(p)/1e9:.2f} GB" for p in sorted(u["files"])[:25]]
    if len(u["files"]) > 25: tree.append(f"... and {len(u['files']) - 25} more weight files")
    for p in big:
        r = MS.classify(p, index); facts.append(f"{r['name']}: format={r['format']} dtype={r.get('dtype','?')} params={r.get('params_m','?')}M tensors={r.get('tensors','?')} keys={','.join(r.get('prefixes', [])[:5])} meta={json.dumps(r.get('meta', {}))[:140]} gguf={json.dumps(r.get('gguf') or {})[:120]}")
        if r["candidates"]: cands.append(f"{r['name']}: " + "; ".join(f"{c['family']} ({c['score']}; {c['why'][0]})" for c in r["candidates"][:2]))
    docs, base = [], u["path"] if os.path.isdir(u["path"]) else os.path.dirname(u["path"])
    for d in DOCS:
        p = os.path.join(base, d)
        if os.path.isfile(p): docs.append(f"--- {d}\n" + open(p, errors="replace").read(1200))
    parent = os.path.join(os.path.dirname(base), "README_MODEL_NOTES.md")
    if os.path.isfile(parent):
        lines = [l for l in open(parent, errors="replace").read().splitlines() if os.path.basename(base).lower() in l.lower()][:6]
        if lines: docs.append("--- parent notes (lines naming this model)\n" + "\n".join(lines))
    return {"source": "NAME: " + u["name"] + "\nFILES:\n" + "\n".join(tree) + "\nTENSOR FACTS:\n" + "\n".join(facts) + "\nLAYOUT CANDIDATES:\n" + ("\n".join(cands) or "none") + "\nDOCS:\n" + "\n".join(docs), "files": big}
def sort_folders(folders, apply=False, workers=8, runner=run_subagent, models=None, **kw):
    models = models or instances.MODELS; kb = os.path.join(paths.kb_root(), "families"); tools = f"{models}/_complete_pipelines/_tools"
    labels = sorted(set(instances.families(models)) | ({d for d in os.listdir(kb) if not d.startswith(("FAMILY-", "_"))} if os.path.isdir(kb) else set()) | (set(os.listdir(tools)) if os.path.isdir(tools) else set()))
    index = MS.build_index(models); units = [u for f in folders for u in find_units(f)]; ev = [evidence(u, index) for u in units]
    jobs = [{"role": "model_sorter", "task": "Place this model in a family and function group.", "ctx": {"source": e["source"], "labels": labels}} for e in ev]
    res = fan_out(jobs, max_workers=workers, runner=runner, **kw) if jobs else []
    rows = []
    for u, e, r in zip(units, ev, res):
        o = r.output if r.ok else {}
        rows.append({"unit": u["name"], "path": u["path"], "files": len(u["files"]), "gb": round(sum(os.path.getsize(p) for p in u["files"]) / 1e9, 2), "ok": r.ok, "family": o.get("family"), "new_family": o.get("new_family"), "group": o.get("group"), "kind": o.get("kind"),
                     "confidence": o.get("confidence"), "evidence": o.get("evidence", []), "problems": r.problems, "weights": u["files"]})
    links = plan_links(rows, models) if apply or True else []
    made = []
    if apply: made = do_links(links)
    return rows, links, made
def weights_for(path):
    if os.path.isfile(path): return [path]
    return _models_in(path, deep=True) if os.path.isfile(os.path.join(path, "model_index.json")) else _models_in(path)
def canonicalize(rows, labels):
    """One spelling per family: an existing label that matches ignoring case wins; new names that differ only in case are merged to the first spelling seen."""
    low = {l.lower(): l for l in labels}
    for r in rows:
        if r.get("family"):
            k = r["family"].lower()
            if k in low: r["family"] = low[k]; r["new_family"] = r["family"] not in labels
            else: low[k] = r["family"]
    return rows
def apply_report(report, models=None, apply=True):
    models = models or instances.MODELS; kb = os.path.join(paths.kb_root(), "families"); tools = f"{models}/_complete_pipelines/_tools"
    labels = sorted(set(instances.families(models)) | ({d for d in os.listdir(kb) if not d.startswith(("FAMILY-", "_"))} if os.path.isdir(kb) else set()) | (set(os.listdir(tools)) if os.path.isdir(tools) else set()))
    rows = [r for r in json.load(open(report)) if r["ok"]]
    for r in rows: r["weights"] = weights_for(r["path"])
    rows = canonicalize(rows, labels); plan = plan_links(rows, models); made = do_links(plan) if apply else []
    return rows, plan, made
def plan_links(rows, models):
    plan = []
    for r in rows:
        if not r["ok"] or r["confidence"] not in ("high", "medium"): continue
        fam = r["family"]; has_denoiser = any(MS.role_of(MS.facts_of(p)) in ("diffusion_models", "checkpoints") for p in r["weights"][:6])
        main = r["group"] in COMFY_GROUPS and (not r["new_family"] or (r["group"] in ("image", "video", "3d") and has_denoiser))                    # a new family joins the main list only if it has a real denoiser
        base = f"{models}/_complete_pipelines/{fam}" if main else f"{models}/_complete_pipelines/_tools/{fam}"
        for p in r["weights"]:
            role = MS.role_of(MS.facts_of(p)) if main else "weights"
            if role in (None, "llm_gguf"): role = "weights"
            plan.append((p, f"{base}/{role}/{os.path.basename(p)}", fam, r["new_family"]))
        docs = r["path"] if os.path.isdir(r["path"]) else os.path.dirname(r["path"])
        for d in ("MODEL.md", "README.md"):
            if os.path.isfile(os.path.join(docs, d)): plan.append((os.path.join(docs, d), f"{base}/NOTES/{os.path.basename(r['path'])}_{d}", fam, r["new_family"]))
    return plan
def do_links(plan):
    made = []
    for src, dst, fam, new in plan:
        if os.path.lexists(dst): continue
        os.makedirs(os.path.dirname(dst), exist_ok=True); os.symlink(os.path.realpath(src), dst); made.append(dst)
    if made:
        mp = os.path.expanduser(f"~/Documents/MODEL_SORT_LINKS_{time.strftime('%Y%m%d-%H%M%S')}.json"); os.makedirs(os.path.dirname(mp), exist_ok=True); json.dump({"links": made, "note": "symlinks created by psn.modelsort_agent; undo removes exactly these"}, open(mp, "w"), indent=1); print("undo manifest:", mp)
    return made
def undo(manifest):
    n = 0
    for p in json.load(open(manifest))["links"]:
        if os.path.islink(p): os.unlink(p); n += 1
    return n
def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    if "--from-report" in a:
        rows, plan, made = apply_report(a[a.index("--from-report") + 1], apply="--apply" in a)
        print(f"{len(rows)} models; {'LINKED' if '--apply' in a else 'WOULD LINK'} {len(made) if '--apply' in a else len(plan)} symlinks; new families: {len({r['family'] for r in rows if r['new_family']})}"); return
    if "--undo" in a: print("removed", undo(a[a.index("--undo") + 1]), "symlinks"); return
    skipped = [x for x in a if not x.startswith("--") and os.path.basename(x.rstrip("/")) in ("_complete_pipelines", "_libraries")]
    if skipped: print("skipped (these ARE the family structure / shared libraries, sorting them into themselves would be circular):", ", ".join(skipped))
    apply = "--apply" in a; w = int(a[a.index("--workers") + 1]) if "--workers" in a else 8; folders = [x for x in a if not x.startswith("--") and os.path.isdir(x) and x not in skipped]
    rows, links, made = sort_folders(folders, apply, w); c = collections.Counter((r["confidence"] or "failed") for r in rows)
    print(f"{len(rows)} models from {len(folders)} folders: {dict(c)}")
    for r in rows: print(f"  {(r['family'] or '-'):22}{'*' if r['new_family'] else ' '} {str(r['group'] or '-'):18} {str(r['confidence'] or '-'):7} {r['gb']:>7} GB  {r['unit'][:40]:40} {('| ' + r['kind']) if r['kind'] else '| ' + '; '.join(r['problems'])[:60]}")
    print(("LINKED" if apply else "WOULD LINK"), len(made) if apply else len(links), "symlinks (new families marked *)")
    out = os.path.expanduser(f"~/Documents/MODEL_SORT_AGENT_{time.strftime('%Y%m%d-%H%M%S')}.json"); os.makedirs(os.path.dirname(out), exist_ok=True); json.dump([{k: v for k, v in r.items() if k != "weights"} for r in rows], open(out, "w"), indent=1); print("report:", out)
if __name__ == "__main__": main()
