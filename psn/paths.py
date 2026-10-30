"""Where things live on this machine, so that nothing box-specific sits in the code. Order for every setting: an environment variable; this machine's settings file (KEY=value lines, $PSN_SETTINGS or ~/.config/parametric-studio/settings.env);
what the running ComfyUI reports, where it can tell us; a default under the home folder. ComfyUI is only asked when a caller says discover=True, never on import. Standard library only."""
import json, os, time, urllib.request
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def home(*parts): return os.path.join(os.path.expanduser("~"), *parts)
_file = {"path": None, "mtime": None, "data": {}}
def _settings():
    p = os.environ.get("PSN_SETTINGS") or home(".config", "parametric-studio", "settings.env")
    try: mt = os.path.getmtime(p)
    except OSError: return {}
    if _file["path"] != p or _file["mtime"] != mt:
        data = {}
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip(); line = line[7:] if line.startswith("export ") else line
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); data[k.strip()] = os.path.expanduser(v.strip().strip("\"'"))
        _file.update(path=p, mtime=mt, data=data)
    return _file["data"]
def setting(*names, default=""):
    """The first of these names that has a value in the environment, then in the settings file; otherwise the default."""
    for n in names:
        if os.environ.get(n): return os.environ[n]
    s = _settings()
    for n in names:
        if s.get(n): return s[n]
    return default
_asked = {"t": 0.0, "d": None}
def ask_comfy(timeout=2):
    """{'models', 'output', 'input'} as the running ComfyUI reports them: folders from its command line (/system_stats) and its model folders (/internal/folder_paths). {} when it cannot be reached. Cached for a minute."""
    if _asked["d"] is not None and time.time() - _asked["t"] < 60: return _asked["d"]
    url, out = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8200").rstrip("/"), {}
    try:
        argv = (json.load(urllib.request.urlopen(url + "/system_stats", timeout=timeout)).get("system") or {}).get("argv") or []
        flag = lambda name: argv[argv.index(name) + 1] if name in argv[:-1] else ""
        if flag("--output-directory"): out["output"] = flag("--output-directory")
        if flag("--input-directory"): out["input"] = flag("--input-directory")
        try: ck = json.load(urllib.request.urlopen(url + "/internal/folder_paths", timeout=timeout)).get("checkpoints") or []
        except Exception: ck = []
        if ck: out["models"] = os.path.dirname(ck[0])
        base = flag("--base-directory") or (os.path.dirname(out["models"]) if "models" in out else "")
        if base: out.setdefault("output", os.path.join(base, "output")); out.setdefault("input", os.path.join(base, "input"))
    except Exception: pass
    _asked.update(t=time.time(), d=out); return out
def _found(key, discover): return ask_comfy().get(key, "") if discover else ""
def models_root(discover=False): return setting("STUDIO_MODELS_ROOT", "PSN_MODELS_ROOT") or _found("models", discover) or home("ComfyUI", "models")
def output_dir(discover=False): return setting("STUDIO_OUTPUT_DIR") or _found("output", discover) or home("ComfyUI", "output")
def comfy_input(discover=False): return setting("STUDIO_COMFY_INPUT") or _found("input", discover) or home("ComfyUI", "input")
def kb_root(): return setting("PSN_KB_ROOT", "STUDIO_KB", default=os.path.join(REPO, "studio", "crew_notes"))
