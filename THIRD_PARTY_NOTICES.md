# Third-party notices

This project is AGPL-3.0-or-later. It bundles or builds on the following, each under its own licence (all are compatible with AGPL-3.0):

| Component | Where | Licence |
|---|---|---|
| Preact 10.24.3 | `studio/web/vendor/preact.mjs`, `hooks.mjs` (licence text beside them) | MIT |
| htm 3.1.1 | `studio/web/vendor/htm.mjs` | Apache-2.0 |
| three.js r160 (core, OrbitControls, GLTFLoader, BufferGeometryUtils) | `studio/web/vendor/` | MIT |
| awesome-claude-agents (role playbook excerpts) | `psn/subagents/playbooks/` (licence file included) | MIT |
| Archivo (font) | `studio/web/vendor/fonts/` (licence text beside it) | SIL OFL 1.1 |
| Inter (font) | `studio/web/vendor/fonts/` (licence text beside it) | SIL OFL 1.1 |
| ComfyUI | runtime dependency, not bundled; the node packs load inside it | GPL-3.0 |

AGPL-3.0 section 13 and GPL-3.0 section 13 allow the two to be combined. Other Python dependencies are installed from PyPI under their own licences (see the installer's lock files).

**Models are not part of this repository and are not relicensed.** Each model keeps its author's licence, shown on its tile in the studio and listed in MODELS.md: for example FLUX.2 Klein 4B and Wan 2.2 are Apache-2.0; FLUX.3 Klein, LTX-2.x, MiniMax H3 and MiniMax Music 3 use their authors' community licences; Anima is non-commercial. Read each licence before using outputs commercially.
