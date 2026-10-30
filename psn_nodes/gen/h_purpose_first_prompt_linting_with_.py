"""Purpose-first prompt linting with filler detection and specific retry instructions.

ComfyUI custom node: takes a text prompt, quantifies filler words per category,
and emits a concrete rewrite instruction (retry message) plus a beat plan for the
target clip duration. Pure Python + torch (CPU) only.
"""

import re
import torch

CAT = "ParametricStudio/PromptLinting"

# Filler lexicon: category -> words/phrases (lowercase).
FILLER_LEXICON = {
    "hedging": {
        "very", "really", "quite", "rather", "somewhat", "pretty", "fairly",
        "extremely", "incredibly", "super", "so", "too", "just", "basically",
        "actually", "literally", "kind of", "sort of", "a bit", "a little",
    },
    "vague": {
        "nice", "good", "great", "cool", "awesome", "beautiful", "stunning",
        "amazing", "wonderful", "fantastic", "some", "something", "various",
        "etc", "stuff", "things", "like", "kind", "sort", "overall", "generally",
    },
    "empty": {
        "in order to", "due to the fact that", "it is worth noting that",
        "as a matter of fact", "needless to say", "in general", "in summary",
        "basically", "essentially", "simply", "merely", "only", "purely",
    },
    "redundant": {
        "very very", "really really", "so so", "a lot of", "lots of",
        "each and every", "first and foremost", "at this point in time",
    },
}

# Words that signal purpose (verbs of intent / concrete nouns).
PURPOSE_HINTS = {
    "show", "reveal", "emphasize", "highlight", "focus", "capture", "frame",
    "pan", "zoom", "track", "cut", "dissolve", "light", "shadow", "color",
    "texture", "motion", "camera", "lens", "angle", "shot", "close-up",
    "wide", "medium", "detail", "contrast", "depth", "atmosphere",
}


def _tokenize(text):
    """Split prompt into lowercase word tokens, keeping multi-word phrases detectable."""
    if not isinstance(text, str):
        raise TypeError("prompt must be a string")
    return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())


def _find_filler_spans(text):
    """Return list of (category, phrase, start, end) for filler occurrences."""
    spans = []
    low = text.lower()
    for category, phrases in FILLER_LEXICON.items():
        for phrase in phrases:
            start = 0
            while True:
                idx = low.find(phrase, start)
                if idx == -1:
                    break
                end = idx + len(phrase)
                # word-boundary check
                before_ok = idx == 0 or not low[idx - 1].isalnum()
                after_ok = end >= len(low) or not low[end].isalnum()
                if before_ok and after_ok:
                    spans.append((category, phrase, idx, end))
                start = end
    spans.sort(key=lambda s: (s[2], -s[3]))
    # drop overlapping spans (keep earliest/longest)
    kept = []
    last_end = -1
    for cat, phrase, s, e in spans:
        if s >= last_end:
            kept.append((cat, phrase, s, e))
            last_end = e
    return kept


def beat_plan(secs):
    """Generate 3-5 beats on a half-second grid tiling the clip duration.

    Returns list of (label, start, end) tuples.
    """
    secs = float(secs)
    if secs <= 0:
        raise ValueError("secs must be positive")
    grid = int(round(secs * 2))  # half-second cells
    if grid < 2:
        grid = 2
    n_beats = 3 if grid <= 6 else (4 if grid <= 12 else 5)
    labels = ["hook", "build", "payoff", "button", "tag"]
    # distribute cells as evenly as possible
    base = grid // n_beats
    extra = grid % n_beats
    beats = []
    pos = 0
    for i in range(n_beats):
        cells = base + (1 if i < extra else 0)
        start = pos / 2.0
        end = (pos + cells) / 2.0
        beats.append((labels[i], start, end))
        pos += cells
    return beats


def filler_report(text, keep_clauses=False):
    """Analyze prompt body: share of words that are filler/purposeful/neutral,
    worst filler category, and the offending phrases.
    """
    tokens = _tokenize(text)
    n_words = len(tokens)
    spans = _find_filler_spans(text)
    filler_words = 0
    cat_counts = {c: 0 for c in FILLER_LEXICON}
    phrases = []
    for cat, phrase, s, e in spans:
        w = len(phrase.split())
        filler_words += w
        cat_counts[cat] += w
        phrases.append({"category": cat, "phrase": phrase, "start": s, "end": e})
    purposeful_words = sum(1 for t in tokens if t in PURPOSE_HINTS)
    neutral_words = max(0, n_words - filler_words - purposeful_words)
    if n_words == 0:
        shares = {"filler": 0.0, "purposeful": 0.0, "neutral": 0.0}
    else:
        shares = {
            "filler": filler_words / n_words,
            "purposeful": purposeful_words / n_words,
            "neutral": neutral_words / n_words,
        }
    worst_cat = max(cat_counts, key=lambda c: cat_counts[c]) if any(cat_counts.values()) else None
    report = {
        "n_words": n_words,
        "filler_words": filler_words,
        "purposeful_words": purposeful_words,
        "neutral_words": neutral_words,
        "shares": shares,
        "cat_counts": cat_counts,
        "worst_category": worst_cat,
        "phrases": phrases,
    }
    if keep_clauses:
        report["kept_clauses"] = _kept_clauses(text, spans)
    return report


