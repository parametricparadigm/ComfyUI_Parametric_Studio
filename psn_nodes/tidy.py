"""Applied once when the pack loads, to every V1 node: one category tree (Parametric/<Area>), a display name, a description and input tooltips. Nothing is renamed, so old graphs keep loading.
The module sources keep their own CATEGORY values because the generated tests assert them. tidy_data.json is written by scripts/audit_nodes.py: the nodes that can reach the network."""
import json, os, re

AREAS = {
 "Prompts": "Prompt Prompts Prompting PromptChunking PromptLinting Text String Naming Templates Injection ELLA Storyboard LyricTravel Semantic SemanticSearch Retrieval Docs DocumentQuality",
 "Sampling": "Latent Sampling CFG ScheduledCFG Schedules Guidance Noise Denoise FreeU Attention SAE ZImagePlot Seed Seeds SeedLab Sweep Patching Adherence Conditioning Regional RegionEdit Field Generation",
 "Image": "Image Color ColorGrading ColorPipeline Compositing CV Mask Matting Segmentation SemanticMasking Inpainting Upscaling TileRefine SmartTile PostProcessing Preprocessing HDR Tonal Film Aesthetic Canvas Steganography ASCII Proportion Structure ArtifactCleanup Resolution Adjust AlphaVAE PBR Forensics Gaze OCR Selection Morphing Preview Save",
 "Video": "Video VideoAnalysis VideoLatent VideoUpscale Motion MotionTransfer Temporal StatefulVideo Continuity DriftCorrection Timeline LTX2 StreamDiffusion NewsVideo Camera Animation Parallax Tracking Scene SceneQueue Live Realtime NDI Media MediaWorkbench Interactive",
 "Audio": "Audio AudioPortrait AudioReactive Music RVC Voice Signal Wave",
 "3D": "3D FBX Geometry PointCloud Rendering Stereo VR VRM MultiView Panorama Environments Schematic Battlemap Games Procedural MatrixGame",
 "Character": "Character CharacterConsistency FaceIdentity AnimePose",
 "Models": "Model Models ModelLoading ModelMixing ModelResidency ModelSelection Loaders UnifiedLoader LoRA Lora TLora Flux CheckpointQC Civitai Quantization StyleGAN Training Dataset Offload MultiGPU",
 "System": "VRAM GPU Hardware Memory MemoryStreaming Resources Health Profiling Cache Storage Config Core",
 "Flow": "Logic ControlFlow FlowControl ConditionalRouting Routing Loop Batch Pipeline Pipelines Workflow Subgraphs GroupControl Graph GraphCleaning ParamHub PresetManagement State Orchestration ErrorHandling Guard Project Replay Repro Plugins AutoGen",
 "Quality": "Quality QualityGate Validation Verification Integrity Safety SmokeTest Debug Debugging TensorDebug TensorFormat Inspection Introspection Metadata Provenance Sidecar Status Time RealTimeABTest StatisticalAnalysis",
 "Data": "Data JSON CSV Excel GSheet Sheet Database S3 CryptIO Secure Assets Sites SingleCell Tools",
 "Agents": "Agent Agents AgentOrchestration Subagents LLM Crew Gemini",
 "Integrations": "Bridges Telegram Modal NvidiaVFX Ray Nuke TouchDesigner",
}
AREA_OF = {sub: area for area, subs in AREAS.items() for sub in subs.split()}; AREA_OF["LLM Captioning"] = "Agents"
GLOSSARY = {"seed": "Random seed: the same seed repeats the same result.", "steps": "Sampling steps.", "cfg": "Guidance scale.", "denoise": "How much to change: 1.0 replaces everything.", "width": "Width in pixels.", "height": "Height in pixels.", "prompt": "The prompt text.", "negative": "What to steer away from.", "negative_prompt": "What to steer away from.", "model": "The model to use.", "clip": "The text encoder.", "vae": "The VAE.", "latent": "The latent to work on.", "samples": "The latent to work on.", "image": "The input image.", "images": "The input images.", "mask": "The mask.", "audio": "The input audio.", "strength": "How strong the effect is.", "threshold": "The cut-off value.", "batch_size": "How many to make at once.", "fps": "Frames per second.", "frames": "Number of frames.", "filename_prefix": "Start of the saved file's name.", "text": "The input text.", "enabled": "Turn this on or off.", "scale": "Scale factor."}
_DATA = {}
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tidy_data.json"), encoding="utf-8") as _f: _DATA = json.load(_f)
except (OSError, ValueError): pass
NETWORK = set(_DATA.get("network") or ())
# Weak duplicates, hidden from the Add Node menu with DEPRECATED. Old graphs keep running. Each was compared with the node it points at by signature and description; the inspector, structure and iterator pairs were also run side by side.
HIDDEN = {"PSN_Latent_Batch_Repeat": "PSN_LatentBatchRepeat", "PSN_Latent_Batch_Merge": "PSN_LatentBatchConcat", "PSN_Node_Inspector": "PSN_NodeInspector", "PSN_Workflow_Structure": "PSN_WorkflowStructure", "PSN_PromptIterator": "PSN_Prompt_Iterator", "PSN_Prompt_Enhancer": "PSN_PromptEnhancer", "PSN_VramGate": "PSN_VRAMGate"}

