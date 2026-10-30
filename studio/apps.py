"""ComfyUI Apps: a ComfyUI app is an ordinary workflow whose `extra` holds linearMode=true and linearData={inputs:[[node, widget],...], outputs:[node,...]} (what the frontend's Build app picks).
This module lists such apps (the installed template package, ~/comfy_apps, $STUDIO_APPS), turns the exposed inputs into a form description, checks that the model files they need exist on this box, and runs them
through the same ComfyUI queue as everything else. Nothing here edits a workflow file."""
import ast, glob, json, os, re, time, urllib.request
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from psn import paths
from studio import sfw
from studio.ui2api import ui_to_api
COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/")
def _dirs():
    out = []
    try:
        import comfyui_workflow_templates_json as t; out.append(os.path.join(os.path.dirname(t.__file__), "templates"))
    except Exception: pass
    out += [os.path.expanduser("~/comfy_apps")] + [d for d in os.environ.get("STUDIO_APPS", "").split(":") if d]
    return [d for d in out if os.path.isdir(d)]
_oi = {"t": 0, "d": None}
def object_info():
    if _oi["d"] is None or time.time() - _oi["t"] > 120: _oi["d"] = json.load(urllib.request.urlopen(COMFY + "/object_info", timeout=60)); _oi["t"] = time.time()
    return _oi["d"]
def _is_app(d): return isinstance(d, dict) and (d.get("extra") or {}).get("linearMode") is True and (d["extra"].get("linearData") or {}).get("inputs") is not None
def open_edition(): return os.environ.get("PSN_EDITION", "open") != "extended"      # EDITIONS.md: the open edition has no partner nodes and no closed APIs
def partner_types(ui, oi):
    """Node types in a workflow that /object_info flags api_node: ComfyUI's partner nodes, which call closed paid APIs."""
    nodes = list(ui.get("nodes", [])) + [n for sg in (ui.get("definitions", {}).get("subgraphs") or []) for n in sg.get("nodes", [])]
    return sorted({n["type"] for n in nodes if isinstance(n.get("type"), str) and (oi.get(n["type"]) or {}).get("api_node")})
def find_apps(oi=None):
    """The apps this edition offers: in the open edition, a workflow that uses a partner node is left out."""
    apps = {}
    if oi is None and open_edition():
        try: oi = object_info()
        except Exception: oi = {}
    for d in _dirs():
        for f in glob.glob(os.path.join(d, "*.app.json")) + (glob.glob(os.path.join(d, "*.json")) if "comfy_apps" in d or d in os.environ.get("STUDIO_APPS", "") else []):
            aid = re.sub(r"\.app$", "", os.path.basename(f)[:-5])
            if aid in apps: continue
            try: ui = json.load(open(f))
            except Exception: continue
            if _is_app(ui) and not (open_edition() and partner_types(ui, oi or {})): apps[aid] = f
    if not open_edition():      # extended edition: ComfyUI's partner workflows as forms; they spend the user's own Comfy credits
        try:
            import comfyui_workflow_templates_json as T
            for f in glob.glob(os.path.join(os.path.dirname(T.__file__), "**", "api_*.json"), recursive=True): apps.setdefault(os.path.basename(f)[:-5], f)
        except Exception: pass
    return apps
def _title(aid): return re.sub(r"^(templates?[-_]|utility[-_])", "", aid).replace("_", " ").replace("-", " ").strip().capitalize()
def _spec(oi, cls, name):
    info = oi.get(cls, {}).get("input", {}); return (info.get("required") or {}).get(name) or (info.get("optional") or {}).get(name)
MODEL_FILE = re.compile(r"\.(safetensors|ckpt|pt|pth|gguf|bin|onnx)$")
VARIANT = re.compile(r"^(base|distilled|turbo|lightning|t2v|i2v|ti2v|v2v|t2i|fl2v|fl2va|ref2v|ref2va|high|low|inpaint|control|camera|vace|fun|\d+(\.\d+)?b|\d+step)$")
def variants(name):
    """The tokens of a model file name that make it a different model (T2V or I2V, high or low noise, 14B or 5B, 4 or 8 steps); precision and resolution tags are not among them."""
    from studio.names import norm
    return {t for t in re.split(r"[^a-z0-9.]+", norm(name)) if VARIANT.match(t)}
def variant_ok(was, now):
    from studio.names import norm
    return norm(was) == norm(now) or variants(was) == variants(now)
