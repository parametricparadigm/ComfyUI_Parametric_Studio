# PLAYBOOK.md: 18-Pony-Illustrious-NoobAI

## Prompt structure

*   **Danbooru-tag prompts:** For tag-based models (NoobAI/Illustrious), use Danbooru-tag prompts rather than natural language prose. [deliverables-best-practice-2026-10-17.md]
*   **Quality tags first:** Place quality tags at the front of the prompt. [deliverables-best-practice-2026-10-17.md]
*   **Dialect distinction:** The prompt library distinguishes between `sdxl-tags` (booru tag lists) and `sdxl-nl` (descriptive text) for this family; retrieval ensures tag lists are not mixed with natural language targets. [prompt-library.md]
*   **Base model tagging:** Records are tagged with a `base` field to distinguish between `pony`, `illustrious`, and `noobai` variants within the SDXL family. [prompt-library.md]
*   **Not in notes:** Specific ordering rules for subject vs. style tags beyond "quality tags in front" are not detailed in the provided documents.

## Words and phrasing that work

*   **Danbooru tags:** The primary phrasing style is Danbooru tags. [deliverables-best-practice-2026-10-17.md]
*   **Not in notes:** Specific high-impact quality tags (e.g., "masterpiece", "best quality") or specific style keywords are not listed in the provided documents.
*   **Not in notes:** Negative prompt examples specific to Pony/Illustrious/NoobAI are not provided in the documents (only general SDXL photoreal negatives or Maeve's specific character negatives are shown).

## Settings that worked

*   **Sampler:** Use Euler or Euler a. [deliverables-best-practice-2026-10-17.md]
*   **CFG (Epsilon):** 5-6. [deliverables-best-practice-2026-10-17.md]
*   **CFG (v-pred):** Approximately 3.5-5.5. [deliverables-best-practice-2026-10-17.md]
*   **Clip Skip:** No clip skip (set to 1 or disabled). [deliverables-best-practice-2026-10-17.md]
*   **Resolution (NoobAI-XL 1.1):** Total area ~1024^2. [deliverables-best-practice-2026-10-17.md]
*   **Best Buckets (NoobAI-XL 1.1):** 768x1344, 832x1216, 896x1152, 1024x1024, 1152x896, 1216x832, 1344x768. [deliverables-best-practice-2026-10-17.md]
*   **Steps (NoobAI-XL 1.1):** 25-30 steps. [deliverables-best-practice-2026-10-17.md]
*   **Not in notes:** Specific step counts or CFG ranges for Pony and Illustrious checkpoints are not explicitly detailed in the provided text, only the general "Tag models (NoobAI/Illustrious)" recommendation.

## Processes built on it

*   **Prompt Library Retrieval:** The studio's Prompt Library workspace allows searching and filtering distinct prompts for the SDXL family (including Pony, Illustrious, NoobAI). [prompt-library.md]
*   **Dialect-Isolated Retrieval:** The system prevents cross-dialect retrieval; SDXL/Pony/Illustrious/NoobAI tag lists are never offered to FLUX targets, and vice versa. [prompt-library.md]
*   **Safety Screening:** All prompts from the library are screened by the studio text guard (`character_policy.prompt_problems`) on import and on every text served. [prompt-library.md]
*   **Import Cap:** The studio import caps each new family (including SDXL) at 60,000 records by default to manage memory, prioritizing best-reacted prompts. [prompt-library.md]
*   **Character Mode Integration:** Character profiles (like Maeve) can be used with these models, though the "Suggested model" field in the profile is currently blank for character mode to fill. [PROFILE.md]
*   **Not in notes:** Specific workflow JSONs or ComfyUI node configurations for these models are not included in the provided documents.

## What to avoid

*   **Natural Language for Tag Models:** Do not use natural language prose for tag-based models (NoobAI/Illustrious); use Danbooru tags. [deliverables-best-practice-2026-10-17.md]
*   **Clip Skip:** Do not use clip skip for these tag models. [deliverables-best-practice-2026-10-17.md]
*   **Cross-Dialect Mixing:** Do not mix booru tag lists with natural language targets in retrieval or prompting. [prompt-library.md]
*   **Not in notes:** Specific negative prompt lists to avoid for Pony/Illustrious/NoobAI are not provided in the documents.
*   **Not in notes:** Specific pitfalls regarding "shizo prompting" or over-prompting are mentioned for Lustify (a different model) but not explicitly for Pony/Illustrious/NoobAI in the provided text.
