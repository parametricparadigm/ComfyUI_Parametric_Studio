"""Design tokens with a contrast guarantee. WCAG 2.x relative luminance and contrast ratio; make_tokens() nudges the text/accent colours until body text >= 4.5:1 and large text/buttons >= 3:1 on their backgrounds, in light and dark."""
import re
def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def _hex(c): return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)
def _lin(v): v /= 255; return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
def luminance(h): r, g, b = _rgb(h); return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
def contrast(a, b): la, lb = sorted((luminance(a), luminance(b)), reverse=True); return (la + 0.05) / (lb + 0.05)
def _shift(h, toward, step=0.08):
    r = _rgb(h); t = (255, 255, 255) if toward == "white" else (0, 0, 0); return _hex(tuple(v + (w - v) * step for v, w in zip(r, t)))
def _ensure(fg, bg, need):
    toward = "white" if luminance(bg) < 0.5 else "black"
    for _ in range(40):
        if contrast(fg, bg) >= need: return fg
        fg = _shift(fg, toward)
    return "#ffffff" if toward == "white" else "#000000"
def make_tokens(brand="#3b6ea5"):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", brand or ""): raise ValueError("brand colour must look like #3b6ea5")
    light = {"bg": "#ffffff", "surface": "#f4f6f9", "text": "#1b1f24", "muted": _ensure("#5b6572", "#ffffff", 4.5)}
    dark = {"bg": "#12151a", "surface": "#1b2028", "text": "#eef1f5", "muted": _ensure("#a3acb8", "#12151a", 4.5)}
    light["accent"] = _ensure(brand, light["bg"], 4.5); dark["accent"] = _ensure(brand, dark["bg"], 4.5)
    for t in (light, dark): t["on_accent"] = "#ffffff" if contrast("#ffffff", t["accent"]) >= contrast("#000000", t["accent"]) else "#000000"
    return {"light": light, "dark": dark, "font": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", "radius": "12px"}
def token_problems(t):
    p = []
    for mode in ("light", "dark"):
        c = t[mode]
        for fg, need in (("text", 7.0), ("muted", 4.5), ("accent", 4.5)):
            if contrast(c[fg], c["bg"]) < need: p.append(f"{mode}: {fg} on bg is {contrast(c[fg], c['bg']):.1f}:1, needs {need}")
        if contrast(c["on_accent"], c["accent"]) < 4.5: p.append(f"{mode}: button text on accent is below 4.5:1")
    return p