def _kept_clauses(text, spans):
    """Return prompt with filler spans blanked out (for keep_clauses mode)."""
    out = list(text)
    for cat, phrase, s, e in spans:
        for i in range(s, e):
            out[i] = " "
    return re.sub(r"\s+", " ", "".join(out)).strip()


def retry_message(report, secs=5.0, dialogue=False, words=None, body_words=0):
    """Build a specific rewrite instruction quoting problematic phrases and budget."""
    if report.get("n_words", 0) == 0:
        return "Prompt is empty. Write a purpose-first prompt: state the shot, the motion, and the look in concrete terms."
    parts = []
    worst = report.get("worst_category")
    phrases = report.get("phrases", [])
    if phrases:
        quoted = ", ".join('"%s"' % p["phrase"] for p in phrases[:5])
        parts.append("Remove filler (%s): %s." % (worst or "mixed", quoted))
    else:
        parts.append("No filler detected; keep the prompt concise.")
    share = report["shares"]["filler"]
    parts.append("Filler share is %.0f%% of words; target under 10%%." % (share * 100))
    # word budget
    if words is None:
        words = (max(10, int(secs * 6)), max(20, int(secs * 12)))
    lo, hi = words
    parts.append("Rewrite in %d-%d words (currently %d)." % (lo, hi, report["n_words"]))
    if dialogue:
        parts.append("Keep dialogue as quoted speech, one line max.")
    # beat structure
    beats = beat_plan(secs)
    beat_desc = ", ".join("%s %.1f-%.1fs" % (b[0], b[1], b[2]) for b in beats)
    parts.append("Structure: %s." % beat_desc)
    parts.append("Lead with the purpose: what the shot must show, then how (camera/light), then style.")
    return " ".join(parts)


def _s(x):
    """Extract tensor from LATENT dict or pass through tensor."""
    if isinstance(x, dict):
        return x["samples"]
    return x


def _out(latent, samples):
    """Wrap samples back into LATENT dict preserving other keys."""
    if isinstance(latent, dict):
        d = dict(latent)
        d["samples"] = samples
        return d
    return samples


class PSN_PromptFillerLint:
    """Lint a text prompt: quantify filler words per category and emit a
    purpose-first rewrite instruction with a beat plan for the clip duration."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "secs": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 60.0, "step": 0.5}),
                "dialogue": ("BOOLEAN", {"default": False}),
                "word_min": ("INT", {"default": 0, "min": 0, "max": 500}),
                "word_max": ("INT", {"default": 0, "min": 0, "max": 1000}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "FLOAT")
    RETURN_NAMES = ("retry_message", "report_json", "filler_words", "filler_share")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, prompt, secs, dialogue, word_min, word_max):
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string")
        if secs <= 0:
            raise ValueError("secs must be positive")
        report = filler_report(prompt)
        words = None
        if word_min > 0 and word_max >= word_min:
            words = (word_min, word_max)
        msg = retry_message(report, secs=secs, dialogue=dialogue, words=words)
        import json as _json
        report_json = _json.dumps({
            "n_words": report["n_words"],
            "filler_words": report["filler_words"],
            "purposeful_words": report["purposeful_words"],
            "neutral_words": report["neutral_words"],
            "shares": report["shares"],
            "cat_counts": report["cat_counts"],
            "worst_category": report["worst_category"],
            "phrases": report["phrases"],
            "beats": beat_plan(secs),
        })
        filler_share = float(report["shares"]["filler"])
        return (msg, report_json, int(report["filler_words"]), filler_share)


class PSN_PromptBeatPlan:
    """Emit the beat timeline (hook/build/payoff/button) for a clip duration,
    as a string and a tensor of beat boundaries [B=1, n_beats+1] in seconds."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "secs": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 60.0, "step": 0.5}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("beat_plan_text", "beat_boundaries")
    FUNCTION = "run"
    CATEGORY = CAT

    def run(self, secs):
        if secs <= 0:
            raise ValueError("secs must be positive")
        beats = beat_plan(secs)
        text = " | ".join("%s %.1f-%.1fs" % (b[0], b[1], b[2]) for b in beats)
        boundaries = [b[1] for b in beats] + [beats[-1][2]]
        tensor = torch.tensor(boundaries, dtype=torch.float32).unsqueeze(0)
        return (text, tensor)


NODE_CLASS_MAPPINGS = {
    "PSN_PromptFillerLint": PSN_PromptFillerLint,
    "PSN_PromptBeatPlan": PSN_PromptBeatPlan,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_PromptFillerLint": "Prompt Filler Lint (Purpose-First)",
    "PSN_PromptBeatPlan": "Prompt Beat Plan",
}
