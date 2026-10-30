"""Runs one subagent: a guarded loop of model call -> (tool call | final answer) -> verification. Budgeted (steps, completion tokens, wall-clock), tools limited to the role's allow-list,
no spawning (a subagent cannot start another: depth is 1 by construction), every run logged. Nothing here publishes, posts or spends."""
import json, os, time, threading, hashlib, uuid
from dataclasses import dataclass, field
from psn.subagents import llm as _llm, tools as _tools
from psn.subagents.roles import ROLES
from psn.subagents.verify import extract_json, validate
from psn.subagents.playbooks import playbook_for

STATE = os.environ.get("PSN_STATE_DIR") or os.path.expanduser("~/.local/state/parametric_studio")
_SLOTS = threading.BoundedSemaphore(int(os.environ.get("PSN_SUBAGENT_MAX", "8")))   # global cap on concurrent subagents (match it to what the model server can batch)

@dataclass
class Result:
    ok: bool; role: str; output: object = None; problems: list = field(default_factory=list); attempts: int = 0; steps: int = 0; tokens: int = 0; seconds: float = 0.0; transcript: str = ""
    def as_dict(self): return {k: getattr(self, k) for k in ("ok", "role", "output", "problems", "attempts", "steps", "tokens", "seconds", "transcript")}

PROTOCOL = ("\n\nReply with ONE JSON object and nothing else.\n"
            "To use a tool: {\"tool\": \"<name>\", \"args\": {...}} using EXACTLY the argument names shown. Tools you may use: %s\n"
            "To finish: {\"final\": <object matching this contract>}   Contract (JSON schema): %s")

def _user_message(role, task, ctx, image):
    shown = {k: v for k, v in (ctx or {}).items() if k not in ("object_info", "image_path") and not k.startswith("_") and len(json.dumps(v, default=str)) < 20000}
    ws = (ctx or {}).get("write_roots")
    text = f"TASK:\n{task}\n\n" + (f"WORKSPACE (the only place you can write or run commands; relative paths start here): {ws[0]}\n\n" if ws else "") + f"CONTEXT (json):\n{json.dumps(shown, default=str)[:30000]}"
    return {"role": "user", "content": [{"type": "text", "text": text}, _llm.image_part(image)]} if image else {"role": "user", "content": text}

def _log(rec):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(os.path.join(STATE, "subagents.jsonl"), "a") as f: f.write(json.dumps(rec) + "\n")
    except OSError: pass

def _save(role, messages):
    try:
        d = os.path.join(STATE, "subagent_transcripts"); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{time.strftime('%Y%m%d-%H%M%S')}-{role}-{os.getpid()}-{threading.get_ident() % 10000}.json")
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f: json.dump(messages, f, default=lambda o: "<binary>", indent=1)
        return p
    except OSError: return ""

def reply_schema(r):
    """Schema of ONE reply: a tool call or the final answer. Sent to the server so decoding is constrained to it (fewer wasted retries); the verifier still checks everything."""
    final = {"type": "object", "required": ["final"], "properties": {"final": r.schema}, "additionalProperties": False}
    if not r.tools: return final
    return {"anyOf": [{"type": "object", "required": ["tool", "args"], "properties": {"tool": {"enum": list(r.tools)}, "args": {"type": "object"}}, "additionalProperties": False}, final]}

def _ckpt_path(run_id): return os.path.join(STATE, "runs", os.path.basename(run_id) + ".json")
def _write_ckpt(run_id, d):
    try:
        os.makedirs(os.path.dirname(_ckpt_path(run_id)), exist_ok=True); tmp = _ckpt_path(run_id) + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f: json.dump(d, f, default=str)
        os.replace(tmp, _ckpt_path(run_id))
    except OSError: pass

def _strip_images(messages):
    return [{**m, "content": [p for p in m["content"] if p.get("type") != "image_url"]} if isinstance(m["content"], list) else m for m in messages]

