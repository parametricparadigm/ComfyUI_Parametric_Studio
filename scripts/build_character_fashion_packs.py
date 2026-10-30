#!/usr/bin/env python3
"""Add the Character and Fashion designers to studio/packs/packs.json the way the other designers were built: a read-only ast parse of the owner's designer modules (never imported, never run, never modified), constants only, then the SFW and brand filter.
Sources, under ~/earlier-studio/earlier_studio (the SFW copy named by DESIGNER_SOURCE_SFW is used when the first is missing): studio/fashion_categories.py (garment kinds, shared style, colour, pattern and fabric lists), studio/signature_outfits.py (palettes, accents, eye colours),
studio/hair_designer.py (hair lists), gamebuilder/story.py (expressions), studio/fashion.py (sheet and on-model view names); archetypes come from the cosplay pack already in packs.json. Process docs: docs/processes/character-sheet.md, sheet-engine.md, character-builder-models.md.
Rules (owner): fully clothed, fictional adults only, no real people, no brands, no body-shape options (studio/signature_outfits.py SILHOUETTES is left out on purpose). Usage: python3 scripts/build_character_fashion_packs.py [--dry-run]"""
import ast, json, os, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; PACKS = ROOT / "studio" / "packs" / "packs.json"; sys.path.insert(0, str(ROOT))
from psn import paths
SRC = next((Path(p) for p in ("~/earlier-studio/earlier_studio", paths.setting("DESIGNER_SOURCE_SFW", default="/nonexistent")) if (Path(p).expanduser() / "studio" / "fashion_categories.py").exists()), None)
SRC = SRC.expanduser() if SRC else None
BAD = re.compile(r"\b(nsfw|nude|naked|lingerie|porn|hentai|explicit|erotic|sex\w*|topless|tattoo\w*|fetish|bondage|gore|bikini|swim\w*|bra|bralette|thong|panty|panties|underwear|corset\w*|negligee|babydoll|teddy|garter\w*|fishnet\w*|stocking\w*|sheer|see-through|transparent|mesh|bodysuit|bodycon|harness|latex|catsuit|cleavage|plunging|backless|strapless|micro)\b", re.I)
BRANDISH = re.compile(r"\b(nike|adidas|gucci|prada|chanel|louis vuitton|supreme|disney|marvel|pokemon|pok[eé]mon|naruto|batman|spider-?man|star wars|harry potter|ferrari|lamborghini|porsche|bmw|mercedes|toyota|honda|ford|chevrolet|tesla|harley|levi'?s|converse|vans|rolex|hermes|hermès|dior|versace|burberry|zara|h&m|uniqlo|lululemon|patagonia|north face)\b", re.I)
TAIL_ADULT = "a fictional adult, fully clothed"
def ok(s): return isinstance(s, str) and s.strip() and not BAD.search(s) and not BRANDISH.search(s)
def clean(xs): return [x for x in xs if ok(x)]
def module(rel):
    tree = ast.parse((SRC / rel).read_text()); env, nodes = {}, {}
    for n in tree.body:
        t = n.targets[0] if isinstance(n, ast.Assign) and len(n.targets) == 1 else getattr(n, "target", None)
        if isinstance(t, ast.Name) and t.id.isupper() and getattr(n, "value", None) is not None:
            nodes[t.id] = n.value
            try: env[t.id] = ast.literal_eval(n.value)
            except Exception: pass
    return env, nodes
def evaluate(node, env):
    """literal_eval that also follows a module-level constant name (SHARED_STYLE) and nothing else: no code runs"""
    if isinstance(node, ast.Name) and node.id in env: return env[node.id]
    if isinstance(node, ast.Dict): return {evaluate(k, env): evaluate(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)): return [evaluate(x, env) for x in node.elts]
    return ast.literal_eval(node)
