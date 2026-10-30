"""Hard checks on a built static site. Everything is code: parseable HTML, one h1 per page, title and viewport, alt text on images, internal links and assets that exist, no remote resources (the site must work offline), required sections present, SFW wording."""
import os, re
from html.parser import HTMLParser
from urllib.parse import urlparse
from psn.subagents.verify import SFW_BLOCK
class _P(HTMLParser):
    def __init__(self): super().__init__(); self.h1 = 0; self.title = ""; self._t = False; self.viewport = False; self.imgs = []; self.refs = []; self.ids = set(); self.stack = []; self.problems = []; self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); self.ids.add(a.get("id")) if a.get("id") else None
        if tag == "h1": self.h1 += 1
        if tag == "title": self._t = True
        if tag == "meta" and a.get("name") == "viewport": self.viewport = True
        if tag == "img": self.imgs.append(a)
        for k in ("href", "src", "action"):
            if a.get(k): self.refs.append(a[k])
        if tag not in ("meta", "link", "img", "br", "hr", "input", "source"): self.stack.append(tag)
        if tag == "script" and not a.get("src"): self.problems.append("inline script found: not needed, keep behaviour in assets/app.js")
    def handle_endtag(self, tag):
        if tag == "title": self._t = False
        if tag in ("meta", "link", "img", "br", "hr", "input", "source"): return
        if not self.stack or self.stack[-1] != tag: self.problems.append(f"unbalanced </{tag}>")
        else: self.stack.pop()
    def handle_data(self, d): self.title += d if self._t else ""; self.text.append(d)
def check_site(root, plan=None):
    """-> list of problems (empty = site passes). `plan`: {"pages": [{"slug", "sections": [{"id"}]}]} to require sections."""
    probs, pages = [], [f for f in os.listdir(root) if f.endswith(".html")]
    if "index.html" not in pages: probs.append("no index.html")
    for f in sorted(pages):
        p = _P(); html = open(os.path.join(root, f), encoding="utf-8").read(); p.feed(html); p.close()
        probs += [f"{f}: {x}" for x in p.problems[:3]]
        if p.stack: probs.append(f"{f}: unclosed <{p.stack[-1]}>")
        if p.h1 != 1: probs.append(f"{f}: needs exactly one <h1>, found {p.h1}")
        if not p.title.strip(): probs.append(f"{f}: empty <title>")
        if not p.viewport: probs.append(f"{f}: missing viewport meta (phones)")
        for im in p.imgs:
            if not (im.get("alt") or "").strip(): probs.append(f"{f}: image without alt text: {im.get('src')}")
        for r in p.refs:
            u = urlparse(r)
            if u.scheme in ("http", "https") or r.startswith("//"): probs.append(f"{f}: remote resource {r[:50]} (must work offline)")
            elif u.scheme in ("mailto", "tel", "") and not r.startswith(("#", "mailto:", "tel:")) and u.path:
                if not os.path.exists(os.path.join(root, u.path)): probs.append(f"{f}: broken link {r}")
        if SFW_BLOCK.search(" ".join(p.text)): probs.append(f"{f}: contains non-SFW wording")
        if plan:
            slug = f[:-5]; want = next((pg for pg in plan["pages"] if pg["slug"] == slug), None)
            for s in (want or {}).get("sections", []):
                if s["id"] not in p.ids: probs.append(f"{f}: planned section '{s['id']}' missing")
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".css") and re.search(r"@import\s+url\(\s*['\"]?https?:|url\(\s*['\"]?https?:", open(os.path.join(dp, f), errors="replace").read()): probs.append(f"{f}: remote URL in CSS")
            if os.path.getsize(os.path.join(dp, f)) > 2_000_000: probs.append(f"{f}: over 2 MB")
    return probs
