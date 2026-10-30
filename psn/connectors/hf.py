"""Hugging Face Hub catalogue connector. Search uses the public Hub API (GET /api/models); downloads use huggingface_hub (hf_hub_download / snapshot_download with allow_patterns),
dry-run first. Token from HF_TOKEN (read by huggingface_hub itself). SFW: gated and not-for-all-audiences repos are dropped."""
import urllib.parse
from psn.connectors.net import get_json, ConnectorError
BASE = "https://huggingface.co/api/models"

def search(query, pipeline_tag=None, limit=20, sort="downloads", opener=None):
    q = [("search", query), ("limit", min(int(limit), 100)), ("sort", sort), ("direction", "-1"), ("full", "false"), ("config", "false")] + ([("pipeline_tag", pipeline_tag)] if pipeline_tag else [])
    out = []
    for m in get_json(BASE + "?" + urllib.parse.urlencode(q), opener=opener) or []:
        tags = m.get("tags") or []
        if m.get("private") or m.get("gated") or "not-for-all-audiences" in tags: continue
        lic = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), "")
        out.append({"id": m.get("id"), "downloads": m.get("downloads"), "likes": m.get("likes"), "pipeline_tag": m.get("pipeline_tag"), "license": lic, "url": f"https://huggingface.co/{m.get('id')}"})
    return out

def fetch(repo_id, filename=None, dest_dir=None, confirm=False, allow_patterns=None, dry_run=True, downloader=None):
    """Download one file (filename) or a filtered snapshot (allow_patterns). dry_run=True (default) only reports what would be fetched. Real downloads need confirm=True."""
    if not dry_run and not confirm: raise ConnectorError("download needs confirm=True (the owner asks for it explicitly)")
    if downloader is None:
        import huggingface_hub as hh
        downloader = hh.hf_hub_download if filename else hh.snapshot_download
    kw = {"repo_id": repo_id, "local_dir": dest_dir, "dry_run": dry_run}
    if filename: kw["filename"] = filename
    else: kw["allow_patterns"] = allow_patterns
    return downloader(**kw)
