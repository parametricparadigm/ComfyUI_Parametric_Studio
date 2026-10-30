import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from psn import paths
from studio import crew

router = APIRouter()

KB_ROOT = paths.setting("STUDIO_KB", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew_notes"))      # the notes in this repo, unless a larger knowledge base is named


class AskRequest(BaseModel):
    who: str
    question: str


def _get_roster() -> List[Dict[str, Any]]:
    try:
        return crew.roster(KB_ROOT)
    except Exception:
        return []


def _find_member(members: List[Dict[str, Any]], member_id: str) -> Optional[Dict[str, Any]]:
    for m in members:
        if m.get("id") == member_id:
            return m
    return None


def _from_notes(member: Dict[str, Any], question: str) -> Dict[str, Any]:
    hits = crew.retrieve(member.get("files") or [], question, k=2)
    if not hits: return {"answer": "I can't back that up from my notes.", "quotes": [], "supported": False, "problems": ["No relevant chunks found"], "member": member.get("id")}
    return {"answer": hits[0]["text"], "quotes": [{"file": os.path.basename(h["file"]), "quote": h["text"]} for h in hits], "supported": True, "problems": [], "from_notes_only": True, "member": member.get("id")}


@router.get("/api/crew")
async def get_crew() -> Dict[str, Any]:
    members = _get_roster()
    return {"members": [{**{k: m.get(k) for k in ("id", "family", "name", "tier", "has_dossier")}, "portrait": crew.portrait(m.get("id")), "motion": crew.motion(m.get("id")), "voice": crew.voice(m.get("id"))[0], "hello": crew.hello(m.get("id"))} for m in members]}


@router.post("/api/crew/ask")
async def ask_crew(req: AskRequest) -> Dict[str, Any]:
    question = req.question.strip()
    if len(question) < 3 or len(question) > 600:
        raise HTTPException(status_code=400, detail="Question must be 3..600 chars")

    members = _get_roster()

    if req.who == "auto":
        try:
            member = crew.route(question, members)
            if isinstance(member, str):  # crew.route answers with the member's id
                member = _find_member(members, member)
        except Exception:
            raise HTTPException(status_code=404, detail="No member found for auto routing")
        if member is None:
            raise HTTPException(status_code=404, detail="No member found for auto routing")
    else:
        member = _find_member(members, req.who)
        if member is None:
            raise HTTPException(status_code=404, detail="Unknown member")

    try:
        result = await run_in_threadpool(crew.ask, member, question, crew.default_chat, 4)
    except RuntimeError:                                       # no language model on this machine: answer with the closest passages from the notes, word for word
        result = _from_notes(member, question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "result": result,
        "member": {
            "id": member.get("id"),
            "name": member.get("name"),
            "tier": member.get("tier"),
        },
    }
