# PLAYBOOK.md: 06-Depth-normals-pose

## Prompt structure

The provided notes do not contain a specific prompt structure for a model family named "06-Depth-normals-pose." The documents describe a "10 poses" process that utilizes several different underlying engines (Qwen-Image 2.1, Klein 9B, Boogu, FLUX.3) rather than a single unified model family with that specific name.

For the **Text instruction** routes (Qwen-Image 2.1 edit and Klein 9B edit), the prompt structure is defined as a raw instruction that is never enhanced. The standard template is:
`Same person, same setting, same outfit and lighting. New pose: <pose>. Keep the face, hair, outfit and the background unchanged, and keep the camera angle and framing.`

Pronouns (woman/man/person and her/his/their) are derived from the picture's prompt and the character's description.

For the **Pose control** route (Klein 9B + skeleton), the prompt structure is fixed and does not include the user's typed pose words. The entire prompt is the trigger: `apply pose from image 1 with reference from image 2`. In this mode, image 1 is the drawn skeleton and image 2 is the source picture.

For **Boogu Edit-Turbo**, the structure is: `Change the person's pose to <pose>. Keep the face, ... unchanged.`.

For **FLUX.3 Klein edit**, the reference is written as `<ref_image_0>`.

Not in notes: Specific prompt syntax or structure for a model explicitly labeled "06-Depth-normals-pose."

## Words and phrasing that work

A pose description for the `<pose>` variable names the stance, where the arms and feet are, and the framing. For example:
*   "standing, facing forward, arms at sides, relaxed shoulders, full body visible"
*   "walking mid-stride, one foot forward, arms in motion, full body"
*   "leaning with back against a wall, one knee bent, arms relaxed, full body"

For the **Pose control** route, specific words are not sent to the model; instead, a skeleton is drawn for each pose.

If the scene involves a held object like a phone, the following phrasing is appended after the pose: `The person keeps holding the phone in the same hand as in the picture, and both arms stay visible.`.

If a re-render is needed after a failed anatomy check, the following phrasing is added: `Both arms, both hands and anything held in them must stay fully visible, with no missing or extra limbs.`.

Not in notes: Specific "magic words" or trigger phrases unique to a "06-Depth-normals-pose" model family.

## Settings that worked

The notes specify settings for the engines used in the "10 poses" process, but do not list settings for a model named "06-Depth-normals-pose."

**Qwen-Image 2.1 edit (`qwen21:edit`):**
*   Precision: bf16
*   Steps: 40
*   CFG: 1
*   Peak VRAM: 36 GiB
*   Time: ~12 s per picture

**Klein 9B edit (`img:klein_edit`):**
*   Steps: 4
*   Peak VRAM: 30 GiB
*   Time: ~4 s per picture

**Klein 9B + consistency LoRA:**
*   LoRA: `f2k_9B_lcs_consist`
*   Weight: 0.8
*   Peak VRAM: 30 GiB
*   Time: ~4.5 s per picture

**Pose control (Klein 9B + skeleton):**
*   LoRA: RefControl pose LoRA
*   Weight: 0.9
*   Mode: bypass
*   Peak VRAM: 30 GiB
*   Time: ~8 s per picture

**Boogu Edit-Turbo (`img:boogu_edit`):**
*   Peak VRAM: 31 GiB
*   Time: ~5 s per picture

**FLUX.3 Klein edit (`flux3:edit`):**
*   Peak VRAM: 26 GiB
*   Time: ~6 s per picture

**General:**
*   Free-VRAM floor: 4 GiB
*   Queueing: `queue_when_free`

Not in notes: Settings specific to a "06-Depth-normals-pose" model family.

## Processes built on it

The primary process built on these capabilities is the **"10 poses"** feature, which turns a finished picture into a set of new poses.

**Workflow:**
1.  Press the "🧍 10 poses" button on a finished image card.
2.  The system detects framing and assumes scene elements (e.g., holding a phone).
3.  The user can edit the plan: change pose words, remove/add lines, change count (1-12), force framing, or pick the model.
4.  The system runs N ordinary studio jobs in sequence via `/api/studio/generate`.
5.  Results are displayed as a contact sheet with check chips and reasons.
6.  Failed checks trigger a re-render once with a new seed; if it fails again, the user must manually Keep or Re-render.

**Model Selection Logic:**
*   **Primary:** Qwen-Image 2.1 edit (auto first) due to measured identity (ArcFace 0.751).
*   **Fallback:** Klein 9B edit (auto fallback) for speed, though with weaker identity (ArcFace 0.714).
*   **Consistency:** Klein 9B + consistency LoRA is available but never auto-picked until proof runs show it helps.
*   **Pose Control:** Klein 9B + skeleton is an option but marked as "unproven".
*   **Preview:** Boogu Edit-Turbo is for fast previews only.
*   **FLUX.3:** Only if picked and lane is up; pose change is a known weak spot.

Not in notes: Processes specifically built on a model family named "06-Depth-normals-pose."

## What to avoid

*   **Stacking LoRAs:** The two LoRAs (consistency and pose control) are never stacked because the model has one bypass slot and both model pages make their own sentence the prompt.
*   **Using Pose Control for Typed Poses Without Skeletons:** A typed pose has no skeleton, so it is refused in
