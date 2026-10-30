# Contributing

Issues and pull requests are welcome. Please open an issue first for anything large.

## Ground rules

- **Licence.** Your contribution is licensed under AGPL-3.0-or-later. Code you copy or adapt from elsewhere must have a compatible licence, keep its notice, and be listed in [docs/CREDITS.md](docs/CREDITS.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Leave the licence files in `studio/web/vendor/` alone.
- **Open edition only.** No paid API connectors, partner nodes or paid SDKs (see [EDITIONS.md](EDITIONS.md)). `tests/test_open_edition_no_paid_apis.py` fails the build if a paid host appears. A workflow in `workflows/` must run on local weights.
- **SFW and lawful.** No adult content, no unlicensed characters, brands or styles in presets, prompts, packs or lessons, and no real people's likenesses without permission.
- **No personal details.** No private paths, usernames, tokens or machine names in code, workflows or docs. Paths come from environment variables.
- **Say only what is true.** A feature's status in the README changes when it has been shown to work, not when the code is merged. Say which machine it ran on.

## Setting up

```bash
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn python-multipart pydantic numpy pillow pytest httpx
COMFYUI_URL=http://127.0.0.1:8188 python -m studio.server
```

The web app has no build step: edit files under `studio/web/` and reload. Preact and htm load from `studio/web/vendor/`.

## Tests

```bash
python -m pytest -q tests/test_llm_tiers.py tests/test_studio_*.py tests/test_install.py   # fast subset, as in CI
python -m pytest -q                                                                         # everything; some node tests need torch; JS lane tests need node
```

Tests must never touch real accounts or live services. Stub HTTP, the filesystem paths and any port in a fixture, or start a stub server on a port the test chose itself. `python .github/scripts/repo_checks.py` runs the licence, secret and private-path checks.

## Common changes

- **A new goal:** a graph in `workflows/` with `${placeholders}` for what may change, an entry in `GOALS` in `studio/goals.py` that states the model's licence, its files with sizes and SHA-256 in `studio/models_manifest.json` (`scripts/build_manifest.py` makes these), a row in [MODELS.md](MODELS.md), and a test.
- **A new node:** add it under `psn_nodes/`, with `INPUT_TYPES`, `RETURN_TYPES` and tests that run without a GPU.
- **A new subagent role:** one entry in `psn/subagents/roles.py`, with a good and a bad case in `tests/test_subagents.py`.

## Pull requests

Keep them small and explain why. Include the output of the tests you ran. Say what you could not test, such as an operating system or GPU you do not have.
