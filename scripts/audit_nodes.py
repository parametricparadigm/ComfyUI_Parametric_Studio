#!/usr/bin/env python3
"""Audit every PSN node from its source and its live class: registers, serializes, metadata, duplicates (AST), closed APIs, network reach, caching, held tensors, device handling. Prints counts; --json writes the detail; --write-data refreshes psn_nodes/tidy_data.json.
Run with ComfyUI's venv. It loads the pack without ComfyUI, so the V3 flagship nodes are checked by tests/test_v3_flagship.py and scripts/verify_nodes_cpu.py instead."""
import argparse, ast, collections, glob, hashlib, importlib.util, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET = {"urllib.request", "requests", "httpx", "aiohttp", "socket", "http.client", "websocket", "websockets", "boto3", "smtplib", "ftplib", "paramiko"}
NET_INTERNAL = ("psn.bridges", "psn.comfy_client", "psn.connectors", "psn.subagents")
CLOSED = re.compile(r"(api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis|api\.runwayml|higgsfield\.ai|api\.replicate\.com|api\.stability\.ai|api\.elevenlabs|fal\.run|api\.groq\.com|api\.together|api\.mistral|comfy\.org/api|api\.comfy\.org)", re.I)
STALE = re.compile(r"\b(time\.time|datetime\.now|datetime\.utcnow|random\.random|random\.randint|random\.choice|uuid\.uuid4|os\.listdir|os\.stat|glob\.glob)\b|\bopen\(")
def load_pack():
    spec = importlib.util.spec_from_file_location("psn_pack", os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT]); m = importlib.util.module_from_spec(spec); sys.modules["psn_pack"] = m; spec.loader.exec_module(m); return m
