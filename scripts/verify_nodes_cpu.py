#!/usr/bin/env python3
"""Start a throwaway ComfyUI with --cpu on an ephemeral port, from a temp folder, with this repo as its only custom node. Check every node registers and /object_info serializes, run CPU graphs through the flagship nodes, stop it.
Usage: scripts/verify_nodes_cpu.py [--comfy DIR] [--work DIR] [--out report.json]. Never touches a running ComfyUI and never uses the GPU (CUDA hidden)."""
from pathlib import Path
import argparse, asyncio, hashlib, importlib.util, json, os, re, signal, socket, subprocess, sys, tempfile, time, urllib.request, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
class Server:
    def __init__(self, comfy, work, extra=()):
        self.extra = list(extra); self.comfy, self.work, self.port = comfy, work, free_port(); self.base = f"http://127.0.0.1:{self.port}"; self.client = uuid.uuid4().hex
        for d in ("custom_nodes", "input", "output", "temp", "user"): os.makedirs(os.path.join(work, d), exist_ok=True)
        link = os.path.join(work, "custom_nodes", "comfyui_parametric_studio")
        if not os.path.islink(link): os.symlink(ROOT, link)
        self.log = os.path.join(work, "server.log")
    def start(self):
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        self.proc = subprocess.Popen([sys.executable, os.path.join(self.comfy, "main.py"), "--cpu", "--listen", "127.0.0.1", "--port", str(self.port), "--base-directory", self.work, "--disable-auto-launch", "--preview-method", "none"] + self.extra, cwd=self.work, env=env, stdout=open(self.log, "w"), stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(600):
            if self.proc.poll() is not None: raise RuntimeError(f"server exited {self.proc.returncode}, see {self.log}")
            try: urllib.request.urlopen(self.base + "/system_stats", timeout=2); return
            except Exception: time.sleep(0.5)
        raise RuntimeError("server did not answer in 300 s")
    def stop(self):
        self.proc.terminate()
        try: self.proc.wait(30)
        except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait(10)
    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=300) as r: return json.loads(r.read())
    async def run(self, graph, timeout=240):
        """Queue a graph and collect its websocket events until it ends."""
        import aiohttp
        events, ws_url = [], f"ws://127.0.0.1:{self.port}/ws?clientId={self.client}"
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(ws_url, max_msg_size=0) as ws:
                await ws.send_json({"type": "feature_flags", "data": {"supports_preview_metadata": True}}); binary = 0
                async with s.post(self.base + "/prompt", json={"prompt": graph, "client_id": self.client}) as r:
                    body = await r.json()
                    if r.status != 200: return {"rejected": body}
                pid = body["prompt_id"]; end = time.time() + timeout
                while time.time() < end:
                    try: m = await ws.receive(timeout=max(1, end - time.time()))
                    except asyncio.TimeoutError: break
                    binary += m.type == aiohttp.WSMsgType.BINARY
                    if m.type != aiohttp.WSMsgType.TEXT:
                        if m.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR): break
                        continue
                    e = json.loads(m.data); d = e.get("data") or {}
                    if d.get("prompt_id") not in (pid, None): continue
                    events.append(e)
                    if e["type"] == "executing" and d.get("node") is None and d.get("prompt_id") == pid: break
                    if e["type"] in ("execution_success", "execution_interrupted"): break
        hist = self.get(f"/history/{pid}").get(pid) or {}
        return {"binary_previews": binary, "events": events, "history": hist, "outputs": hist.get("outputs") or {}, "ran": [e["data"]["node"] for e in events if e["type"] == "executing" and e["data"].get("node")], "errors": [e["data"] for e in events if e["type"] == "execution_error"], "status": (hist.get("status") or {}).get("status_str")}
def card(text="x", number=1): return {"class_type": "PSN_ShotCard", "inputs": {"text": text, "number": number, "width": 128, "height": 72}}
def director(idea, move="dolly_in", **kw): kw = kw or ({"pace": "slow"} if move == "dolly_in" else {}); return {"class_type": "PSN_DirectorPrompt", "inputs": {"idea": idea, "camera": move, **{f"camera.{k}": v for k, v in kw.items()}, "shot": "wide", "lens": "auto", "lighting": "noir", "mood": "auto"}}
def shot_list(n, ids): return {"class_type": "PSN_ShotList", "inputs": {**{f"shots.shot_{i}": [ids[i], 0] for i in range(n)}, "render": "storyboard", "render.width": 128, "render.height": 72}}
class Checks:
    def __init__(self): self.rows = []
    def add(self, name, ok, detail=""): self.rows.append({"check": name, "ok": bool(ok), "detail": str(detail)[:600]}); print(("PASS " if ok else "FAIL ") + name + (f": {str(detail)[:300]}" if detail else ""), flush=True)
