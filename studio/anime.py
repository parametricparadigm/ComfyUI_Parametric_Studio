"""Anime studio core ("strict" anime look). Eight styles with original wording, and a realism filter: words that pull a model toward photographs are removed from the user's prompt and the chosen style leads it.
The Anima model's own prefix (masterpiece, best quality, safe) is added by studio.goals."""
import re
STYLES = {
 "tv": ("TV anime", "clean TV anime key frame, crisp lineart, flat cel shading, bright balanced colors"),
 "storybook": ("Painterly storybook", "painterly storybook anime illustration, soft watercolor washes, gentle textured brushwork, warm light"),
 "shonen": ("Shonen action", "dynamic shonen anime action scene, bold ink lines, strong contrast, speed lines, vivid saturated colors"),
 "shojo": ("Shojo romance", "shojo anime illustration, delicate lineart, sparkling highlights, pastel palette, soft glowing background"),
 "90s": ("90s retro", "1990s retro anime still, slightly grainy cel animation look, muted vintage palette, hand painted background"),
 "chibi": ("Chibi", "cute chibi anime style, big head and tiny body, thick rounded outlines, playful bright colors"),
 "cyberpunk": ("Cyberpunk", "cyberpunk anime scene, neon signs, rainy night city, glowing cyan and magenta light, sharp lineart"),
 "mecha": ("Mecha", "mecha anime illustration, detailed robot design, panel lines, dramatic low angle, sunset sky"),
}
REALISM = re.compile(r"\b(photo(?:graph(?:y|ic|s)?)?|photo[- ]?realistic|hyper[- ]?realistic|realistic|realism|35\s?mm|50\s?mm|85\s?mm|dslr|film grain|skin pores?|live[- ]action|raw photo|8k uhd|cinematic photo|bokeh|depth of field)\b[,]?\s*", re.I)

def strict_prompt(prompt, style="tv"):
    """-> (text, removed_words). Removes realism words and puts the chosen style sentence first."""
    removed = [m.group(1).lower() for m in REALISM.finditer(prompt or "")]
    clean = re.sub(r"\s{2,}", " ", REALISM.sub("", prompt or "")).strip(" ,")
    phrase = STYLES.get(style, STYLES["tv"])[1]
    return (f"{phrase}, {clean}" if clean else phrase), removed
