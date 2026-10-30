from studio.anime import STYLES, strict_prompt, REALISM
from studio.goals import values_for, GOALS

def test_eight_styles_with_phrases():
    assert len(STYLES) == 8 and all(len(v[1].split()) >= 6 for v in STYLES.values())
    assert len({v[1] for v in STYLES.values()}) == 8

def test_realism_words_removed_and_style_leads():
    t, removed = strict_prompt("photorealistic portrait of a girl, 35mm, film grain, skin pores, red scarf", "shonen")
    assert t.startswith(STYLES["shonen"][1]) and "red scarf" in t and "girl" in t
    assert not REALISM.search(t) and {"photorealistic", "35mm", "film grain", "skin pores"} <= set(removed)

def test_plain_prompt_untouched_and_empty_prompt():
    t, removed = strict_prompt("a fox in the snow", "tv"); assert removed == [] and t.endswith("a fox in the snow")
    assert strict_prompt("", "chibi")[0] == STYLES["chibi"][1]
    assert strict_prompt("x", "unknown-style")[0].startswith(STYLES["tv"][1])

def test_anime_goal_values():
    v, o = values_for("anime", {"prompt": "DSLR photo of a knight", "options": {"style": "mecha", "mode": "fast"}})
    assert v["prompt"].startswith("masterpiece, best quality, safe, ") and "dslr" not in v["prompt"].lower()
    assert (v["steps"], v["cfg"], v["unet"]) == (10, 1.0, "anima/anima-turbo-v1.1.safetensors") and o["style"] == "mecha"
    v2, _ = values_for("anime", {"prompt": "a knight", "options": {"mode": "quality"}}); assert (v2["steps"], v2["cfg"]) == (30, 3.0) and "worst quality" in v2["negative"]
    assert "anime" in GOALS and GOALS["anime"]["family"] == "Anima"
