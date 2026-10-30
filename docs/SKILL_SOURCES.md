# Skill and library sources (verified 2026-10-30 via GitHub API; nothing cloned or executed)

Rule: ideas and recipes only from permissively licensed repos; read any script before running it; never run `npx ... install` unreviewed. Rewrite, do not vendor, unlicensed material.

## Adopt (licence-safe, active)
| Repo | Licence | Use in the studio |
|---|---|---|
| CloudAI-X/threejs-skills | MIT | 3D viewer, hero, glTF loading, shaders, perf (vanilla path, not R3F) |
| pbakaus/impeccable | Apache-2.0 | polish / critique / audit vocabulary for UI review passes (copy the markdown, skip the installer) |
| jakubkrehel/make-interfaces-feel-better | MIT | small-detail polish checklist (radii, shadows, motion restraint, tabular numbers) |
| paper-design/shaders | Apache-2.0 | candidate runtime shader backgrounds (pin version; verify no-build ESM) |
| MengTo/Skills | MIT | WebGL/shader recipes, no-ai-design-slop; cherry-pick after reading |
| Leonxlnx/taste-skill | MIT | anti-slop art-direction pass; review inspector scripts first |
| nextlevelbuilder/ui-ux-pro-max-skill | MIT | design-system generation ideas |
| bergside/awesome-design-skills | MIT | theme/token presets |
| ahujasid/mcp-for-blender | MIT | asset prep only (socket bridge, review first) |
| huggingface/skills | Apache-2.0 | hf-cli, local-models, datasets |

## Skip
uxuiprinciples/agent-skills (no licence, paid-API funnel); ceorkm/mobile-app-ui-design (mobile, no LICENSE file);
carmahhawwari/ui-design-brain (stale); freshtechbro/claudedesignskills (stale, superseded by threejs-skills);
21st-dev/magic-mcp (hosted, API key); shadcn-ui/ui (React/Tailwind, no-build Preact studio);
vercel-labs/agent-skills (no LICENSE file); "AI Vision Debug MCP" (identity unconfirmed, cloud Gemini).

## Caveats
Star counts on the three largest repos (~420/day) could not be audited for spikes. Some repos ship executable scripts.
