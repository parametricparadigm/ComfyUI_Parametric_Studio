"""Deterministic fallback prompts: when the language model is unavailable or fails its checks, a formula still produces a valid, SFW, well-formed prompt (same inputs and seed give the same prompt). enhance_or_fallback() tries the verified
prompt_enhancer subagent first and says which source answered. Idea carried over from the home studio's fallback_prompt/lint/fix; original code."""
import hashlib, re
from psn.subagents.verify import SFW_BLOCK
LIGHT = ["soft window light", "golden hour backlight", "overcast diffused light", "warm tungsten glow", "cool blue dusk light", "bright morning sun"]
STYLE = ["photographic, natural colour", "cinematic still, shallow depth of field", "clean editorial photograph", "film photograph with fine grain", "crisp documentary look"]
MOOD = ["calm", "quietly joyful", "contemplative", "warm and inviting", "serene", "energetic"]
DETAIL = ["fine texture", "sharp focus on the subject", "rich natural detail", "balanced composition"]
def _pick(options, key, seed): return options[int(hashlib.sha256(f"{key}|{seed}".encode()).hexdigest(), 16) % len(options)]
def build_prompt(parts, seed=0, video=False):
    """parts: subject (required), optional setting, light, style, mood, detail, camera (video only). -> one prompt string."""
    s = (parts.get("subject") or "").strip()
    if not s: raise ValueError("a subject is required")
    out = [s]; 
    if parts.get("setting"): out.append("in " + parts["setting"].strip())
    out += [parts.get("light") or _pick(LIGHT, s, seed), parts.get("style") or _pick(STYLE, s + "style", seed), parts.get("mood") or _pick(MOOD, s + "mood", seed), parts.get("detail") or _pick(DETAIL, s + "detail", seed)]
    if video and parts.get("camera"): out.append(parts["camera"].strip())
    return fix(", ".join(out))
def lint(prompt, min_words=8, max_words=200):
    p, w = [], prompt.split()
    if len(w) < min_words: p.append(f"too short ({len(w)} words)")
    if len(w) > max_words: p.append(f"too long ({len(w)} words)")
    if SFW_BLOCK.search(prompt): p.append("non-SFW wording")
    if re.search(r"\b(\w+)(?:,? \1\b){1}", prompt, re.I): p.append("repeated word")
    return p
def fix(prompt, max_words=200):
    """Collapse whitespace, drop immediately repeated words, trim to max_words at a comma."""
    t = re.sub(r"\s+", " ", prompt).strip(" ,"); t = re.sub(r"\b(\w+)(?: \1\b)+", r"\1", t, flags=re.I); w = t.split()
    if len(w) > max_words: t = " ".join(w[:max_words]).rsplit(",", 1)[0]
    return t
def enhance_or_fallback(idea, parts=None, seed=0, video=False, runner=None, **kw):
    """-> {"prompt","negative","source": 'model'|'fallback', "problems"}. The model's answer is used only if the subagent verifier accepts it."""
    from psn.subagents import run_subagent
    runner = runner or run_subagent
    try:
        r = runner("prompt_enhancer", f"Idea: {idea}", {"must_keep": [(parts or {}).get("subject", idea).split()[0]] if (parts or {}).get("subject", idea) else [], "video": video, "min_words": 12}, **kw)
        if r.ok: return {"prompt": r.output["prompt"], "negative": r.output["negative"], "source": "model", "problems": []}
        why = r.problems
    except Exception as e: why = [f"{type(e).__name__}: {str(e)[:80]}"]
    p = build_prompt({"subject": idea, **(parts or {})}, seed, video); return {"prompt": p, "negative": "blurry, low quality, distorted, watermark, text", "source": "fallback", "problems": why + lint(p)}
