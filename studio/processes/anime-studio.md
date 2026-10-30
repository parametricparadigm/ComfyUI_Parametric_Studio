# Anime studio

> From the author's earlier studio, cleaned for publication: private paths, ports and some lines were removed, so a step may read short and a screen it names may not exist here. Status in this studio: Untested.


Workspace **Anime** (left rail). Code: `earlier_studio/studio/anime.py`, UI `static/studio/Anime.js`, routes
`/api/studio/anime/*`, CPU join engine `anime`.

**Strict** = pinned to an anime look at every step: realism words (photo, photorealistic, 35mm, DSLR, film grain, skin
pores, live-action ...) are removed from every prompt and the chosen style sentence leads it (8 styles: TV, painterly
storybook, shonen, shojo, 90s, chibi, cyberpunk, mecha); pictures render on the anime pick (HiDream-O1); a saved
character is redrawn as an anime character once (Klein 9B reference edit of the headshot) and that anime anchor is the
reference for every later picture; clips animate an anime still on H3 · Stylised with the style as the look.

| Mode | Steps |
|---|---|
| 🖼 Pictures | 1-4 anime pictures (of the anime anchor when a character is picked) |
| 🎞 Clip | anime still (anchor or a fresh picture) -> one H3 stylised clip |
| 📺 Episode (long form) | premise/script -> 2-30 scenes planned by the LLM -> per scene a keyframe of the SAME character (edited from the anchor) -> an H3 stylised clip -> joined |

Untested on the GPU: the H3 stylised look text with these anime styles, and how well Klein keyframes hold the anime
character across scenes. First test: a 6-scene episode with a saved character, Draft quality.

## Redraw frame (2026-10-17)

The one anime redraw of a saved character has a **frame**: `head` (head and shoulders, from the sheet's headshot: the original behaviour), `waist` (waist up) or `full` (whole body), both from
the sheet's full-body shot (job field `character_roles`). Request field `frame`: `auto` (default: the narrowest frame that shows a picked tattoo's placement, else `head`, so a run
without a tattoo is unchanged), `head`, `waist`, `full`; the Anime page has a *Redraw frame* select. A tattoo on the back, the side or behind the ear cannot be shown by a front-view
redraw and the run note says so. See [tattoo-designer.md](tattoo-designer.md). Untested on the GPU.
