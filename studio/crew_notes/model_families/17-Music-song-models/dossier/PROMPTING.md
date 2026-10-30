# PROMPTING - 17-Music-song-models

## Prompt Structure and Inputs

**ACE-Step 1.5**
*   **Caption:** The primary text input describing the desired music style, genre, or mood. The LM stage takes a caption and generates metadata, lyrics, and audio codes [MODEL.md].
*   **Lyrics:** Specific lyrics for vocal tracks are supported via the LM stage [MODEL.md].
*   **Reference Audio:** ACE-Step 1.5 supports cover generation and timbre conditioning using reference audio [MODEL.md].
*   **Description Formats:** The model supports various description formats including short tags, descriptive text, or use-case scenarios [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md].
*   **LM Planning:** The Language Model (LM) functions as an omni-capable planner that transforms simple user queries into comprehensive song blueprints, synthesizing metadata, lyrics, and captions via Chain-of-Thought to guide the Diffusion Transformer (DiT) [https://huggingface.co/ACE-Step/Ace-Step1.5].

**Mini-Max Music 3**
*   **Text Prompts:** The text encoder processes prompts for music generation [MODEL.md].
*   **Specific Structure:** Not in sources: specific prompt structure or required fields for Mini-Max Music 3 beyond general text prompts.

## Language Support

*   **ACE-Step 1.5:** Supports 50+ languages [MODEL.md]. The model maintains strict adherence to prompts across these languages [https://huggingface.co/ACE-Step/Ace-Step1.5].
*   **Mini-Max Music 3:** Not in sources: specific language support details for Mini-Max Music 3.

## Negative Prompts

## Style and Camera Vocabulary

*   **ACE-Step 1.5:**
    *   **Style/Genre:** Supports all mainstream music styles with various description formats [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md].
    *   **Instrumentation:** Capable of generating music across different genres with appropriate instrumentation and style [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md].
    *   **Vocal Techniques:** Capable of rendering various vocal styles and techniques, including different singing techniques and styles [https://raw.githubusercontent.com/ace-step/ACE-Step/HEAD/README.md].
    *   **Camera Vocabulary:** Not in sources: specific camera vocabulary or visual prompt terms for ACE-Step 1.5.
*   **Mini-Max Music 3:**
    *   **Style/Genre:** Not in sources: specific style or genre vocabulary guidance for Mini-Max Music 3.
    *   **Camera Vocabulary:** Not in sources: specific camera vocabulary or visual prompt terms for Mini-Max Music 3.

## Text Encoder Behavior

**ACE-Step 1.5**
*   **Architecture:** The text encoder is a frozen Qwen3 encoder (28 layers, 1024-dim) [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF].
*   **Locking:** The DiT was trained end-to-end with this exact model. Its CondEncoder projection weights (1024 to 2048) are baked into every DiT checkpoint, so the Text-Enc is architecturally locked to the 0.6B model [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF].
*   **Role:** The text encoder (Qwen3-Embedding-0.6B) is architecturally locked to the DiT's CondEncoder projection weights [MODEL.md].
*   **Pipeline Role:** In the synthesis stage, the Caption and Lyrics are processed by the Text-Enc (Qwen3-Embedding-0.6B) to produce conditioning for the DiT [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF].

**Mini-Max Music 3**
*   **Architecture:** The local installation includes a pruned text encoder (`minimax_music3_text_encoder_pruned_bf16.safetensors`) [MODEL.md].
*   **Role:** The text encoder encodes text prompts for music generation [LOCAL_MODELS.tsv].
*   **Specifics:** Not in sources: specific architectural details or locking mechanisms for the Mini-Max Music 3 text encoder beyond it being a diffusion-based model component.

## Prompt Length

*   **ACE-Step 1.5:** Not in sources: specific maximum or recommended prompt length limits.
*   **Mini-Max Music 3:** Not in sources: specific maximum or recommended prompt length limits.

## Additional Guidance

*   **ACE-Step 1.5:** For tips on writing effective prompts, understanding inference parameters, and getting the best results, refer to the "A Musician's Guide" (non-technical) and the "Tutorial" (design philosophy, architecture, hyperparameters) linked in the source material [https://huggingface.co/Serveurperso/ACE-Step-1.5-GGUF].
*   **Mini-Max Music 3:** Not in sources: specific prompting guides or tutorials.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
