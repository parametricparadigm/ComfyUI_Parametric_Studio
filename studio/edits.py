"""AI video edits: the editing models and processes, run from ComfyUI's official LOCAL templates (never the paid partner-node ones), each with the form inferred from the template's own promoted controls.
Box-aware: every tool reports whether its nodes and model files exist on this machine and lists what to download."""
import json, os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from studio import apps as A, sfw
CAT = {"remove": "Remove", "upscale": "Upscale and smooth", "extend": "Extend", "restyle": "Restyle and control", "camera": "Move the camera", "fill": "Fill and widen", "edit": "Edit by instruction"}
TOOLS = [  # id, category, label, template, blurb
 ("void", "remove", "Remove objects or people", "utility_void_video_inpainting", "Paint over what should disappear; the model fills the gap and keeps the motion natural."),
 ("bgremove", "remove", "Remove the background", "utility-bria_remove_video_background", "Cut the subject out of a clip, ready for compositing."),
 ("seedvr2", "upscale", "Upscale (SeedVR2)", "utility_seedvr2_3b_int8_upscale_video", "Sharper, higher resolution video with a restoration model."),
 ("interpolate", "upscale", "Slow motion and smoother frames", "utility_video_frame_interpolation", "Insert in-between frames: smoother playback or slow motion."),
 ("h3_extend", "extend", "Extend a clip (MiniMax H3)", "video_minimax_h3_i2v_continuation", "Continue a shot from its last frames with matching sound."),
 ("h3_control", "restyle", "Restyle with control (MiniMax H3)", "video_minimax_h3_fun_controlnet_union", "Keep the structure of a video (depth, pose, edges) and change how it looks."),
 ("wan_control", "restyle", "Drive a video with pose or depth (Wan 5B Fun)", "video_wan2_2_5B_fun_control", "A smaller control model that fits more machines."),
 ("wan_control14", "restyle", "Drive a video with pose or depth (Wan 14B Fun)", "video_wan2_2_14B_fun_control", "The larger control model for big GPUs."),
 ("vace_v2v", "restyle", "Video to video (Wan VACE)", "video_wan_vace_14B_v2v", "Re-render a clip from a prompt while keeping its motion."),
 ("wan_camera", "camera", "New camera move (Wan Fun Camera 14B)", "video_wan2_2_14B_fun_camera", "Give an existing clip a new camera path."),
 ("wan_camera_s", "camera", "New camera move (Wan 2.1 Fun Camera 1.3B)", "video_wan2.1_fun_camera_v1.1_1.3B", "The small version of the camera tool."),
 ("wan_inpaint", "fill", "Fill a region (Wan 5B Fun inpaint)", "video_wan2_2_5B_fun_inpaint", "Replace part of a clip with something new."),
 ("vace_inpaint", "fill", "Fill a region (VACE)", "video_wan_vace_inpainting", "Mask-based video inpainting."),
 ("vace_outpaint", "fill", "Widen the frame (VACE outpaint)", "video_wan_vace_outpainting", "Extend the picture beyond its borders."),
 ("bernini", "edit", "Edit by instruction (Bernini)", "video_bernini_r_video_editing", "Say what to change; the model edits the clip."),
 ("capybara", "edit", "Edit by instruction (Capybara)", "video_capybara_v0_1_video_edit", "Another instruction-driven video editor."),
]
PARTNER_TOOLS = {"bgremove"}      # its template runs a partner node; named here too, so it stays hidden when ComfyUI runs with --disable-api-nodes and /object_info cannot flag it
def _path(name):
    for d in A._dirs():
        p = os.path.join(d, name + ".json")
        if os.path.exists(p): return p
def _hidden(tid, path, oi):
    """The open edition leaves out any tool whose template uses a partner node (EDITIONS.md)."""
    if not A.open_edition(): return False
    if tid in PARTNER_TOOLS: return True
    try: return bool(path and A.partner_types(json.load(open(path)), oi or {}))
    except Exception: return False
def catalogue(oi):
    out = []
    for tid, cat, label, tpl, blurb in TOOLS:
        p = _path(tpl)
        if _hidden(tid, p, oi): continue
        row = {"id": tid, "category": cat, "category_label": CAT[cat], "label": label, "blurb": blurb, "template": tpl, "installed": bool(p)}
        if p:
            try: d = A.describe(tid, p, oi); row.update(ready=d["ready"], runnable=d["runnable"], inputs=len(d["inputs"]), missing_models=d["missing_models"], unknown_nodes=d["unknown_nodes"])
            except Exception: row.update(ready=False, runnable=False, inputs=0, missing_models=[], unknown_nodes=[])
        else: row.update(ready=False, runnable=False, inputs=0, missing_models=[], unknown_nodes=[])
        out.append(row)
    return out
router = APIRouter()
class Run(BaseModel): values: dict = {}
def _find(tid):
    t = next((x for x in TOOLS if x[0] == tid), None)
    if not t or not _path(t[3]): raise HTTPException(404, "no such edit tool")
    try: oi = A.object_info()
    except Exception: oi = {}
    if _hidden(tid, _path(t[3]), oi): raise HTTPException(404, "no such edit tool")
    return t, _path(t[3])
@router.get("/api/edits")
def edits_list():
    try: return {"categories": CAT, "tools": catalogue(A.object_info())}
    except Exception: raise HTTPException(503, "ComfyUI is not reachable") from None
@router.get("/api/edits/{tid}")
def edits_get(tid: str):
    t, p = _find(tid); d = A.describe(tid, p, A.object_info()); d["title"] = t[2]; d["blurb"] = t[4]; return d
@router.post("/api/edits/{tid}/run")
def edits_run(tid: str, b: Run):
    t, p = _find(tid); sfw.check(*b.values.values())
    try: g = A.build_graph(p, b.values, A.object_info())
    except ValueError as e: raise HTTPException(400, str(e)) from None
    import urllib.request
    try: r = urllib.request.urlopen(urllib.request.Request(A.COMFY + "/prompt", json.dumps({"prompt": g, "client_id": "studio-edits"}).encode(), {"Content-Type": "application/json"}), timeout=30)
    except Exception as e: raise HTTPException(502, f"ComfyUI refused the graph: {str(e)[:120]}") from None
    return {"job": json.loads(r.read())["prompt_id"]}
@router.post("/api/edits/{tid}/fetch-models")
def edits_fetch(tid: str, b: dict):
    t, p = _find(tid)
    from psn.connectors.net import ConnectorError
    try: return {"saved": A.fetch_models(tid, p, A.object_info(), confirm=bool(b.get("confirm")))}
    except (ValueError, ConnectorError) as e: raise HTTPException(400, str(e)) from None