def resolve(g, oi):
    """names.resolve_names (a file kept in a sub-folder or under a close name is not missing), minus close names that are another variant of the model: those stay as written, so they still show as missing. -> (graph, report)"""
    from studio.names import resolve_names
    g, rep = resolve_names(g, oi)
    for r in rep:
        if r["now"] is not None and not variant_ok(r["was"], r["now"]): g[r["node"]]["inputs"][r["input"]] = r["was"]; r["now"] = None
    return g, rep
def model_refs(g, oi):
    """Every model file name a graph loads, as written (before resolve)."""
    return sorted({v for n in g.values() for k, v in n["inputs"].items() if isinstance(v, str) and MODEL_FILE.search(v) and isinstance(options_of(oi, n["class_type"], k), list)})
def options_of(oi, cls, name):
    sp = _spec(oi, cls, name)
    if not sp: return None
    return sp[0] if isinstance(sp[0], list) else (sp[1].get("options") if len(sp) > 1 and isinstance(sp[1], dict) else None)
def _targets(ex, nid, w, g):
    lst = [x for x in ex.get((str(nid), w), []) if x[0] in g]
    return [x for x in lst if ":" not in x[0]] or lst         # a top-level node wins over an inner node that happens to share its id
NEG = re.compile(r"worst quality|low quality|blurry|jpeg artifacts|watermark", re.I)
def linear_inputs(ui):
    ld = (ui.get("extra") or {}).get("linearData")
    return [tuple(x) for x in ld["inputs"]] if ld and ld.get("inputs") is not None else None
def infer_inputs(ui):
    """For a plain template (no app data): the controls its author promoted (sub-graph proxy widgets) plus its loaders and positive prompt nodes. Same idea as ComfyUI's Build app, done automatically."""
    subs = {s["id"] for s in (ui.get("definitions", {}).get("subgraphs") or [])}; out = []
    for n in ui.get("nodes", []):
        if n.get("mode") in (2, 4): continue
        t, nid = n["type"], n["id"]
        if t == "LoadImage": out.append((nid, "image"))
        elif t == "LoadVideo": out.append((nid, "file"))
        elif t in ("CLIPTextEncode", "PrimitiveString", "PrimitiveStringMultiline"):
            txt = (n.get("widgets_values") or [""])[0]
            if "negative" in str(n.get("title", "")).lower() or (isinstance(txt, str) and NEG.search(txt)): continue
            out.append((nid, "text" if t == "CLIPTextEncode" else "value"))
        elif t in subs:
            proxy = (n.get("properties") or {}).get("proxyWidgets") or []
            if isinstance(proxy, str):
                try: proxy = ast.literal_eval(proxy)
                except Exception: proxy = []
            for pr in proxy:
                if pr and len(pr) >= 2 and str(pr[0]) == "-1" and pr[1] in ("text", "prompt", "value", "image", "video", "seed", "duration", "strength", "steps", "length", "width", "height"): out.append((nid, pr[1]))
    seen, res = set(), []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res[:10]
def describe(aid, path, oi):
    ui = json.load(open(path)); ex = {}; g, probs = ui_to_api(ui, oi, ex); models = model_refs(g, oi); g, _rep = resolve(g, oi); ld = (ui.get("extra") or {}).get("linearData") or {}; nodes = {str(n["id"]): n for n in ui.get("nodes", [])}; inputs = []
    all_ids = {str(n["id"]) for n in ui.get("nodes", [])} | {str(n["id"]) for sg in (ui.get("definitions", {}).get("subgraphs") or []) for n in sg.get("nodes", [])}
    for nid, w in (linear_inputs(ui) if linear_inputs(ui) is not None else infer_inputs(ui)):
        if str(nid) not in all_ids: continue                       # stale reference to a deleted node: the ComfyUI frontend prunes these too
        tg = _targets(ex, nid, w, g); node = nodes.get(str(nid), {}); title = node.get("title") or node.get("type", "")[:24]
        if not ex.get((str(nid), w)) is None and not tg and ex.get((str(nid), w)): continue      # the input exists but feeds nothing that runs: leave it out of the form
        if not tg: inputs.append({"key": f"{nid}|{w}", "label": f"{title}: {w}", "type": "unsupported"}); continue
        an, inp = tg[0]; cls = g[an]["class_type"]; spec = _spec(oi, cls, inp); typ = "text"; opts = None
        if spec:
            t0 = spec[0]
            if isinstance(t0, list): typ, opts = "choice", t0
            elif t0 == "COMBO": typ, opts = "choice", (spec[1] or {}).get("options")
            elif t0 in ("INT", "FLOAT"): typ = "number"
            elif t0 == "BOOLEAN": typ = "bool"
            if inp == "image" or cls in ("LoadImage", "LoadImageMask"): typ = "image"
            if cls == "LoadVideo": typ = "video"
        inputs.append({"key": f"{nid}|{w}", "label": f"{title}: {w}".replace("_", " "), "type": typ, "options": opts if opts and len(opts) < 300 else None, "default": g[an]["inputs"].get(inp)})
    missing = sorted({v for n in g.values() for k, v in n["inputs"].items() if isinstance(v, str) and MODEL_FILE.search(v) and isinstance(options_of(oi, n["class_type"], k), list) and v not in options_of(oi, n["class_type"], k)})
    ok = not [p for p in probs] and not any(i["type"] == "unsupported" for i in inputs)
    unknown = sorted({m.group(1) for pr in probs for m in [re.search(r"unknown node type (\S+)", pr)] if m})
    hints = model_hints(ui)
    return {"id": aid, "title": _title(aid), "inputs": inputs, "outputs": len(ld.get("outputs", [])) or sum(1 for n in g.values() if oi.get(n["class_type"], {}).get("output_node")), "nodes": len(g), "runnable": ok and not missing, "ready": ok, "problems": probs[:4], "missing_models": missing[:8],
            "downloads": [{"name": n, **hints[n]} for n in missing if n in hints][:8], "unknown_nodes": unknown, "models": models, "hints": {n: hints[n] for n in models if n in hints}}
