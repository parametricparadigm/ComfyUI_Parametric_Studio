"""One safe-for-work check for what people type into Create, recipes, apps and schedules. The word list is the one schedules already used. Negative prompts are not checked: they name what to keep out."""
import re
from fastapi import HTTPException
BAD = re.compile(r"\b(nsfw|nude|naked|lingerie|porn|hentai|explicit|erotic|topless|fetish|onlyfans|sex\w*|gore)\b", re.I)
MESSAGE = "This studio makes safe-for-work pictures, video and music only, and something in your text is outside that. Please reword it and try again."
def flagged(*texts): return any(isinstance(t, str) and BAD.search(t) for t in texts)
def check(*texts):
    if flagged(*texts): raise HTTPException(400, MESSAGE)