def area_of(category):
    sub = str(category or "").split("/", 1)[-1].split("/")[0]
    return AREA_OF.get(sub, "Misc")
def humanize(node_id):
    return re.sub(r"\s+", " ", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", re.sub(r"^PSN_?", "", node_id).replace("_", " "))).strip() or node_id
def first_paragraph(text):
    text = " ".join((text or "").strip().split("\n\n")[0].split())
    return text[:400]
def describe(cls, display):
    own = getattr(cls, "DESCRIPTION", None)
    if own: return own
    doc = cls.__dict__.get("__doc__")
    if doc: return first_paragraph(doc)
    mod = __import__("sys").modules.get(cls.__module__)
    return first_paragraph(getattr(mod, "__doc__", "")) or f"{display}."
def tooltip_for(name, spec):
    """A plain line from the name and the widget's own limits. Says only what the spec says, plus a small glossary of names that mean one thing in ComfyUI."""
    opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}; kind = spec[0]
    bits = [GLOSSARY.get(name) or (name.replace("_", " ").capitalize() + ".")]
    if isinstance(kind, (list, tuple)): bits.append(f"One of {len(kind)} choices.")
    elif "min" in opts and "max" in opts: bits.append(f"From {opts['min']:g} to {opts['max']:g}." if isinstance(opts["min"], (int, float)) and isinstance(opts["max"], (int, float)) else "")
    if "default" in opts and not isinstance(opts["default"], (list, dict)) and str(opts["default"]) != "": bits.append(f"Default {opts['default']}.")
    return " ".join(b for b in bits if b)[:300]
def with_tooltips(types):
    if not isinstance(types, dict): return types
    out = dict(types)
    for section in ("required", "optional"):
        inputs = types.get(section)
        if not isinstance(inputs, dict): continue
        fresh = {}
        for name, spec in inputs.items():
            if isinstance(spec, (tuple, list)) and spec and not (len(spec) > 1 and isinstance(spec[1], dict) and spec[1].get("tooltip")):
                opts = dict(spec[1]) if len(spec) > 1 and isinstance(spec[1], dict) else {}; opts["tooltip"] = tooltip_for(name, spec); spec = (spec[0], opts, *spec[2:])
            fresh[name] = spec
        out[section] = fresh
    return out
def _wrap_input_types(cls):
    original = cls.INPUT_TYPES
    def INPUT_TYPES(*_): return with_tooltips(original())
    cls.INPUT_TYPES = staticmethod(INPUT_TYPES)
def tidy(mappings, display):
    """Mutates the classes and the display map in place. V3 nodes declare all of this in their schema, so they are left alone."""
    done = set()
    for node_id, cls in mappings.items():
        if hasattr(cls, "GET_SCHEMA") or cls in done: continue
        done.add(cls); old = getattr(cls, "CATEGORY", "") or ""; sub = old.split("/", 1)[-1]
        if not old.startswith("Parametric/"):
            cls.CATEGORY = f"Parametric/{area_of(old)}"
            if sub and not hasattr(cls, "SEARCH_ALIASES"): cls.SEARCH_ALIASES = [sub.lower()]
        if not display.get(node_id) or display[node_id] == node_id: display[node_id] = humanize(node_id)
        text = describe(cls, display[node_id])
        if node_id in NETWORK and not re.search(r"network|internet|online|http|api|webhook|url|remote|download|upload|server|bridge", text, re.I): text = text.rstrip() + " Uses the network."
        if node_id in HIDDEN: cls.DEPRECATED = True; text = text.rstrip() + f" Hidden from the menu: use {HIDDEN[node_id]} instead."
        cls.DESCRIPTION = text
        _wrap_input_types(cls)
    return mappings
