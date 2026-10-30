# PROMPTING - 25-TTS-voice-models

## Prompt Structure and Inputs

The "prompt" for this model family is not a single text string but a combination of target text, reference audio (for cloning), and specific control parameters or instructions, depending on the model variant.

**FireRedTTS-1S**
*   **Structure**: Requires `prompt_wav` (reference audio), `prompt_text` (transcript of the reference audio), `text` (target text to synthesize), and `lang` (language code).
*   **Reference Audio**: The reference audio (`prompt_wav`) should be 3–10 seconds long. It must be smooth and natural, and the accompanying `prompt_text` must be accurate to enhance stability and naturalness [MODEL.md] [SOURCES.md].
*   **Text Normalization**: A boolean setting `use_tn` controls text normalization. The source notes that `use_tn=True` was enabled for test-hard evaluation [MODEL.md] [SOURCES.md].
*   **Silence Handling**: Removing long silences (>1s) in the middle of `prompt_wav` may bring better stability. If stability problems occur due to many long silences, a tool (`tools/process_prompts.py`) is recommended to remove them [PUBLIC README https://huggingface.co/FireRedTeam/FireRedTTS/raw/main/README.md].

**Chatterbox**
*   **Structure**: Requires a `text` string. For voice cloning, an optional `audio_prompt_path` is provided. For multilingual models, a `language_id` tag is required [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].
*   **Language Matching**: The reference clip (audio prompt) must match the specified language tag. If they do not match, language transfer outputs may inherit the accent of the reference clip’s language [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].

**Qwen3-TTS**
*   **Structure**: Requires `text`. Depending on the variant, it accepts optional audio input (for cloning) or natural language instructions (for voice design/control) [MODEL.md].
*   **Voice Design**: The `Qwen3-TTS-12Hz-1.7B-VoiceDesign` variant performs voice design based on user-provided descriptions [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **Custom Voice**: The `Qwen3-TTS-12Hz-1.7B-CustomVoice` variant provides style control over target timbres via user instructions, supporting 9 premium timbres [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **Base/Cloning**: The `Qwen3-TTS-12Hz-1.7B-Base` and `0.6B-Base` variants are capable of 3-second rapid voice clone from user audio input [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].

**GPT-SoVITS**
*   **Structure**: Requires `text` and an optional vocal sample. For zero-shot TTS, a 5-second vocal sample is used. For few-shot TTS, 1 minute of training data is used [MODEL.md].

**Kyutai TTS**
*   **Structure**: Requires `text` and a speaker embedding or reference audio [MODEL.md].

## Prompt Length and Reference Audio Duration

*   **FireRedTTS**: Reference audio duration is recommended to be 3–10 seconds [MODEL.md] [SOURCES.md].
*   **GPT-SoVITS**: Zero-shot requires a 5-second vocal sample; few-shot requires 1 minute of training data [MODEL.md].
*   **Qwen3-TTS**: Base models support 3-second rapid voice clone from audio input [MODEL.md] [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **Target Text Length**: Not in sources: Specific maximum or recommended character/word limits for the target text string.

## Language

*   **FireRedTTS**: Uses a `lang` parameter (e.g., `"zh"` for Chinese) [SOURCES.md].
*   **Chatterbox**: Uses a `language_id` parameter (e.g., `"fr"`, `"zh"`) for multilingual models. Supports 23+ languages including Arabic, Danish, German, Greek, English, Spanish, Finnish, French, Hebrew, Hindi, Italian, Japanese, Korean, Malay, Dutch, Norwegian, Polish, Portuguese, Russian, Swedish, Swahili, Turkish, and Chinese [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].
*   **Qwen3-TTS**: Supports 10 major languages: Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, and Italian [MODEL.md] [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **GPT-SoVITS**: Supports cross-lingual synthesis for English, Japanese, Korean, Cantonese, and Chinese [MODEL.md].

## Negative Prompts

Not in sources: The provided evidence does not mention the use of "negative prompts" for any model in this family.

## Style, Camera, and Control Vocabulary

Since these are Text-to-Speech models, "camera" vocabulary is not applicable. Style and control are achieved through specific parameters or natural language instructions:

**Chatterbox**
*   **Exaggeration**: A parameter `exaggeration` (default 0.5) controls emotion/intensity. Higher values (e.g., ~0.7+) are used for dramatic speech and tend to speed up speech [MODEL.md] [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].
*   **CFG (Classifier-Free Guidance)**: A parameter `cfg` (default 0.5) controls stability and pacing. Lower values (e.g., ~0.3) are recommended for fast speakers or expressive speech to improve pacing [MODEL.md] [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].
*   **Accent Mitigation**: To mitigate accent inheritance from a mismatched reference clip, the CFG weight can be set to 0 [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].

**Qwen3-TTS**
*   **Natural Language Instructions**: The model supports speech generation driven by natural language instructions to control timbre, emotion, and prosody. It adaptively adjusts tone, rhythm, and emotional expression based on these instructions and text semantics [MODEL.md] [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **Voice Design Descriptions**: For the VoiceDesign variant, users provide text descriptions to design the voice [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].

**Kyutai TTS**
*   **Emotional Style**: Includes emotional style references for specific speakers (e.g., p003 and p031) [MODEL.md] [LOCAL_MODELS.tsv].

## Text Encoder and Prompt Processing

*   **Qwen3-TTS**: Uses a "discrete multi-codebook LM architecture" with `Qwen3-TTS-Tokenizer-12Hz`. The tokenizer encodes input speech into codes and decodes them back. The model features "strong contextual understanding" and "deeply integrating text semantic understanding" to adaptively adjust output [MODEL.md] [PUBLIC README https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice/raw/main/README.md].
*   **FireRedTTS**: Uses an "autoregressive-style system" with either an acoustic LLM decoder or a flow-matching decoder. It uses a text front-end (implied by `use_tn` and "rich-punctuation model" mentions) [MODEL.md] [SOURCES.md] [PUBLIC README https://huggingface.co/FireRedTeam/FireRedTTS/raw/main/README.md].
*   **Chatterbox**: Uses a "0.5B Llama backbone" with "alignment-informed inference" [MODEL.md] [PUBLIC README https://huggingface.co/ResembleAI/chatterbox/raw/main/README.md].
*   **GPT-SoVITS**: Described as a "few-shot voice conversion and TTS system" [MODEL.md].
*   **Kyutai TTS**: Uses "speaker-specific voice embeddings" for conditioning [MODEL.md].

Not in sources: Specific details on how the text encoder tokenizes the target text string (e.g., BPE, character-level) for Chatterbox, FireRedTTS, or GPT-SoVITS, other than the general architectural descriptions above.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