def strip_doc(body): return [b for b in body if not (isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant) and isinstance(b.value.value, str))]
def norm_class(node):
    """AST of a class without its name, docstrings and CATEGORY line, with the source's local names kept: same text means same behaviour."""
    parts = []
    for b in strip_doc(node.body):
        if isinstance(b, ast.Assign) and any(getattr(t, "id", "") == "CATEGORY" for t in b.targets): continue
        if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)): b = ast.parse(ast.unparse(b)).body[0]; b.body = strip_doc(b.body) or [ast.Pass()]
        parts.append(ast.dump(b, annotate_fields=False))
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()
def scan_module(path):
    src = open(path, encoding="utf-8").read(); tree = ast.parse(src); nets, funcs, classes = set(), {}, {}
    for st in ast.walk(tree):
        if isinstance(st, ast.Import):
            for a in st.names:
                if a.name in NET or a.name.split(".")[0] in NET or a.name.startswith(NET_INTERNAL): nets.add((a.asname or a.name).split(".")[0])
        elif isinstance(st, ast.ImportFrom) and st.module:
            full = "." * st.level + st.module
            if st.module in NET or st.module.split(".")[0] in NET or st.module.startswith(NET_INTERNAL) or (st.level and re.match(r"\.*psn\.(bridges|connectors|subagents|comfy_client)", full)):
                nets.update(a.asname or a.name for a in st.names)
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)): funcs[st.name] = st
        elif isinstance(st, ast.ClassDef): classes[st.name] = st
    def names(n): return {x.id for x in ast.walk(n) if isinstance(x, ast.Name)} | {x.attr for x in ast.walk(n) if isinstance(x, ast.Attribute)}
    reach = {f: names(n) for f, n in funcs.items()}; bad = set(f for f, ns in reach.items() if ns & nets); grew = True
    while grew:
        grew = False
        for f, ns in reach.items():
            if f not in bad and ns & bad: bad.add(f); grew = True
    info = {}
    for cname, cn in classes.items():
        text = ast.unparse(cn); ns = names(cn); fn_text = "".join(ast.unparse(funcs[f]) for f in ns if f in funcs)
        info[cname] = {"hash": norm_class(cn), "network": bool(ns & nets or ns & bad), "closed": sorted(set(m.group(0).lower() for m in CLOSED.finditer(text + fn_text))),
            "stale": bool(STALE.search(text + fn_text)), "is_changed": "IS_CHANGED" in {b.name for b in cn.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef))},
            "device": bool(re.search(r"\.cuda\(\)|\.to\(\s*['\"]cuda|torch\.device\(|\.to\(\s*\w*device\b", text + fn_text)), "uses_mm": "model_management" in src,
            "held": bool("torch" in src and re.search(r"^\s*(_?[A-Za-z_]*(cache|CACHE|store|STORE|memory|MEMORY|bank|BANK|history|HISTORY|registry|REGISTRY)[A-Za-z_]*)\s*(:\s*[\w\[\], ]+)?\s*=\s*(\{\}|\[\]|dict\(\)|OrderedDict\(\))", src, re.M))}
    return info
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); ap.add_argument("--write-data", action="store_true"); a = ap.parse_args()
    m = load_pack(); nodes = m.NODE_CLASS_MAPPINGS; disp = m.NODE_DISPLAY_NAME_MAPPINGS
    src = {}
    for path in glob.glob(os.path.join(ROOT, "psn_nodes", "**", "*.py"), recursive=True):
        rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
        try: src[rel] = scan_module(path)
        except SyntaxError: src[rel] = {}
    rows, counts, by_hash = {}, collections.Counter(), collections.defaultdict(list); sigs = collections.defaultdict(list)
    for nid, cls in sorted(nodes.items()):
        mod = cls.__module__.replace("psn_pack.", ""); s = src.get(mod, {}).get(cls.__name__, {}); r = {"module": mod, "class": cls.__name__, **{k: s.get(k) for k in ("network", "closed", "stale", "is_changed", "device", "uses_mm", "held")}}
        counts["registered"] += 1
        try: it = cls.INPUT_TYPES(); json.dumps(it); json.dumps(list(cls.RETURN_TYPES)); counts["serializes"] += 1
        except Exception as e: r["serialize_error"] = str(e)[:200]; counts["serialize_errors"] += 1; it = {}
        cat = getattr(cls, "CATEGORY", "") or ""; r["category"] = cat
        counts["category_in_tree"] += cat.startswith("Parametric/") and cat != "Parametric/Misc"; counts["category_misc"] += cat == "Parametric/Misc"; counts["has_display_name"] += bool(disp.get(nid)) and disp[nid] != nid; counts["has_description"] += bool(getattr(cls, "DESCRIPTION", ""))
        inputs = [(n, sp) for sec in ("required", "optional") for n, sp in (it.get(sec) or {}).items()]; counts["inputs"] += len(inputs); counts["inputs_with_tooltip"] += sum(1 for _, sp in inputs if len(sp) > 1 and isinstance(sp[1], dict) and sp[1].get("tooltip"))
        for k in ("network", "stale", "device", "held"): counts[f"{k}"] += bool(s.get(k))
        counts["closed_api"] += bool(s.get("closed")); counts["stale_without_is_changed"] += bool(s.get("stale") and not s.get("is_changed")); counts["device_without_model_management"] += bool(s.get("device") and not s.get("uses_mm")); counts["hidden_deprecated"] += bool(getattr(cls, "DEPRECATED", False))
        counts["network_undisclosed"] += bool(s.get("network") and not re.search(r"network|internet|online|http|api|webhook|url|remote|download|upload|server|bridge", getattr(cls, "DESCRIPTION", "") or "", re.I))
        if s.get("hash"): by_hash[s["hash"]].append(nid)
        sigs[(tuple(sorted((n, str(sp[0])[:40]) for n, sp in inputs)), tuple(map(str, cls.RETURN_TYPES)))].append(nid); rows[nid] = r
    dup_groups = [sorted(v) for v in by_hash.values() if len(v) > 1]; hidden = sorted(n for g in dup_groups for n in g[1:]); near = [sorted(v) for k, v in sigs.items() if len(v) > 1 and len(k[0]) >= 2 and not any(set(v) <= set(g) for g in dup_groups)]
    counts["exact_duplicate_groups"] = len(dup_groups); counts["exact_duplicates_to_hide"] = len(hidden); counts["same_signature_groups"] = len(near)
    report = {"counts": dict(sorted(counts.items())), "exact_duplicates": dup_groups, "same_signature_candidates": near, "load_errors": getattr(sys.modules.get("psn_pack.psn_nodes.gen"), "LOAD_ERRORS", {}), "closed_api": {k: v["closed"] for k, v in rows.items() if v.get("closed")}, "network": sorted(k for k, v in rows.items() if v.get("network")), "stale_without_is_changed": sorted(k for k, v in rows.items() if v.get("stale") and not v.get("is_changed")), "device_without_model_management": sorted(k for k, v in rows.items() if v.get("device") and not v.get("uses_mm")), "held": sorted(k for k, v in rows.items() if v.get("held")), "misc": sorted(k for k, v in rows.items() if v["category"] == "Parametric/Misc"), "serialize_errors": {k: v["serialize_error"] for k, v in rows.items() if v.get("serialize_error")}}
    if a.write_data: json.dump({"network": report["network"]}, open(os.path.join(ROOT, "psn_nodes", "tidy_data.json"), "w"), indent=0, sort_keys=True)
    if a.json: json.dump({**report, "nodes": rows}, open(a.json, "w"), indent=1, default=str)
    print(json.dumps(report["counts"], indent=0)); print("exact duplicate groups:", dup_groups[:12]); print("closed api:", list(report["closed_api"].items())[:12]); print("misc:", report["misc"][:20]); print("load errors:", report["load_errors"]); print("serialize errors:", report["serialize_errors"])
if __name__ == "__main__": main()
