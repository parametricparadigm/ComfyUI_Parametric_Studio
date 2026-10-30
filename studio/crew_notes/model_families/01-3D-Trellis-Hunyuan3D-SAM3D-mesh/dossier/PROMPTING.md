# PROMPTING - 01-3D-Trellis-Hunyuan3D-SAM3D-mesh

## Prompt Structure and Input Modality
The primary input for the majority of models in this family (Trellis, Hunyuan3D, SAM3D, TripoSR, Stable-Fast-3D, Pixal3D) is a single 2D image, not a text prompt [MODEL.md]. The standard workflow for these models is image-to-3D generation, where the model transforms a 2D image input into a 3D representation [MODEL.md].

*   **Trellis**: The input is explicitly defined as a "Single Image" [SOURCES.md: microsoft/TRELLIS.2-4B]. The workflow uses `Trellis2PreProcessImage` and `Trellis2ImageCondGenerator` to extract image conditioning, with no text prompt input shown in the node chain [WORKFLOW_PLAN.md].
*   **Hunyuan3D**: The shape generation stage (`Hunyuan3D-DiT`) takes an image as input to create geometry that aligns with the condition image [SOURCES.md: tencent/Hunyuan3D-2]. The texture synthesis stage (`Hunyuan3D-Paint`) can accept text prompts, as indicated by the presence of a `text_encoder` model file and the tag `text-to-3d` in the repository metadata [LOCAL_MODELS.tsv] [SOURCES.md: tencent/Hunyuan3D-2].
*   **SAM-3D-Objects**: The input is an image and a mask [WORKFLOW_PLAN.md].
*   **TripoSR**: The model type is "Feed-forward 3D reconstruction from a single image" [SOURCES.md: stabilityai/TripoSR].

## Text Encoder Functionality
*   **Hunyuan3D PaintPBR**: A specific text encoder model (`hunyuan3d-paintpbr-v2-1/text_encoder`) is present in the local environment. Its role is to "Encode text prompts for PBR texture generation" [MODEL.md] [LOCAL_MODELS.tsv]. This implies that text prompts are used specifically for the texture synthesis stage of the Hunyuan3D pipeline, not necessarily for the initial shape generation [MODEL.md].
*   **Other Models**: No text encoders are listed for Trellis, SAM-3D-Objects, TripoSR, Stable-Fast-3D, Pixal3D, or UniRig in the local model inventory [LOCAL_MODELS.tsv]. These models rely on vision encoders (e.g., DINOv3, DINOv2) to extract features from input images [MODEL.md] [LOCAL_MODELS.tsv].

## Language
*   **Hunyuan3D**: The repository metadata lists `en` and `zh` as supported languages [SOURCES.md: tencent/Hunyuan3D-2].
*   **Trellis**: The repository metadata lists `en` as the supported language [SOURCES.md: microsoft/TRELLIS.2-4B].
*   **Other Models**: Not in sources: Specific language support for SAM-3D-Objects, TripoSR, Stable-Fast-3D, Pixal3D, or UniRig.

## Negative Prompts
Not in sources: Usage or support for negative prompts in any model within this family.

## Style and Camera Vocabulary
Not in sources: Specific style or camera vocabulary guidelines for prompting.

## Prompt Length
Not in sources: Recommended or maximum prompt length.

## Model-Specific Prompting Notes

### Hunyuan3D
The system is described as having a "text-to-3d" capability in its tags [SOURCES.md: tencent/Hunyuan3D-2]. The API usage examples in the README show image-based generation for both shape and texture, but reference `minimal_demo.py` for "text to 3D" usage [SOURCES.md: tencent/Hunyuan3D-2]. The local pipeline includes a text encoder for the PaintPBR stage, suggesting text prompts influence the texture output [LOCAL_MODELS.tsv].

### Trellis
The model is a "pre-trained foundation model" that has "not been aligned with human preferences (e.g., via RLHF) or fine-tuned for specific aesthetic standards" [SOURCES.md: microsoft/TRELLIS.2-4B]. Consequently, outputs reflect the training data distribution, and users may need to experiment with inputs (images) to achieve desired artistic results [SOURCES.md: microsoft/TRELLIS.2-4B]. There is no mention of text prompting in the provided usage code or node workflow [SOURCES.md: microsoft/TRELLIS.2-4B] [WORKFLOW_PLAN.md].

### SAM-3D-Objects
The workflow requires an image and a mask. The mask is used to isolate the object for generation [WORKFLOW_PLAN.md]. Not in sources: Text prompt support.

### TripoSR
The model is a feed-forward reconstruction model from a single image. Not in sources: Text prompt support.

### Stable-Fast-3D
Described as a combined tokenizer and estimator architecture for 3D generation from images. Not in sources: Text prompt support.

### Pixal3D
Uses flow-matching DiTs for shape and texture generation from images. Not in sources: Text prompt support.

### UniRig
Processes existing 3D meshes to generate skeletons and skin weights. It does not generate geometry from prompts or images in the same manner as the generative models. Not in sources: Text prompt support.

---
Written by Qwen3.8-27B-FP8 from local KB pages and public READMEs on 2026-10-30; not run or tested. Evidence size 60000 chars.