def build_graph(path, values, oi):
    ui = json.load(open(path)); ex = {}; g, probs = ui_to_api(ui, oi, ex); g, _rep = resolve(g, oi)
    if probs: raise ValueError("this app uses features the converter cannot run yet: " + probs[0])
    for key, val in (values or {}).items():
        nid, w = key.split("|", 1); tg = _targets(ex, nid, w, g)
        if not tg: raise ValueError(f"unknown input {key}")
        for an, inp in tg: g[an]["inputs"][inp] = val
    for n in g.values():      # these widgets are dynamic in the UI format, so the converter cannot see them; every save node needs them
        if n.get("class_type") == "SaveVideo": n["inputs"].setdefault("format", "auto"); n["inputs"].setdefault("codec", "auto")
        elif n.get("class_type") == "SaveAudioAdvanced": n["inputs"].setdefault("format", "flac")
    return g
def template_dir():
    """The folder of ComfyUI's official templates in this Python, or None."""
    try:
        import comfyui_workflow_templates_json as t; d = os.path.join(os.path.dirname(t.__file__), "templates"); return d if os.path.isdir(d) else None
    except Exception: return None
def fill_dynamic(graph, oi):
    """V3 dynamic combos (SaveVideo.format, SaveImageAdvanced.format, ...) are widgets the template converter does not carry: set the first option and its nested inputs to their defaults, under both the dotted name the server reads and the plain name API graphs use. Drops ImageCompare (a viewer). -> number of inputs set."""
    fixed = 0
    for nid in [k for k, n in graph.items() if n["class_type"] == "ImageCompare"]: del graph[nid]
    def one(ins, name, spec, prefix):
        nonlocal fixed
        opts = (spec[1] or {}).get("options") or []; keys = [o["key"] for o in opts]; key = prefix + name
        cur = ins.get(key, ins.get(name)) if not prefix else ins.get(key)
        if cur not in keys: cur = (spec[1] or {}).get("default") if (spec[1] or {}).get("default") in keys else (keys[0] if keys else None); fixed += 1
        if cur is None: return
        ins[key] = cur
        if not prefix: ins[name] = cur
        sel = next((o for o in opts if o["key"] == cur), {}); nested = {**((sel.get("inputs") or {}).get("required") or {}), **((sel.get("inputs") or {}).get("optional") or {})}
        for nn, ns in nested.items():
            if ns[0] == "COMFY_DYNAMICCOMBO_V3":
                one(ins, nn, ns, key + ".")
                if (key + "." + nn) in ins: ins.setdefault(nn, ins[key + "." + nn])
            else:
                o2 = (ns[1] or {}) if len(ns) > 1 else {}; dv = o2.get("default", (ns[0][0] if isinstance(ns[0], list) and ns[0] else (o2.get("options") or [None])[0]))
                ins.setdefault(key + "." + nn, dv); ins.setdefault(nn, ins[key + "." + nn])
    for n in graph.values():
        info = oi.get(n["class_type"], {}).get("input", {})
        for grp in ("required", "optional"):
            for name, spec in (info.get(grp) or {}).items():
                if spec and spec[0] == "COMFY_DYNAMICCOMBO_V3" and (grp == "required" or name in n["inputs"]): one(n["inputs"], name, spec, "")
    return fixed
