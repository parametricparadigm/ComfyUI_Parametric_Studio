"""One table of everything the studio can do: each workflow template with its family instance, readiness and proof level. Carried over from the home studio's model catalogue (one entry per recipe,
one source for every page), generated from the real files instead of kept by hand. Original code."""
import json, os, urllib.request
from psn import readiness, proof, instances
from psn.graph import GraphBuilder

def fill_defaults(graph, defaults):
    from copy import deepcopy
    g = deepcopy(graph)
    for n in g.values():
        for k, v in (n.get("inputs") or {}).items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"): n["inputs"][k] = defaults.get(v[2:-1], v)
    return g

def family_of(graph, inst_root=None):
    """The instance family whose model folders contain the most of this workflow's models."""
    need = {m["value"] for m in readiness.required_models(graph)}; best, score = None, 0
    try: fams = instances.families()
    except OSError: return None
    for f in fams:
        s = 0
        for t, paths in instances.model_dirs(f).items():
            for rel in paths:
                d = os.path.join(instances.MODELS, rel)
                s += sum(1 for v in need if os.path.exists(os.path.join(d, v)) or os.path.exists(os.path.join(d, os.path.basename(v))))
        if s > score: best, score = f, s
    return best

def build(workflows_dir, object_info=None, defaults=None, models=None):
    rows = []
    for fn in sorted(os.listdir(workflows_dir)):
        if not fn.endswith("_api.json"): continue
        wid = fn[:-5]; g = json.load(open(os.path.join(workflows_dir, fn))); rep = readiness.check(g, models); problems = []
        if object_info is not None: problems = GraphBuilder.from_prompt(fill_defaults(g, defaults or {})).validate(object_info)
        if object_info is not None: proof.record_load_test(wid, g, problems, rep)
        lvl, why = proof.level(wid, g); fam = family_of(g)
        inst = {}
        try: inst = instances.load(fam) if fam else {}
        except OSError: pass
        rows.append({"id": wid, "family": fam, "port": inst.get("port"), "est_vram_gb": inst.get("est_vram_gb"), "nodes": len(g), "ready": rep["ready"], "models_gb": rep["total_gb"], "missing": [m["value"] for m in rep["missing"]],
                     "proof": lvl, "proof_why": why, "validation_problems": problems[:3]})
    return rows

def to_md(rows):
    L = ["# Workflow catalogue", "", "| workflow | family (port) | ready | models | proof | note |", "|---|---|---|---|---|---|"]
    L += [f"| `{r['id']}` | {r['family']} ({r['port']}) | {'yes' if r['ready'] else 'NO: ' + ', '.join(r['missing'][:2])} | {r['models_gb']} GB | **{r['proof']}** | {r['proof_why'][:90]} |" for r in rows]
    return "\n".join(L) + "\n"
