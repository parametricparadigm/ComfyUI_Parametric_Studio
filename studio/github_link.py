"""GitHub connection. Read side (no login needed): find community ComfyUI workflows/apps, list a repo's .json files, import one into ~/comfy_apps after a SFW scan. Write side (needs GITHUB_TOKEN in the environment,
never stored or printed): publish your own apps or a built site to YOUR repo. Every write needs confirm=True; nothing is ever pushed automatically. Also: 'is a newer version of this studio out?' (read-only)."""
import base64, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
API = "https://api.github.com"; RAW = "https://raw.githubusercontent.com"
BAD = re.compile(r"\b(nsfw|nude|naked|lingerie|porn|hentai|explicit|erotic|topless|fetish|onlyfans|sex\w*)\b", re.I)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}$"); PATH_RE = re.compile(r"^[\w./ -]{1,200}$")
class GitHubError(RuntimeError): pass
def _req(url, token=None, method="GET", body=None, timeout=25, opener=None):
    h = {"User-Agent": "parametric-studio", "Accept": "application/vnd.github+json"}
    if token: h["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    try:
        with (opener or urllib.request.urlopen)(urllib.request.Request(url, data=data, headers=h, method=method), timeout=timeout) as r: return json.loads(r.read(8_000_000) or b"{}")
    except urllib.error.HTTPError as e:
        raise GitHubError(f"GitHub said {e.code}" + (" (rate limit: wait a minute, or set GITHUB_TOKEN for a higher limit)" if e.code in (403, 429) else " (not found or no access)" if e.code == 404 else "")) from None
    except (urllib.error.URLError, ValueError) as e: raise GitHubError(f"could not reach GitHub: {type(e).__name__}") from None
def search(query, limit=12, opener=None):
    q = urllib.parse.urlencode({"q": f"{query} in:name,description,topics comfyui", "sort": "stars", "per_page": min(limit, 30)}); d = _req(f"{API}/search/repositories?{q}", opener=opener)
    return [{"repo": r["full_name"], "stars": r["stargazers_count"], "license": (r.get("license") or {}).get("spdx_id") or "none declared", "pushed": (r.get("pushed_at") or "")[:10], "description": (r.get("description") or "")[:140], "url": r["html_url"]} for r in d.get("items", []) if not BAD.search((r.get("description") or "") + r["full_name"])]
def list_json(repo, path="", opener=None):
    if not REPO_RE.match(repo) or (path and not PATH_RE.match(path)) or ".." in path: raise GitHubError("that repository or path does not look right")
    d = _req(f"{API}/repos/{repo}/contents/{urllib.parse.quote(path)}", opener=opener)
    return [{"path": x["path"], "size": x.get("size", 0)} for x in (d if isinstance(d, list) else []) if x.get("type") == "file" and x["name"].lower().endswith(".json") and x.get("size", 0) <= 5_000_000]
def scan_sfw(text):
    return sorted({m.group(0).lower() for m in BAD.finditer(text)})
def import_file(repo, path, dest_dir, confirm=False, opener=None, ref="HEAD"):
    if not confirm: raise GitHubError("importing needs confirm=true")
    if not REPO_RE.match(repo) or not PATH_RE.match(path) or ".." in path or not path.lower().endswith(".json"): raise GitHubError("only .json files from a valid repository can be imported")
    url = f"{RAW}/{repo}/{ref}/{urllib.parse.quote(path)}"
    try:
        with (opener or urllib.request.urlopen)(urllib.request.Request(url, headers={"User-Agent": "parametric-studio"}), timeout=25) as r: text = r.read(5_000_001).decode("utf-8", "replace")
    except Exception as e: raise GitHubError(f"could not download it: {type(e).__name__}") from None
    if len(text) > 5_000_000: raise GitHubError("file over 5 MB")
    try: json.loads(text)
    except ValueError: raise GitHubError("that file is not valid JSON") from None
    flagged = scan_sfw(text)
    if flagged: raise GitHubError("not imported: this studio is safe-for-work and the file contains " + ", ".join(flagged))
    out = Path(dest_dir); out.mkdir(parents=True, exist_ok=True); name = re.sub(r"[^\w.-]+", "_", repo.replace("/", "__") + "__" + Path(path).name)[:140]; (out / name).write_text(text); return str(out / name)
def publish(repo, files, message, confirm=False, token=None, opener=None):
    """files: {repo_path: text}. Creates or updates each file in YOUR repo with the Contents API. Needs confirm and a token (env GITHUB_TOKEN)."""
    token = token or os.environ.get("GITHUB_TOKEN")
    if not confirm: raise GitHubError("publishing needs confirm=true: nothing is pushed unless you ask")
    if not token: raise GitHubError("set GITHUB_TOKEN (a token with repo access) in the environment first")
    if not REPO_RE.match(repo) or not files or len(files) > 50: raise GitHubError("a valid repository and 1 to 50 files are required")
    done = []
    for path, text in files.items():
        if not PATH_RE.match(path) or ".." in path or path.startswith("/") or path.split("/")[0] == ".github": raise GitHubError(f"refusing path {path!r}")
        if scan_sfw(text): raise GitHubError(f"{path} is not safe-for-work")
        sha = None
        try: sha = _req(f"{API}/repos/{repo}/contents/{urllib.parse.quote(path)}", token, opener=opener).get("sha")
        except GitHubError: pass
        body = {"message": (message or "Update from Parametric Studio")[:200], "content": base64.b64encode(text.encode()).decode()}
        if sha: body["sha"] = sha
        _req(f"{API}/repos/{repo}/contents/{urllib.parse.quote(path)}", token, "PUT", body, opener=opener); done.append(path)
    return done
def latest_version(repo, opener=None):
    try: d = _req(f"{API}/repos/{repo}/releases/latest", opener=opener); return {"tag": d.get("tag_name"), "url": d.get("html_url")}
    except GitHubError: return {"tag": None, "url": None}
router = APIRouter()
class Imp(BaseModel): repo: str; path: str; confirm: bool = False
class Pub(BaseModel): repo: str; files: dict; message: str = ""; confirm: bool = False
def _wrap(fn, *a, **k):
    try: return fn(*a, **k)
    except GitHubError as e: raise HTTPException(400, str(e)) from None
@router.get("/api/github/search")
def gh_search(q: str = "workflow"): return {"repos": _wrap(search, q)}
@router.get("/api/github/files")
def gh_files(repo: str, path: str = ""): return {"files": _wrap(list_json, repo, path)}
@router.post("/api/github/import")
def gh_import(b: Imp): return {"saved": _wrap(import_file, b.repo, b.path, os.path.expanduser("~/comfy_apps"), b.confirm)}
@router.post("/api/github/publish")
def gh_publish(b: Pub): return {"published": _wrap(publish, b.repo, b.files, b.message, b.confirm)}
@router.get("/api/github/status")
def gh_status(): return {"token_set": bool(os.environ.get("GITHUB_TOKEN")), "note": "Reading is public. Publishing needs GITHUB_TOKEN set on this machine; the token is never shown or stored by the studio."}
