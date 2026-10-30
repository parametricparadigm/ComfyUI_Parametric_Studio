"""Role playbooks: short working guidance for subagent roles, adapted from the MIT-licensed awesome-claude-agents collection (licence in playbooks/).
Only the front of each file is used (frontmatter stripped, capped), so a playbook sharpens a role's habits without crowding the task. Off with PSN_PLAYBOOKS=0."""
import os, re
DIR = os.path.join(os.path.dirname(__file__), "playbooks")
MAP = {"builder": ["testing-expert", "code-reviewer"], "coder": ["testing-expert"], "judge": ["code-reviewer"], "red_team": ["security-expert", "code-reviewer"],
       "graph_debugger": ["code-archaeologist"], "operator": ["performance-expert"], "planner": ["tech-lead-orchestrator"], "router": ["project-analyst"], "scout": ["project-analyst"],
       "researcher": ["code-archaeologist"], "writer": ["documentation-specialist"], "summarizer": ["documentation-specialist"]}
CAP = int(os.environ.get("PSN_PLAYBOOK_CHARS", "1800"))
_cache = {}
def _load(name):
    if name not in _cache:
        try: t = open(os.path.join(DIR, name + ".md"), errors="replace").read()
        except OSError: t = ""
        t = re.sub(r"\A---.*?---\s*", "", t, flags=re.S); t = re.sub(r"[`*]{2,}|\*\*", "", t)
        t = "\n\n".join(b for b in re.split(r"\n\s*\n", t) if not re.search(r"WebFetch|Context7|context7|https?://|fetch (the )?(latest|recent)|web search|WebSearch", b, re.I))
        _cache[name] = re.sub(r"\n{3,}", "\n\n", t).strip()[:CAP].rsplit("\n", 1)[0]
    return _cache[name]
def playbook_for(role_name):
    """-> text to append to the role's system prompt ('' when none or disabled)."""
    if os.environ.get("PSN_PLAYBOOKS", "1") == "0": return ""
    parts = [p for p in (_load(n) for n in MAP.get(role_name, [])) if p]
    return ("\n\nWORKING GUIDANCE (habits to apply; the task and contract above still win):\n" + "\n\n".join(parts)) if parts else ""