def build():
    fc, fcn = module("studio/fashion_categories.py"); so, _ = module("studio/signature_outfits.py"); hd, _ = module("studio/hair_designer.py"); st, _ = module("gamebuilder/story.py"); fa, _ = module("studio/fashion.py")
    cats = evaluate(fcn["CATEGORIES"], fc); cos = json.load(open(PACKS))["packs"]["cosplay"]; kinds = next(g for g in cos["groups"] if g["id"] == "kinds")["categories"]
    kind_of = lambda c: clean(cats[c]["options"]["garment"]) if c in cats and "garment" in cats[c]["options"] else []
    garments = {cats[c]["label"]: kind_of(c) for c in ("tops", "bottoms", "shoes", "jewellery", "accessories") if c in cats and kind_of(c)}
    eyes = [a for a, _b in so["_PALETTE_FOR"] if a.endswith(" eyes")]
    palettes = [p["name"] for p in so["PALETTES"]]
    G = lambda id, label, opts: {"id": id, "label": label, "options": clean(opts)}
    common = [G("style", "Style", fc["SHARED_STYLE"]), G("colour", "Colour", fc["SHARED_COLOUR"]), G("pattern", "Pattern", fc["SHARED_PATTERN"]), G("fabric", "Fabric", fc["GARMENT_FABRIC"]), G("palette", "Palette", palettes), G("accent", "Accent", so["ACCENTS"])]
    onv, shv = fa["ON_VIEWS"], fa["SHEET_VIEWS"]
    fashion_views = {"flat lay on a clean background": "Clean flat-lay product photograph of the complete outfit on a plain background", "ghost mannequin product photo": "E-commerce ghost-mannequin product photograph of the outfit, white background",
                     **{f"{v} on a plain backdrop": f"Studio product photograph of the outfit, {v}, plain backdrop" for v in (shv["front"], shv["back"], shv["three_quarter"], shv["detail"])},
                     **{f"on an adult model: {v}": f"Fashion photograph of the outfit worn by a fictional adult model, fully clothed, {v}, plain studio backdrop" for v in (onv["front"], onv["back"], onv["three_quarter"], onv["walk"])}, "lookbook collage of the outfit": "Lookbook collage of the same outfit in several views, fully clothed"}
    char_views = {"head and shoulders, front": f"Studio portrait of {TAIL_ADULT}, head and shoulders, front view, plain light grey background, even soft light", "head and shoulders, three-quarter view": f"Studio portrait of {TAIL_ADULT}, head and shoulders, three-quarter view, plain light grey background",
                  "head and shoulders, profile": f"Studio portrait of {TAIL_ADULT}, head and shoulders, side profile, plain light grey background",
                  **{f"full body, {nm}": f"Full-length photograph of {TAIL_ADULT}, {onv[k]}, plain light grey background" for k, nm in (("front", "front"), ("back", "back"), ("side", "side"), ("three_quarter", "three-quarter"), ("walk", "walking"))},
                  "expression sheet": f"Expression sheet of the same {TAIL_ADULT}: a grid of head-and-shoulders portraits with different expressions, plain background", "turnaround sheet": f"Character turnaround sheet of {TAIL_ADULT}: front, side and back full-length views side by side, plain background"}
    char = {"id": "character", "label": "Character designer", "doc": "Original fictional adult characters, fully clothed, as a character sheet: headshots, full-body views and expressions. Built from the owner's hair, fashion and story modules (see scripts/build_character_fashion_packs.py).",
            "groups": [{"id": "age", "label": "Age", "options": ["young adult", "adult", "mature adult", "older adult"]}, {"id": "role", "label": "Role", "categories": {k: clean(v) for k, v in kinds.items() if k in ("Fantasy", "Sci-fi & mecha", "Heroes & villains", "Game archetypes", "Steampunk & retro-futurist", "Historical & period", "Anime & manga archetypes")}},
                       G("hair_colour", "Hair colour", hd["COLOUR"]), G("hair_texture", "Hair texture", hd["TEXTURE"]), G("hair_length", "Hair length", hd["LENGTH"]), G("bangs", "Bangs", hd["BANGS"]), G("hair_accessory", "Hair accessory", hd["ACCESSORIES"]), G("eyes", "Eyes", eyes), G("expression", "Expression", list(st["EXPRESSIONS"])),
                       {"id": "outfit", "label": "Outfit", "categories": {k: v for k, v in garments.items() if k in ("Tops, dresses & outfits", "Bottoms", "Shoes")}}, *common[:3], common[4]],
            "views": list(char_views), "view_words": char_views}
    fash = {"id": "fashion", "label": "Fashion designer", "doc": "Original clothing, shoes, jewellery and accessories as a full sheet: flat lays, mannequin shots and fully clothed fictional adult models. Built from the owner's fashion modules (see scripts/build_character_fashion_packs.py).",
            "groups": [{"id": "garment", "label": "Garment", "categories": garments}, *common], "views": list(fashion_views), "view_words": fashion_views}
    for p in (char, fash):
        p["groups"] = [g for g in p["groups"] if len(g.get("options") or sum((g.get("categories") or {}).values(), [])) >= 2]
        assert not BAD.search(json.dumps(p)) and not BRANDISH.search(json.dumps(p)), p["id"]
    return char, fash
def main():
    if SRC is None: sys.exit("the owner's designer modules were not found")
    char, fash = build(); doc = json.load(open(PACKS))
    for p in (char, fash): print(f"{p['id']:10} groups={len(p['groups'])} views={len(p['views'])} options={sum(len(g.get('options') or sum(g['categories'].values(), [])) for g in p['groups'])}  groups: {', '.join(g['id'] for g in p['groups'])}")
    if "--dry-run" in sys.argv: return
    doc["packs"]["character"], doc["packs"]["fashion"] = char, fash; PACKS.write_text(json.dumps(doc, indent=1)); print("wrote", PACKS)
if __name__ == "__main__": main()
