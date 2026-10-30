# PLAYBOOK.md: 02-Anima

## Prompt structure

*   **Standard Quality Prefix:** Begin prompts with `masterpiece, best quality, score_7, safe` to establish the baseline quality and safety rating expected by the model. [anima-turbo-lora-v0.2.md]
*   **Subject Definition:** Clearly define the subject using specific tags such as `1boy, adult man, knight`. [anima-turbo-lora-v0.2.md]
*   **Visual Details:** Include descriptive tags for appearance and environment, such as `silver armor, red cape, standing on a cliff edge at sunset, wind, dramatic clouds, detailed background`. [anima-turbo-lora-v0.2.md]
*   **Camera and Composition:** Specify the shot type and perspective, for example `wide shot, looking at viewer`. [anima-turbo-lora-v0.2.md]
*   **No Trigger Words:** The Anima Turbo LoRA does not require specific trigger words; the prompt structure relies on standard descriptive tags. [anima-turbo-lora-v0.2.md]

## Words and phrasing that work

*   **Quality Tags:** `masterpiece`, `best quality`, `score_7`, `safe`. [anima-turbo-lora-v0.2.md]
*   **Character Tags:** `1boy`, `adult man`, `knight`. [anima-turbo-lora-v0.2.md]
*   **Atmospheric/Environmental Tags:** `sunset`, `wind`, `dramatic clouds`, `detailed background`. [anima-turbo-lora-v0.2.md]
*   **Action/Pose Tags:** `standing on a cliff edge`, `looking at viewer`. [anima-turbo-lora-v0.2.md]
*   **Not in notes:** Specific negative prompt phrases or words that are known to degrade Anima output quality.

## Settings that worked

*   **Resolution:** Width 1024, Height 1024. [anima-turbo-lora-v0.2.md]
*   **Steps:** 8 steps. [anima-turbo-lora-v0.2.md]
*   **CFG Scale:** 1.0. [anima-turbo-lora-v0.2.md]
*   **Sampler:** `euler`. [anima-turbo-lora-v0.2.md]
*   **Scheduler:** `simple`. [anima-turbo-lora-v0.2.md]
*   **LoRA Strength:** 1.0. [anima-turbo-lora-v0.2.md]
*   **LoRA Loader:** Bake (using `LoraLoaderModelOnly` or `LoraLoader`). [anima-turbo-lora-v0.2.md]
*   **Base Model Context:** While the Turbo LoRA was tested with 8 steps/CFG 1.0, the base Anima model generally runs with 30-50 steps, CFG 4-5, and `er_sde` sampler according to the card recipe. [anima-turbo-lora-v0.2.md]

## Processes built on it

*   **Baking LoRAs:** The Anima Turbo LoRA is designed to be baked into the model using `LoraLoaderModelOnly` or `LoraLoader` because the base is BF16/FP16. [anima-turbo-lora-v0.2.md]
*   **Accelerator Usage:** The Anima Turbo LoRA functions as a speed accelerator/distill, allowing for faster generation (8 steps) compared to the base model's standard 30-50 steps. [anima-turbo-lora-v0.2.md]
*   **Not in notes:** Specific multi-step workflows, chaining processes, or integration with other specific model families beyond the Anima base.

## What to avoid

*   **Running without Base Model:** Do not attempt to run the Anima Turbo LoRA if the Anima base model is not on disk, as it will fail. [anima-turbo-lora-v0.2.md]
*   **Ignoring Loader Type:** Do not use non-baking loaders for this LoRA, as the BF16/FP16 base requires baking for proper integration. [anima-turbo-lora-v0.2.md]
*   **Not in notes:** Specific negative prompts, prohibited content types, or specific hardware limitations other than the requirement for the base model to be present.
