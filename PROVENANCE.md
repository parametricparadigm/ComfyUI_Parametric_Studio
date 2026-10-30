# Provenance (original code)
All code in `psn/` and `psn_nodes/` was written from the owner's specs and the design notes in the Parametric Studio knowledge base (section 42 guide, node specs, security deep dive). No third-party source code was copied, ported or closely paraphrased.

| component | design idea from | licence of that source | what we took |
|---|---|---|---|
| `psn/expr.py` safe evaluator | `yanhuifair/ComfyUI-FairLab` (whitelist AST evaluator, no code execution) | MIT | the idea only (walk a whitelisted AST instead of calling eval); no code |
| `psn/sandbox*.py` | `Duanyll/comfyui_functional` (opt-in switch for unsafe code) and the Oct 27 audit of 12 "run a Python string" packs | not reviewed for reuse | the lesson: default-deny, explicit opt-in; no code |
| `psn/orchestration.py`, `psn/graph.py`, `PSN_Branch`, `PSN_QualityGate`, `PSN_AttemptPlanner` | ComfyUI's lazy-evaluation convention (`check_lazy_status`) and the section 17/28 pack surveys | GPL-3.0 (ComfyUI core) for the convention only | the public node API shape; no ComfyUI code is included |
Rules: the repo is AGPL-3.0-or-later (see LICENSE); bundled third-party code is listed with its licence in THIRD_PARTY_NOTICES.md; third-party packs stay optional extras; record every new inspiration here.

Subagents (psn/subagents, psn_nodes/subagents.py): original code written 2026-10-29; no third-party code.

psn_nodes/gen/ (section 44 batch, merged 2026-10-30): written by the local Qwen3.8-27B node factory from our own knowledge-base specs (no third-party code), tests written alongside.
Reviewed by Claude before merge: static scan for eval/exec/network/subprocess/file writes (clean); n_4 metadata encryption was replaced (the generated repeating-key XOR with a built-in key
was not encryption) by scrypt + Fernet, no default key.

psn_nodes/latent.py (12 torch-backed latent nodes, 2026-10-30): original code written by Claude for this project; tested on CPU tensors. Replaces the factory's section-24 latent modules, which only handled plain lists
(their docstring says tensor conversion is "out of scope") and so could not run on a real LATENT; those were not merged.
