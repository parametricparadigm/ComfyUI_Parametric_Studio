# PROMPTING - 03-Audio-FX-separation-foley-models

## Prompt Structure and Inputs

The family supports text-to-audio, video-to-audio, and text-video-to-audio tasks [MODEL.md]. For **HunyuanVideo-Foley**, inputs include video and/or text [MODEL.md]. The model employs a hybrid architecture where semantic features are extracted via a pre-trained text encoder [https://huggingface.co/tencent/HunyuanVideo-Foley/raw/main/README.md]. The model intelligently balances visual and textual information analysis to comprehensively orchestrate sound effect elements [https://huggingface.co/tencent/HunyuanVideo-Foley/raw/main/README.md].

For **MM-Audio**, inputs include video or text [MODEL.md]. It utilizes a CLIP Vision Encoder to encode visual features for conditioning [MODEL.md].

For **ControlFoley**, inputs include video or audio [MODEL.md].

For **SAM-Audio**, inputs are audio [MODEL.md].

For **Speech Enhancement** models (MossFormer2, VoxLock), inputs are mixed audio or video (for Target Speaker Extraction) [MODEL.md].

For **Audio Source Separation** (ConvTasNet), inputs are mixed audio at 8kHz [MODEL.md].

## Language

The HunyuanVideo-Foley model is tagged with the languages `en` and `zh` [https://huggingface.co/AEmotionStudio/hunyuanvideo-foley-models/raw/main/README.md].

## Text Encoder Behavior

In **HunyuanVideo-Foley**, the text processing component extracts semantic features via a pre-trained text encoder [https://huggingface.co/tencent/HunyuanVideo-Foley/raw/main/README.md]. These features are processed alongside visual features in multimodal transformer blocks [https://huggingface.co/tencent/HunyuanVideo-Foley/raw/main/README.md].

In **MM-Audio**, a CLIP Vision Encoder is used to encode visual features for audio generation conditioning [MODEL.md].

## Prompt Length and Specifics

Not in sources: Specific prompt length limits, character counts, or token limits for any model in this family.

## Negative Prompts

Not in sources: Usage of negative prompts for any model in this family.

## Style and Camera Vocabulary

Not in sources: Specific style or camera vocabulary guidelines for prompting. The sources state that the model generates audio "synchronized and semantically aligned with complex video scenes" [https://huggingface.co/tencent/HunyuanVideo-Foley/raw/main/README.md], but do not provide a vocabulary list for describing these scenes in text prompts.

## Inference Settings

Not in sources: Specific inference parameters such as number of diffusion steps, guidance scale, or sampling method for HunyuanVideo-Foley, ControlFoley, MM-Audio, and SAM-Audio [MODEL.md].

## Node Integration for Prompting

In the **if-ai__ComfyUI_HunyuanVideoFoley** pack, the `HunyuanVideoFoley` node accepts a `STRING` input for the prompt [WORKFLOW_PLAN.md]. The `HunyuanVideoFoleyModelLoader` node outputs a `STRING` type [WORKFLOW_PLAN.md].

## Unknowns

- The exact Python dependencies required for each node pack are not listed [MODEL.md].
- The specific API graph configurations for each model are not provided [MODEL.md].

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