def expected_ids():
    """The node ids of the pack as ComfyUI will see them, from the source: V1 ids by loading the pack without comfy_api, plus the V3 ids in flagship.py."""
    code = f"import importlib.util,json,sys;r={ROOT!r};s=importlib.util.spec_from_file_location('psn_pack',r+'/__init__.py',submodule_search_locations=[r]);m=importlib.util.module_from_spec(s);sys.modules['psn_pack']=m;s.loader.exec_module(m);print('IDS'+json.dumps(sorted(m.NODE_CLASS_MAPPINGS)))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}, cwd=tempfile.gettempdir()).stdout
    ids = set(json.loads(out[out.index("IDS") + 3:].splitlines()[0]))
    src = open(os.path.join(ROOT, "psn_nodes", "flagship.py"), encoding="utf-8").read()
    return ids | set(re.findall(r'node_id="(PSN_\w+)"', src))
async def graphs(sv, c, work, classic=False, checkpoint=None):
    # Director Prompt: DynamicCombo control reaches the prompt
    r = await sv.run({"1": director("a boat at dawn", "orbit_left", arc="half", pace="slow"), "2": {"class_type": "PreviewAny", "inputs": {"source": ["1", 0]}}})
    text = "".join(r.get("outputs", {}).get("2", {}).get("text", [""])) if not r.get("rejected") else str(r)
    c.add("Director Prompt runs and its revealed controls reach the prompt", "half circle at a slow pace" in text and text.startswith("a boat at dawn. Wide shot."), text)
    r = await sv.run({"1": director("a boat at dawn", "locked"), "2": {"class_type": "PreviewAny", "inputs": {"source": ["1", 0]}}})
    text = "".join(r.get("outputs", {}).get("2", {}).get("text", [""])) if not r.get("rejected") else str(r)
    c.add("Director Prompt: a move with no controls also runs", "locked off" in text, text)
    r = await sv.run({"1": {"class_type": "PSN_RecastPrompt", "inputs": {"target": "the waiter", "direction": "", "video_ref": 2, "picture_ref": 1}}, "2": {"class_type": "PreviewAny", "inputs": {"source": ["1", 0]}}})
    text = "".join(r.get("outputs", {}).get("2", {}).get("text", [""])) if not r.get("rejected") else str(r)
    c.add("Recast Prompt runs with its reference tags", "Replace only the waiter in <Video 2> with the character in <Picture 1>" in text, text)
    # Shot List: expansion with cheap nodes, one card per shot, and only the changed shot renders again
    g = {"1": director("shot one"), "2": director("shot two"), "3": director("shot three"), "4": shot_list(3, ["1", "2", "3"]), "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "shots"}}, "6": {"class_type": "PreviewAny", "inputs": {"source": ["4", 1]}}}
    r = await sv.run(g); imgs = r.get("outputs", {}).get("5", {}).get("images", [])
    expanded = [n for n in r.get("ran", []) if n.startswith("4.")]
    c.add("Shot List expands into one subgraph per shot and joins them", len(imgs) == 3 and "".join(r["outputs"]["6"]["text"]) == "3" and not r["errors"], {"images": len(imgs), "expanded_nodes": expanded, "status": r.get("status"), "rejected": r.get("rejected")})
    g2 = json.loads(json.dumps(g)); g2["2"]["inputs"]["idea"] = "shot two, changed"
    r2 = await sv.run(g2); cards = [n for n in r2.get("ran", []) if n.startswith("4.")]
    hist_nodes = (r2.get("history", {}).get("prompt") or [None, None, {}])[2]
    c.add("Shot List: changing one shot still gives every image", len(r2.get("outputs", {}).get("5", {}).get("images", [])) == 3 and not r2["errors"], {"first_run_expanded": len(expanded), "second_run_ran": cards})
    if classic: c.add("Shot List with --cache-classic: changing one shot renders only that shot and the join", len(cards) == 2, cards)
    else: print(f"INFO default cache, changing one shot ran: {cards}", flush=True)
    # VRAM Gate: passes and blocks
    open_g = {"1": card("gate open"), "2": {"class_type": "PSN_VRAMGate", "inputs": {"value": ["1", 0], "peak_gb": 0.001, "margin_gb": 0.0, "free_idle_models": False}}, "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": "gate"}}, "4": {"class_type": "PreviewAny", "inputs": {"source": ["2", 2]}}}
    r = await sv.run(open_g); status = "".join(r.get("outputs", {}).get("4", {}).get("text", [""]))
    c.add("VRAM Gate passes when there is room", len(r.get("outputs", {}).get("3", {}).get("images", [])) == 1 and status.startswith("Open:") and not r["errors"], {"status": status, "rejected": r.get("rejected")})
    r_again = await sv.run(open_g)
    c.add("VRAM Gate: a passing gate does not make the graph run again", "1" not in r_again.get("ran", []) and "3" not in r_again.get("ran", []), {"ran": r_again.get("ran")})
    shut = json.loads(json.dumps(open_g)); shut["2"]["inputs"].update(peak_gb=900000.0, margin_gb=4.0, free_idle_models=True); shut["1"]["inputs"]["text"] = "gate shut"; shut["3"]["inputs"]["filename_prefix"] = "gate_shut"
    r = await sv.run(shut); msg = " ".join(str(e.get("exception_message")) for e in r.get("errors", []))
    saved = r.get("outputs", {}).get("3", {}).get("images", [])
    c.add("VRAM Gate blocks with a plain reason and nothing downstream saves", not saved and "Not enough free memory" in msg and "900004.0 GB" in msg and not os.path.exists(os.path.join(work, "output", "gate_shut_00001_.png")), {"reason": msg, "status": r.get("status"), "rejected": r.get("rejected")})
    r = await sv.run(shut); msg2 = " ".join(str(e.get("exception_message")) for e in r.get("errors", []))
    c.add("VRAM Gate says why every time, also on a second blocked run", "Not enough free memory" in msg2, msg2)
    # Latent Inspector: all three views, image and video, noise and flat
    for view, extra in (("channel_grid", {"columns": 0, "per_channel": True, "scale": 2}), ("pca_rgb", {"clip_percent": 1.0, "scale": 8}), ("histogram", {"bins": 32})):
        g = {"1": {"class_type": "EmptyLatentImage", "inputs": {"width": 256, "height": 256, "batch_size": 1}}, "2": {"class_type": "PSN_LatentNoiseInject", "inputs": {"latent": ["1", 0], "seed": 3, "strength": 1.0, "scale": 1, "octaves": 1}}, "3": {"class_type": "PSN_LatentInspector", "inputs": {"latent": ["2", 0], "view": view, **{f"view.{k}": v for k, v in extra.items()}, "batch_index": 0, "frame": 0}}, "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": f"inspect_{view}"}}, "5": {"class_type": "PreviewAny", "inputs": {"source": ["3", 1]}}}
        r = await sv.run(g); stats = "".join(r.get("outputs", {}).get("5", {}).get("text", [""])); ui = r.get("outputs", {}).get("3", {}).get("images", [])
        previews = [e for e in r.get("events", []) if e["type"] == "progress_state"]
        c.add(f"Latent Inspector {view}", len(r.get("outputs", {}).get("4", {}).get("images", [])) == 1 and "Reading:" in stats and len(ui) == 1 and r.get("binary_previews", 0) >= 1 and not r["errors"], {"stats_tail": stats.splitlines()[-1] if stats else None, "preview_on_node": len(ui), "progress_events": len(previews), "live_previews": r.get("binary_previews"), "errors": r.get("errors"), "rejected": r.get("rejected")})
    g = {"1": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": 64, "height": 64, "length": 9, "batch_size": 1}}, "2": {"class_type": "PSN_LatentInspector", "inputs": {"latent": ["1", 0], "view": "channel_grid", "view.columns": 0, "view.per_channel": True, "view.scale": 2, "batch_index": 0, "frame": 1}}, "3": {"class_type": "PreviewAny", "inputs": {"source": ["2", 1]}}}
    r = await sv.run(g); stats = "".join(r.get("outputs", {}).get("3", {}).get("text", [""]))
    c.add("Latent Inspector reads a 5D video latent", "16 channels" in stats and "flat" in stats, stats.splitlines()[0] if stats else r)
    # Graph Proof
    g = {"1": card("proof"), "2": {"class_type": "PSN_GraphProof", "inputs": {"filename_prefix": "proof/run", "images": ["1", 0], "note": "cpu check"}}}
    r = await sv.run(g); text = r.get("outputs", {}).get("2", {}).get("text", [""])[0]; digest, rel = (text.split("\n") + [""])[:2]
    path = os.path.join(work, "output", rel); ok = os.path.isfile(path); doc = json.load(open(path)) if ok else {}
    same = hashlib.sha256(json.dumps(doc.get("graph"), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest() == digest if ok else False
    c.add("Graph Proof writes a verifiable file with hash, settings and pixels", ok and same and doc.get("graph") == g and "pixels" in doc and doc["settings"]["1"]["values"]["text"] == "proof", {"path": rel, "hash": digest})
    r = await sv.run(g); again = r.get("outputs", {}).get("2", {}).get("text", [""])[0].split("\n")[0]
    c.add("Graph Proof: same graph, same hash, and it runs again", again == digest and "2" in r.get("ran", []), again)
    g3 = json.loads(json.dumps(g)); g3["1"]["inputs"]["number"] = 2
    r = await sv.run(g3); c.add("Graph Proof: a changed graph gets a new hash", r.get("outputs", {}).get("2", {}).get("text", [""])[0].split("\n")[0] != digest)
    if checkpoint: await sampler_graph(sv, c, checkpoint)
async def sampler_graph(sv, c, checkpoint):
    g = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}}, "2": director("a red cube"), "3": director("a blue sphere"),
         "4": {"class_type": "PSN_ShotList", "inputs": {"shots.shot_0": ["2", 0], "shots.shot_1": ["3", 0], "render": "sampler", "render.model": ["1", 0], "render.clip": ["1", 1], "render.vae": ["1", 2], "render.negative": "", "render.width": 64, "render.height": 64, "render.seed": 1, "render.steps": 1, "render.cfg": 1.0, "render.sampler_name": "euler", "render.scheduler": "normal"}},
         "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "sampler"}}}
    r = await sv.run(g, timeout=400); imgs = r.get("outputs", {}).get("5", {}).get("images", []); kinds = sorted({n.rsplit(".", 1)[0] for n in r.get("ran", []) if n.startswith("4.")})
    c.add("Shot List sampler mode renders one real image per shot through forwarded links", len(imgs) == 2 and not r.get("errors") and r.get("status") == "success", {"images": len(imgs), "expanded": [n for n in r.get("ran", []) if n.startswith("4.")], "errors": r.get("errors"), "rejected": r.get("rejected"), "checkpoint": checkpoint})
def main():
    ap = argparse.ArgumentParser(); sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); from psn import paths; ap.add_argument("--comfy", default=paths.setting("COMFYUI_PATH", default=paths.home("ComfyUI"))); ap.add_argument("--work"); ap.add_argument("--out"); ap.add_argument("--cache-classic", action="store_true"); ap.add_argument("--checkpoint", help="a small checkpoint name: also runs Shot List in sampler mode, 1 step at 64x64 on the CPU"); a = ap.parse_args()
    work = a.work or tempfile.mkdtemp(prefix="psn_cpu_"); c = Checks(); sv = Server(a.comfy, work, ["--cache-classic"] if a.cache_classic else []); t0 = time.time(); report = {}
    try:
        sv.start(); started = time.time() - t0; info = sv.get("/object_info"); log = open(sv.log, errors="replace").read()
        report.update(port=sv.port, work=work, startup_seconds=round(started, 1), object_info_nodes=len(info)); json.dumps(info)
        m = re.search(r"([\d.]+) seconds(?: \(IMPORT FAILED\))?: \S*comfyui_parametric_studio", log); report["pack_import_seconds_in_comfyui"] = float(m.group(1)) if m else None
        expected = expected_ids(); missing = sorted(expected - set(info)); psn = [k for k in info if (info[k].get("python_module") or "").endswith("comfyui_parametric_studio")]
        report.update(expected=len(expected), pack_nodes_in_object_info=len(psn), missing=missing[:40])
        c.add("every pack node registered and serialized in /object_info", not missing and "IMPORT FAILED" not in log, {"expected": len(expected), "in_object_info": len(psn), "missing": missing[:10]})
        others = sorted({(info[k].get("python_module") or "") for k in info if (info[k].get("python_module") or "").startswith("custom_nodes.")}); c.add("this repo is the only custom node", others == ["custom_nodes.comfyui_parametric_studio"], others)
        errs = re.findall(r"An error occurred while retrieving information for the (\S+)", log); c.add("no node failed to serialize", not errs, errs[:10])
        v3 = info.get("PSN_ShotList", {}); c.add("V3 schema reaches the client", v3.get("input", {}).get("required", {}).get("shots", [""])[0] == "COMFY_AUTOGROW_V3" and info["PSN_VRAMGate"]["output_matchtypes"][0] == "value" and info["PSN_DirectorPrompt"]["input"]["required"]["camera"][0] == "COMFY_DYNAMICCOMBO_V3")
        asyncio.run(graphs(sv, c, work, a.cache_classic, a.checkpoint)); report["checks"] = c.rows
    finally:
        sv.stop(); report["stopped"] = sv.proc.poll() is not None
    bad = [r for r in c.rows if not r["ok"]]; report.update(passed=len(c.rows) - len(bad), failed=len(bad))
    if a.out: json.dump(report, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "checks"})); return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
