import os
import re
import secrets
import mimetypes
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from psn.sitebuilder.build import brief_problems, build_site

router = APIRouter()

SITE_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _sites_root() -> Path:
    root = os.environ.get("STUDIO_SITES", os.path.expanduser("~/studio_sites"))
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _site_dir(site_id: str) -> Path:
    return _sites_root() / site_id


def _safe_resolve(site_id: str, rel_path: str) -> Path | None:
    """Resolve a relative path within the site directory, rejecting traversal."""
    if not SITE_ID_RE.match(site_id):
        return None
    site_dir = _site_dir(site_id)
    if not site_dir.is_dir():
        return None
    # Reject absolute paths
    if rel_path.startswith("/"):
        return None
    # Reject null bytes
    if "\0" in rel_path:
        return None
    # Resolve the path
    target = (site_dir / rel_path).resolve()
    # Ensure it's inside the site directory
    try:
        target.relative_to(site_dir.resolve())
    except ValueError:
        return None
    return target


class BuildRequest(BaseModel):
    brief: Dict[str, Any]


@router.post("/api/site/build")
async def build_site_endpoint(req: BuildRequest):
    brief = req.brief
    problems = brief_problems(brief)
    if problems:
        return JSONResponse(status_code=400, content={"problems": problems})

    site_id = secrets.token_hex(6)
    out_dir = _site_dir(site_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = build_site(brief, str(out_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    files = []
    problems_out = []

    if isinstance(result, dict):
        if 'files' in result:
            files = result['files']
        elif 'file_list' in result:
            files = result['file_list']
        else:
            for item in out_dir.rglob('*'):
                if item.is_file():
                    files.append(str(item.relative_to(out_dir)))

        if 'problems' in result:
            problems_out = result['problems']
        elif 'errors' in result:
            problems_out = result['errors']

    elif isinstance(result, list):
        files = result

    rel_files = []
    for f in files:
        if isinstance(f, str):
            rel_files.append(f.replace(os.sep, '/'))
        else:
            rel_files.append(str(Path(f).relative_to(out_dir)).replace(os.sep, '/'))

    return {
        "site_id": site_id,
        "files": rel_files,
        "problems": problems_out
    }


@router.get("/api/site/{site_id}")
async def list_site_files(site_id: str):
    if not SITE_ID_RE.match(site_id):
        raise HTTPException(status_code=404, detail="Not found")

    site_dir = _site_dir(site_id)
    if not site_dir.is_dir():
        raise HTTPException(status_code=404, detail="Not found")

    files = []
    for item in site_dir.rglob('*'):
        if item.is_file():
            files.append(str(item.relative_to(site_dir)).replace(os.sep, '/'))

    return {"files": files}


@router.get("/api/site/{site_id}/{path:path}")
async def serve_site_file(site_id: str, path: str):
    if not SITE_ID_RE.match(site_id):
        raise HTTPException(status_code=404, detail="Not found")

    target = _safe_resolve(site_id, path)
    if target is None or not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    media_type, _ = mimetypes.guess_type(str(target))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(target, media_type=media_type)
