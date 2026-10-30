# Editions (owner decision, 2026-10-29)
- OPEN edition (this repo, the contest entry): full open source, SFW, and nothing paid. No paid API connectors, no partner nodes, no API keys for paid services. Free bridges only (Telegram Bot API, Discord/Slack webhooks, ntfy, local OSC, Tailscale/LAN remote ComfyUI, folder round-trip). A test (`tests/test_open_edition_no_paid_apis.py`) fails the build if paid-API hosts or SDKs appear in the source.
- EXTENDED edition (separate package/repo, not in the contest entry): may add paid API connectors (OpenAI, Anthropic, Kling, Runway, Higgsfield and similar) behind the same bridge policy (off by default, keys in a chmod-600 config, host allow-lists, rate limits, explicit owner opt-in for spending).
The two share the PSN core (`psn/`); the extended package only adds connectors.

## Moved to the EXTENDED edition (owner, 2026-10-29)
Social/auto-publishing connectors: MLTask (LinkedIn, TikTok, Twitter), DWA (DeviantArt), and similar "post my output to a platform" packs. They need platform APIs (some paid), OAuth and account access, and posting is an outward-facing action: nothing auto-posts without the owner's explicit approval. Not part of the open/contest edition. (Scrapers/downloaders such as the Instagram downloader stay out of every edition's showcase.)

## Partner nodes
The open edition hides every app and edit tool that uses a node ComfyUI flags `api_node` in `/object_info`, and does not register `PSN_Gemini_Prompt_Crafter`. They appear only with `PSN_EDITION=extended`, which is reserved for a later edition.

## Building the Extended edition
`python scripts/assemble_extended.py` builds it beside the open tree. With `PSN_EDITION=extended`, the Apps page lists ComfyUI's partner workflows and the Designers page offers Connect your Printify.
