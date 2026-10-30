"""Portable model names: a workflow written on one box names its model files the way that box lays them out; on another box the same files sit in different sub-folders or carry a slightly different name.
resolve_names() rewrites each combo value that is not installed to the closest installed name (a close match only; anything else is reported, never guessed). Works on API-format graphs with object_info."""
import difflib, re
SUBSTITUTE = {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors", "minimax_music3_text_encoder_pruned_int8_convrot.safetensors": "minimax_music3_text_encoder_pruned_bf16.safetensors", "minimax_music3_text_encoder_pruned_bf16.safetensors": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"}
def norm(s): return re.sub(r"[^a-z0-9.]+", "_", str(s).lower().split("/")[-1])
def resolve_names(graph, oi, threshold=0.86):
    """-> (graph, report) where report = [{node, input, was, now, score}] for changes and [{... 'now': None}] for values with no close match. The graph is modified in place."""
    report = []
    for nid, n in graph.items():
        info = oi.get(n["class_type"], {}).get("input", {}); req = {**(info.get("required") or {}), **(info.get("optional") or {})}
        for k, v in list(n["inputs"].items()):
            spec = req.get(k)
            if not spec or not isinstance(v, str) or "${" in v: continue
            opts = spec[0] if isinstance(spec[0], list) else (spec[1].get("options") if len(spec) > 1 and isinstance(spec[1], dict) else None)
            if not opts or v in opts: continue
            if not re.search(r"\.(safetensors|ckpt|pt|pth|gguf|bin|onnx)$", v): continue
            if SUBSTITUTE.get(v) in opts: n["inputs"][k] = SUBSTITUTE[v]; report.append({"node": nid, "input": k, "was": v, "now": SUBSTITUTE[v], "score": 1.0}); continue
            best = max(opts, key=lambda o: difflib.SequenceMatcher(None, norm(v), norm(o)).ratio()); r = difflib.SequenceMatcher(None, norm(v), norm(best)).ratio()
            if r >= threshold: n["inputs"][k] = best; report.append({"node": nid, "input": k, "was": v, "now": best, "score": round(r, 2)})
            else: report.append({"node": nid, "input": k, "was": v, "now": None, "score": round(r, 2)})
    return graph, report
