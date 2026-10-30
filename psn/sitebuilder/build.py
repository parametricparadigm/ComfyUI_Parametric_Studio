"""The builder: brief -> copy (the site_copywriter subagent; its output is checked by code) -> contrast-checked tokens -> deterministic HTML/CSS/JS writer -> hard checks. The model never writes HTML or CSS: it writes structured copy, and this module renders it,
so the result is consistent and verifiable. Images start as generated SVG placeholders and a todo list of image prompts, ready for a ComfyUI family instance to replace them."""
import html, json, os, re, shutil, tempfile, zipfile
from psn.sitebuilder import style, checks
from psn.subagents import run_subagent
from psn.subagents.verify import SFW_BLOCK
DEFAULT_PAGES = ["Home", "About", "Services", "Contact"]

def brief_problems(b):
    p = []
    if not isinstance(b, dict) or not str(b.get("name", "")).strip(): return ["brief needs a name"]
    if len(json.dumps(b)) > 8000: p.append("brief is too long (8000 characters)")
    if SFW_BLOCK.search(json.dumps(b)): p.append("brief contains non-SFW wording: this studio builds SFW sites only")
    for k, v in (b.get("facts") or {}).items():
        if not isinstance(v, str): p.append(f"fact '{k}' must be text")
    return p

def _atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True); fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path)); os.write(fd, text.encode("utf-8")); os.close(fd); os.replace(tmp, path)

def css(t):
    L, D = t["light"], t["dark"]; var = lambda c: ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in c.items())
    return f""":root{{{var(L)};--font:{t['font']};--r:{t['radius']}}}@media (prefers-color-scheme:dark){{:root{{{var(D)}}}}}
*{{box-sizing:border-box}}body{{margin:0;font:1.05rem/1.65 var(--font);background:var(--bg);color:var(--text)}}a{{color:var(--accent)}}
header,main,footer{{max-width:68rem;margin:0 auto;padding:1rem 1.25rem}}header{{display:flex;flex-wrap:wrap;gap:.75rem;align-items:center;justify-content:space-between}}
.brand{{font-weight:700;font-size:1.25rem;text-decoration:none;color:var(--text)}}nav{{display:flex;flex-wrap:wrap;gap:.25rem}}nav a{{padding:.5rem .8rem;border-radius:var(--r);text-decoration:none}}nav a[aria-current=page]{{background:var(--surface);font-weight:600}}
section{{display:grid;gap:1.25rem;align-items:center;margin:2.5rem 0;grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))}}section:first-of-type{{padding:2rem;background:var(--surface);border-radius:var(--r)}}section:first-of-type h2{{font-size:clamp(1.8rem,5vw,2.8rem);line-height:1.15}}
img{{width:100%;height:auto;border-radius:var(--r);background:var(--surface)}}h1{{font-size:clamp(1.6rem,4vw,2.2rem);margin:.5rem 0}}.btn{{display:inline-block;padding:.7rem 1.2rem;border-radius:var(--r);background:var(--accent);color:var(--on-accent);text-decoration:none;font-weight:600}}
footer{{color:var(--muted);border-top:1px solid var(--surface);margin-top:3rem}}:focus-visible{{outline:3px solid var(--accent);outline-offset:2px}}@media (max-width:40rem){{header{{flex-direction:column;align-items:flex-start}}}}
"""

def placeholder_svg(t, seed, alt):
    h = sum(map(ord, seed)) % 360; c = t["light"]["accent"]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" role="img" aria-label="{html.escape(alt)}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c}"/><stop offset="1" stop-color="hsl({h},45%,35%)"/></linearGradient></defs><rect width="800" height="500" fill="url(#g)"/></svg>'

def page_html(brief, copy, page, tokens, facts):
    e = html.escape; nav = "".join(f'<a href="{"index" if p["slug"] == "home" else p["slug"]}.html"' + (' aria-current="page"' if p is page else "") + f'>{e(p["title"])}</a>' for p in copy["pages"])
    secs = []
    for s in page["sections"]:
        paras = "".join(f"<p>{e(x.strip())}</p>" for x in s["body"].split("\n\n") if x.strip())
        secs.append(f'<section id="{e(s["id"])}"><div><h2>{e(s["heading"])}</h2>{paras}</div><img src="assets/{e(page["slug"])}-{e(s["id"])}.svg" alt="{e(s["alt"])}" loading="lazy" width="800" height="500"></section>')
    foot = " · ".join(filter(None, [e(facts.get("address", "")), f'<a href="mailto:{e(facts["email"])}">{e(facts["email"])}</a>' if facts.get("email") else "", f'<a href="tel:{re.sub(r"[^0-9+]", "", facts["phone"])}">{e(facts["phone"])}</a>' if facts.get("phone") else "", e(facts.get("hours", ""))]))
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(page["title"])} · {e(brief["name"])}</title>'
            f'<meta name="description" content="{e(page["description"])}"><link rel="stylesheet" href="assets/style.css"></head><body><header><a class="brand" href="index.html">{e(brief["name"])}</a><nav aria-label="Main">{nav}</nav></header>'
            f'<main><h1>{e(page["title"])}</h1>{"".join(secs)}</main><footer><p>{foot or e(brief["name"])}</p></footer><script src="assets/app.js" defer></script></body></html>')

def write_site(brief, copy, tokens, out):
    facts = brief.get("facts") or {}; os.makedirs(out, exist_ok=True); todo = []
    _atomic(f"{out}/assets/style.css", css(tokens)); _atomic(f"{out}/assets/app.js", "document.documentElement.classList.add('js');\n")
    for pg in copy["pages"]:
        _atomic(f"{out}/{'index' if pg['slug'] == 'home' else pg['slug']}.html", page_html(brief, copy, pg, tokens, facts))
        for s in pg["sections"]:
            _atomic(f"{out}/assets/{pg['slug']}-{s['id']}.svg", placeholder_svg(tokens, pg["slug"] + s["id"], s["alt"])); todo.append({"file": f"assets/{pg['slug']}-{s['id']}.svg", "prompt": s["image_prompt"], "alt": s["alt"]})
    _atomic(f"{out}/site.json", json.dumps({"brief": brief, "copy": copy, "tokens": tokens}, indent=1)); _atomic(f"{out}/images_todo.json", json.dumps(todo, indent=1)); return todo

def build_site(brief, out_dir, runner=run_subagent, **kw):
    """-> {"ok", "site_dir", "problems", "pages", "images_todo", "zip", "copy_attempts"}. Nothing is written unless the brief and the copy pass their checks."""
    bp = brief_problems(brief)
    if bp: return {"ok": False, "problems": bp, "stage": "brief"}
    brief = {**brief, "pages": brief.get("pages") or DEFAULT_PAGES}
    r = runner("site_copywriter", "Write the copy for this website.", {"brief": brief}, **kw)
    if not r.ok: return {"ok": False, "problems": r.problems, "stage": "copy", "copy_attempts": r.attempts}
    tokens = style.make_tokens(brief.get("brand", "#3b6ea5")); tp = style.token_problems(tokens)
    if tp: return {"ok": False, "problems": tp, "stage": "style"}
    todo = write_site(brief, r.output, tokens, out_dir); probs = checks.check_site(out_dir, r.output)
    z = shutil.make_archive(out_dir.rstrip("/") + "_site", "zip", out_dir) if not probs else ""
    return {"ok": not probs, "site_dir": out_dir, "problems": probs, "stage": "done" if not probs else "build checks", "pages": [p["slug"] for p in r.output["pages"]], "images_todo": len(todo), "zip": z, "copy_attempts": r.attempts}