def run_subagent(role, task, ctx=None, endpoint=None, max_attempts=3, max_seconds=600, max_total_tokens=40000, transport=None, run_id=None, checkpoint=True, _resume=None):
    """-> Result. `role` is a name in ROLES. `ctx` carries what the verifier needs (source text, labels, object_info ...). `transport` replaces the HTTP call (tests).
    With checkpoint=True the run is saved after every step under $STATE/runs/<run_id>.json; resume_subagent(run_id) continues it after a crash. Side-effecting tools are recorded in a ledger,
    so a retry or a resume returns the recorded result instead of doing it twice."""
    r = ROLES[role] if isinstance(role, str) else role; ctx = dict(ctx or {}); res = Result(False, r.name); rs = _resume or {}
    run_id = run_id or rs.get("run_id") or f"{time.strftime('%Y%m%d-%H%M%S')}-{r.name}-{uuid.uuid4().hex[:6]}"; t0 = time.time() - rs.get("elapsed", 0)
    ctx["_role"] = r.name; ctx["_state"] = rs.get("state") or {"written": [], "bash": [], "workflow": []}; ctx["_state"].setdefault("ledger", {})
    if any(t in _tools.AGENTIC for t in r.tools) and not ctx.get("write_roots"):
        ws = os.path.join(STATE, "work", f"{time.strftime('%Y%m%d-%H%M%S')}-{r.name}-{os.getpid()}-{threading.get_ident() % 10000}"); os.makedirs(ws, mode=0o700, exist_ok=True); ctx["write_roots"] = [ws]
    image = ctx.get("image_path") if r.vision else None
    messages = rs.get("messages") or [{"role": "system", "content": r.system + playbook_for(r.name) + _PROTO(r)}, _user_message(r, task, ctx, image)]
    if rs and image: messages[1] = _user_message(r, task, ctx, image)                       # checkpoints never hold image bytes: rebuild the first message
    res.steps, res.tokens = rs.get("steps", 0), rs.get("tokens", 0); first = True; schema = reply_schema(r)
    def save(attempt, step, status="running"):
        if checkpoint: _write_ckpt(run_id, {"run_id": run_id, "role": r.name, "task": task, "status": status, "attempt": attempt, "step_in_attempt": step, "steps": res.steps, "tokens": res.tokens,
                                           "elapsed": time.time() - t0, "messages": _strip_images(messages), "state": ctx["_state"], "ctx": {k: v for k, v in ctx.items() if k not in ("object_info", "_state")}})
    with _SLOTS:
        for attempt in range(rs.get("attempt", 1) if first else 1, max_attempts + 1):
            res.attempts = attempt; out = None; problems = []; calls = {}; step0 = rs.get("step_in_attempt", 0) if first else 0; first = False
            for step in range(step0, r.max_steps):
                if time.time() - t0 > max_seconds or res.tokens > max_total_tokens: problems = [f"budget exhausted ({res.tokens} tokens, {time.time()-t0:.0f}s)"]; break
                try: text, n = _llm.chat(endpoint or r.endpoint, messages, r.temperature, r.max_tokens, r.thinking, transport=transport, response_format=schema)
                except PermissionError: raise
                except Exception as e: problems = [f"model call failed: {type(e).__name__}: {str(e)[:120]}"]; break
                res.steps += 1; res.tokens += n; messages.append({"role": "assistant", "content": text}); obj = extract_json(text)
                if not isinstance(obj, dict): problems = ["reply was not a JSON object"]; messages.append({"role": "user", "content": "Reply with ONE JSON object only."}); save(attempt, step + 1); continue
                if "tool" in obj:
                    name, targs = obj["tool"], obj.get("args"); led = ctx["_state"]["ledger"]; lk = hashlib.sha1(json.dumps([name, targs], sort_keys=True, default=str).encode()).hexdigest()
                    if name not in r.tools: obs = {"error": f"tool '{name}' is not allowed for role {r.name}; allowed: {list(r.tools)}"}
                    elif name in _tools.LEDGERED and lk in led: obs = {**led[lk], "replayed": True, "note": "this exact call already happened; its recorded result is returned and nothing was repeated"}
                    else:
                        obs = _tools.call(name, targs, ctx)
                        if name in _tools.LEDGERED and not ({"error", "denied"} & set(obs)): led[lk] = obs
                    key = json.dumps([name, targs], sort_keys=True, default=str); calls[key] = calls.get(key, 0) + 1
                    note = f"\nYou have made this exact call {calls[key]} times with the same result. Change your approach or finish and report what happened." if calls[key] >= 3 else ""
                    messages.append({"role": "user", "content": "TOOL RESULT: " + json.dumps(obs, default=str) + note}); problems = ["no final answer yet"]; save(attempt, step + 1); continue
                out = obj.get("final", obj); problems = validate(out, r.schema)
                if not problems:
                    try: problems = list(r.verify(out, ctx))
                    except Exception as e: problems = [f"verifier could not check the output: {type(e).__name__}: {str(e)[:100]}"]
                break
            if out is not None and not problems: res.ok, res.output, res.problems = True, out, []; break
            res.output, res.problems = out, problems
            if time.time() - t0 > max_seconds or res.tokens > max_total_tokens: break
            messages.append({"role": "user", "content": "Your answer was rejected by the checker. Problems:\n- " + "\n- ".join(problems[:10]) + "\nFix them and reply with the corrected final JSON object."}); save(attempt + 1, 0)
    res.seconds = round(time.time() - t0, 2); res.transcript = _save(r.name, messages); save(res.attempts, 0, "done" if res.ok else "failed")
    _log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run_id": run_id, "role": r.name, "ok": res.ok, "attempts": res.attempts, "steps": res.steps, "tokens": res.tokens, "secs": res.seconds, "task": task[:80], "transcript": res.transcript})
    return res

def resume_subagent(run_id, ctx_extra=None, **kw):
    """Continue a run that was interrupted (crash, restart, kill) from its last checkpoint. Pass ctx_extra for things not stored, e.g. {"object_info": ...}. A finished run is not run again."""
    d = json.load(open(_ckpt_path(run_id)))
    if d["status"] in ("done", "failed"): raise ValueError(f"run {run_id} already {d['status']}; start a new run instead")
    return run_subagent(d["role"], d["task"], {**d["ctx"], **(ctx_extra or {})}, run_id=run_id, _resume=d, **kw)

def _PROTO(r):
    docs = "\n".join(f"  - {n}: {' '.join((_tools.TOOLS[n].__doc__ or '').split())}" for n in r.tools)
    return PROTOCOL % ("\n" + docs if docs else "none", json.dumps(r.schema))
