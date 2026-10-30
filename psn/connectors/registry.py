"""What the studio can plug into, honestly labelled. kind: catalogue (find + download models) | remote (generate on someone else's machine). Open edition = fully local generation:
remote connectors stay off there unless the owner sets PSN_ALLOW_FREE_REMOTE=1. Facts below are from each service's own docs as read on 2026-10-30; limits change often."""
import os
CONNECTORS = {
 "civitai": {"kind": "catalogue", "status": "built", "needs_token": "downloads (CIVITAI_TOKEN)", "docs": "https://developer.civitai.com/site/", "note": "Search is anonymous; downloads need a token. SFW-only here. Per-model licence flags are shown."},
 "huggingface": {"kind": "catalogue", "status": "built", "needs_token": "gated repos only (HF_TOKEN)", "docs": "https://huggingface.co/docs/huggingface_hub/", "note": "Hub API is free with rate limits. Hosted inference via Inference Providers is NOT free on the Free plan per a third-party table; HF's own page says a free tier exists - unresolved, so not wired."},
 "ai_horde": {"kind": "remote", "status": "planned", "needs_token": "optional (anonymous key works, lowest priority)", "docs": "https://stablehorde.net/", "note": "Free, volunteer GPUs, slow, built-in NSFW censor; a third-party test saw one of four harmless prompts blocked. urllib got 403 from its Cloudflare in that test, requests worked."},
 "pollinations": {"kind": "remote", "status": "planned", "needs_token": "yes (current gen API); old image URL is keyless, watermarked, 1 per 45 s", "docs": "https://gen.pollinations.ai/docs", "note": "Current API spends Pollen credits and needs a key: not free in the sense the Open edition requires."},
 "cloudflare_workers_ai": {"kind": "remote", "status": "planned", "needs_token": "yes (free account)", "docs": "https://developers.cloudflare.com/workers-ai/", "note": "10,000 Neurons/day free per a third-party table; verify on Cloudflare's own page before wiring."},
}
def available(edition=None):
    """Connectors usable under the current edition. Remote ones need extended edition or PSN_ALLOW_FREE_REMOTE=1."""
    ed = edition or os.environ.get("PSN_EDITION", "open"); remote_ok = ed == "extended" or os.environ.get("PSN_ALLOW_FREE_REMOTE") == "1"
    return {k: v for k, v in CONNECTORS.items() if v["status"] == "built" and (v["kind"] == "catalogue" or remote_ok)}
