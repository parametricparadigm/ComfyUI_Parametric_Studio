"""Civitai catalogue connector (public REST API, https://developer.civitai.com/site/). Search is anonymous; downloads need the owner's token in CIVITAI_TOKEN (sent as a header).
SFW only: nsfw=false is always sent and any item the API flags nsfw/minor/poi is dropped. Only .safetensors files whose pickle scan did not fail are offered."""
import os, urllib.parse
from psn.connectors.net import get_json, download, ConnectorError
BASE = "https://civitai.com/api/v1"

def _files(version):
    out = []
    for f in version.get("files") or []:
        fmt = ((f.get("metadata") or {}).get("format") or f.get("format") or "")
        if str(fmt).lower() not in ("safetensor", "safetensors") and not str(f.get("name", "")).endswith(".safetensors"): continue
        if str(f.get("pickleScanResult", "Success")) == "Danger" or str(f.get("virusScanResult", "Success")) == "Danger": continue
        out.append({"name": f.get("name"), "size_mb": round((f.get("sizeKB") or f.get("sizeKb") or 0) / 1024, 1), "sha256": (f.get("hashes") or {}).get("SHA256", ""), "url": f.get("downloadUrl"), "primary": bool(f.get("primary"))})
    return out

def search(query, types=None, base_models=None, limit=20, sort="Most Downloaded", opener=None):
    q = [("limit", min(int(limit), 100)), ("sort", sort), ("nsfw", "false"), ("primaryFileOnly", "true")]
    if query: q += [("query", query)]
    q += [("types", t) for t in (types or [])] + [("baseModels", b) for b in (base_models or [])]
    d = get_json(BASE + "/models?" + urllib.parse.urlencode(q), opener=opener); items = []
    for m in d.get("items") or []:
        if m.get("nsfw") or m.get("minor") or m.get("poi"): continue
        vs = [{"id": v.get("id"), "name": v.get("name"), "base_model": v.get("baseModel"), "files": _files(v)} for v in m.get("modelVersions") or []]
        vs = [v for v in vs if v["files"]]
        if vs: items.append({"id": m.get("id"), "name": m.get("name"), "type": m.get("type"), "commercial_use": m.get("allowCommercialUse"), "creator": (m.get("creator") or {}).get("username"),
                             "downloads": (m.get("stats") or {}).get("downloadCount"), "url": f"https://civitai.com/models/{m.get('id')}", "versions": vs})
    return items

def fetch(file, dest_dir, confirm=False, token=None, opener=None, max_bytes=None):
    """Download one file dict from search(). Needs confirm=True. Lands in dest_dir (a staging folder; the model sorter files it afterwards)."""
    if not confirm: raise ConnectorError("download needs confirm=True (the owner asks for it explicitly)")
    if not file.get("url") or not file.get("sha256"): raise ConnectorError("file has no download URL or no SHA-256 from the service")
    name = os.path.basename(file["name"] or "model.safetensors")
    return download(file["url"], os.path.join(dest_dir, name), sha256=file["sha256"], token=token or os.environ.get("CIVITAI_TOKEN"), opener=opener, max_bytes=max_bytes)