REGISTRY = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/extension-node-map.json"
def model_hints(ui):
    """{file name: {url, directory}} from the `properties.models` ComfyUI templates attach to their nodes."""
    out = {}
    nodes = list(ui.get("nodes", [])) + [n for sg in (ui.get("definitions", {}).get("subgraphs") or []) for n in sg.get("nodes", [])]
    for n in nodes:
        for m in (n.get("properties") or {}).get("models") or []:
            if m.get("name") and str(m.get("url", "")).startswith("https://huggingface.co/"): out[m["name"]] = {"url": m["url"], "directory": m.get("directory") or ""}
    return out
def resolve_packs(types, registry=None):
    """Map unknown node type names to the GitHub pack that provides them, from ComfyUI-Manager's public node map. {type: repo_url or None}."""
    try: reg = registry if registry is not None else json.load(urllib.request.urlopen(urllib.request.Request(REGISTRY, headers={"User-Agent": "psn-studio"}), timeout=30))
    except Exception: return {t: None for t in types}
    out = {t: None for t in types}
    for repo, val in reg.items():
        for t in val[0] if val and isinstance(val[0], list) else []:
            if t in out and out[t] is None: out[t] = repo
    return out
def fetch_models(aid, path, oi, confirm=False, downloader=None):
    """Download the model files an app is missing (from the HF URLs its template lists) into the models library. Needs confirm=True; each file is checked against the hash HF reports."""
    if not confirm: raise ValueError("downloads need confirm=true")
    ui = json.load(open(path)); d = describe(aid, path, oi); hints = model_hints(ui); done = []
    from psn.connectors.net import download
    for name in d["missing_models"]:
        h = hints.get(name)
        if not h: continue
        dest = os.path.join(paths.models_root(True), h["directory"] or "other", name); sha = None
        try:
            req = urllib.request.Request(h["url"], method="HEAD", headers={"User-Agent": "psn-studio"})
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *a, **k): return None
            try: urllib.request.build_opener(NoRedirect).open(req, timeout=20)
            except urllib.error.HTTPError as e: sha = (e.headers.get("X-Linked-Etag") or "").strip('"') or None
        except Exception: pass
        (downloader or download)(h["url"], dest, sha256=sha if sha and len(sha) == 64 else None); done.append(dest)
    return done
router = APIRouter()
class Run(BaseModel): values: dict = {}
@router.get("/api/apps")
def apps_list():
    try: oi = object_info()
    except Exception: raise HTTPException(503, "ComfyUI is not reachable") from None
    out = []
    for aid, path in sorted(find_apps().items()):
        try: d = describe(aid, path, oi); out.append({k: d[k] for k in ("id", "title", "runnable", "missing_models", "outputs", "nodes")} | {"inputs": len(d["inputs"])})
        except Exception: continue
    return {"apps": out}
@router.get("/api/apps/{aid}")
def apps_get(aid: str):
    p = find_apps().get(aid)
    if not p: raise HTTPException(404, "no such app")
    return describe(aid, p, object_info())
@router.post("/api/apps/{aid}/fetch-models")
def apps_fetch(aid: str, b: dict):
    p = find_apps().get(aid)
    if not p: raise HTTPException(404, "no such app")
    from psn.connectors.net import ConnectorError
    try: return {"saved": fetch_models(aid, p, object_info(), confirm=bool(b.get("confirm")))}
    except (ValueError, ConnectorError) as e: raise HTTPException(400, str(e)) from None
@router.get("/api/apps/{aid}/packs")
def apps_packs(aid: str):
    p = find_apps().get(aid)
    if not p: raise HTTPException(404, "no such app")
    d = describe(aid, p, object_info()); return {"unknown_nodes": d["unknown_nodes"], "packs": resolve_packs(d["unknown_nodes"]) if d["unknown_nodes"] else {}}
@router.post("/api/apps/{aid}/run")
def apps_run(aid: str, b: Run):
    p = find_apps().get(aid)
    if not p: raise HTTPException(404, "no such app")
    sfw.check(*b.values.values())
    try: g = build_graph(p, b.values, object_info())
    except ValueError as e: raise HTTPException(400, str(e)) from None
    try: r = urllib.request.urlopen(urllib.request.Request(COMFY + "/prompt", json.dumps({"prompt": g, "client_id": "studio-apps", **({"extra_data": {"api_key_comfy_org": os.environ["COMFY_API_KEY"]}} if not open_edition() and os.environ.get("COMFY_API_KEY") else {})}).encode(), {"Content-Type": "application/json"}), timeout=30)
    except Exception as e: raise HTTPException(502, f"ComfyUI refused the graph: {str(e)[:120]}") from None
    return {"job": json.loads(r.read())["prompt_id"]}
