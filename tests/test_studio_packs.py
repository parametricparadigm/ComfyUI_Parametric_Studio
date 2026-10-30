import json, re, pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import packs as P

BAD = re.compile(r"\b(nsfw|nude|naked|lingerie|porn|hentai|explicit|erotic|sex\w*|topless|tattoo\w*|fetish|gore|nike|adidas|gucci|disney|marvel|pokemon|ferrari|lamborghini|porsche|bmw|tesla|harley)\b", re.I)

def test_packs_are_sfw_and_brand_free():
    d = P.load(); assert len(d) >= 10
    for pid, p in d.items():
        assert not BAD.search(json.dumps(p)), pid
        assert p["groups"] and all(len(P._opts(g)) >= 2 for g in p["groups"]), pid

def test_compose_uses_only_valid_options_and_adds_originality_tail():
    d = P.load()["tshirt"]; g = next(g for g in d["groups"] if g["id"] == "garment_colour"); view = d["views"][0]
    t = P.compose("tshirt", {"garment_colour": g["options"][0]}, idea="a fox reading a book", view=view, words="READ MORE")
    assert "a fox reading a book" in t and 'exactly: "READ MORE"' in t and P.TAIL in t and g["options"][0] in t
    with pytest.raises(ValueError): P.compose("tshirt", {"garment_colour": "not a colour"})
    with pytest.raises(ValueError): P.compose("tshirt", {}, view="not a view")
    with pytest.raises(KeyError): P.compose("nope", {})

def test_words_only_for_apparel_and_router():
    assert 'exactly' not in P.compose("vehicle", {}, idea="a desert racer", words="HELLO")
    app = FastAPI(); app.include_router(P.router); c = TestClient(app)
    assert c.get("/api/packs").json()["packs"][0]["id"] and c.get("/api/packs/vehicle").json()["groups"]
    assert c.get("/api/packs/zzz").status_code == 404
    r = c.post("/api/packs/vehicle/compose", json={"idea": "a desert racer", "choices": {}}); assert r.status_code == 200 and "desert racer" in r.json()["prompt"]
    assert c.post("/api/packs/vehicle/compose", json={"choices": {"kinds": "not real"}}).status_code == 400

def test_every_designer_has_a_sheet_and_the_slot_in_a_view_is_filled():
    d = P.load()
    for pid, p in d.items(): assert p["views"] and all(v in p["view_words"] for v in p["views"]), pid      # the print-on-demand pack used to list 0 views
    assert len(d["printify"]["views"]) >= 2 and "swap_views" not in [g["id"] for g in d["printify"]["groups"]]
    t = P.compose("plant", {"kinds": "monstera"}, view="in a room, styled"); assert "{subject}" not in t and "monstera" in t.split(".")[0]

def test_character_and_fashion_are_fully_clothed_adult_and_the_first_tiles_with_vehicle():
    ids = [s["id"] for s in P.summary()]; assert ids[:3] == ["character", "fashion", "vehicle"] and len(ids) == 13
    c, f = P.load()["character"], P.load()["fashion"]; assert all("fictional adult" in w for w in c["view_words"].values()) and not any(o in json.dumps([c, f]).lower() for o in ("bikini", "lingerie", "swimsuit", "corset", "silhouette"))
    assert "fictional adult" in P.compose("character", {"age": "adult"}, view="full body, front") and P.compose("fashion", {"garment": "trench coat"}, view="flat lay on a clean background").startswith("Clean flat-lay")
