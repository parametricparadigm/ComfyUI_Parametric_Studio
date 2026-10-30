import os
import re
import json
import urllib.request
import urllib.parse
import zlib
from collections import Counter

NAMES = [
    "Professor Latent", "Captain Checkpoint", "Lady LoRA", "Sir Sampler-Alot",
    "Dr. Denoise", "Madame Attention", "Bit Bandit", "Tensor Tilly",
    "Seedling", "Noisy Nick", "Pixel Pete", "Gradient Grace",
    "Kernel Kate", "Batch Betty", "Epoch Eddie", "Loss Larry",
    "Momentum Max", "Adam Alex", "SGD Sam", "Backprop Ben",
    "Forward Faye", "Dropout Dan", "BatchNorm Bob", "ReLU Rita",
    "Softmax Sally", "Sigmoid Steve", "Tanh Tina", "GELU Gary",
    "Swish Sue", "Mish Mike", "GLU Greg", "LayerNorm Lou",
    "GroupNorm Gus", "InstanceNorm Ida", "Convolution Carl", "Pooling Paul",
    "Upscale Uma", "Downscale Dan", "Interpolate Ian", "Bilinear Bill",
    "Bicubic Ben", "Lanczos Liz", "Nearest Neighbor Ned", "Bicubic Bob",
    "Diffusion Dot", "Latent Larry", "Noise Nora", "Signal Sam",
    "Filter Fred", "Kernel Kim", "Stride Steve", "Padding Pat",
    "Dilation Dan", "Depthwise Dee", "Pointwise Pete", "Convolution Carl",
    "Residual Ray", "Skip Connection Sam", "Highway Highway", "Identity Ida",
    "Transformer Tom", "Encoder Emma", "Decoder Dan", "Attention Alex",
    "Multi-Head Mike", "Self-Attention Sam", "Cross-Attention Chris", "Query Query",
    "Key Key", "Value Val", "Projection Pete", "Feed-Forward Fred",
    "Positional Pos", "Embedding Emma", "Tokenizer Tony", "Vocabulary Vic",
    "Context Context", "Window Win", "Sliding Slide", "Chunk Chuck",
    "Token Token", "Sequence Seq", "Length Len", "Batch Batch",
    "Epoch Epoch", "Iteration It", "Step Step", "Rate Rate",
    "Learning Larry", "Decay Decay", "Warmup Warm", "Cool Cool",
    "Schedule Sch", "Cosine Cos", "Linear Lin", "Step Step"
]

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "what", "which", "who", "whom", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "as", "until", "while", "about", "between", "into",
    "through", "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once"
}

def _slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def _tokenize(text):
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]

def _normalize_ws(s):
    return ' '.join(s.split())

def roster(kb_root):
    families_dir = os.path.join(kb_root, "model_families")
    if not os.path.isdir(families_dir):
        return []
    
    family_folders = sorted([d for d in os.listdir(families_dir) if os.path.isdir(os.path.join(families_dir, d))])
    
    members = []
    name_index = 0
    
    for folder in family_folders:
        match = re.match(r'^\d+-(.*)', folder)
        family_name = match.group(1) if match else folder
        family_id = _slugify(family_name)
        
        dossier_dir = os.path.join(families_dir, folder, "dossier")
        files = []
        if os.path.isdir(dossier_dir):
            for f in sorted(os.listdir(dossier_dir)):
                if f.endswith('.md'):
                    files.append(os.path.join(dossier_dir, f))
        
        name = NAMES[name_index % len(NAMES)]
        name_index += 1
        
        members.append({
            "id": family_id,
            "family": family_name,
            "name": name,
            "tier": "family",
            "files": files,
            "has_dossier": len(files) > 0
        })
    
    secondary_ids = ['text-encoders', 'vae', 'vision']
    for sid in secondary_ids:
        name = NAMES[name_index % len(NAMES)]
        name_index += 1
        members.append({
            "id": sid,
            "family": sid,
            "name": name,
            "tier": "secondary",
            "files": []
        })
    
    tertiary_ids = ['lora', 'controlnet', 'upscaler']
    for tid in tertiary_ids:
        name = NAMES[name_index % len(NAMES)]
        name_index += 1
        members.append({
            "id": tid,
            "family": tid,
            "name": name,
            "tier": "tertiary",
            "files": []
        })
    
    all_dossier_files = []
    for m in members:
        if m["tier"] == "family":
            all_dossier_files.extend(m["files"])
    
    members.append({
        "id": "master",
        "family": "master",
        "name": "Comfy Prime",
        "tier": "master",
        "files": all_dossier_files
    })
    
    return members

def retrieve(files, question, k=4, chunk_chars=900):
    q_tokens = set(_tokenize(question))
    q_lower = question.lower()
    
    chunks = []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
        except:
            continue
        
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if len(current_chunk) + len(p) + 1 > chunk_chars and current_chunk:
                chunks.append((f, current_chunk))
                current_chunk = p
            else:
                current_chunk = (current_chunk + "\n\n" + p) if current_chunk else p
        
        if current_chunk:
            chunks.append((f, current_chunk))
    
    scored = []
    for f, text in chunks:
        text_lower = text.lower()
        text_tokens = set(_tokenize(text))
        
        overlap = len(q_tokens & text_tokens)
        score = float(overlap)
        
        if q_lower in text_lower:
            score += 10.0
        
        if score > 0:
            scored.append({"file": f, "text": text, "score": score})
    
    scored.sort(key=lambda x: (-x["score"], x["file"], x["text"]))
    
    return scored[:k]

def _plain(t):
    """Compare what was said, not how it was typed: no markdown, bracket citations, quote marks or case."""
    t = re.sub(r"\[[^\]]{0,120}\]", " ", str(t)); t = re.sub(r"[`*_#>|\"'\u2018\u2019\u201c\u201d]", "", t); return re.sub(r"\s+", " ", t).strip().lower()

def _match_quote(quote, chunks, floor=0.8):
    """The note text this quote came from, or None. Exact after cleaning, or a close match to one sentence or line of the notes; the note's own words are what gets shown, so an answer can never display words the notes don't contain."""
    q = _plain(quote)
    if len(q) < 12: return None
    from difflib import SequenceMatcher
    best, best_score = None, 0.0
    for c in chunks:
        plain = _plain(c["text"])
        if q in plain: return {"file": c["file"], "quote": str(quote).strip()}
        for part in re.split(r"(?<=[.!?:;])\s+|\n+", c["text"]):
            pp = _plain(part)
            if len(pp) < 12: continue
            score = SequenceMatcher(None, q, pp, autojunk=False).ratio()
            if score > best_score: best, best_score = {"file": c["file"], "quote": part.strip()}, score
    return best if best_score >= floor else None

def ask(member, question, chat, k=4, chunk_chars=900):
    chunks = retrieve(member["files"], question, k=k, chunk_chars=chunk_chars)
    
    if not chunks:
        return {
            "answer": "I can't back that up from my notes.",
            "quotes": [],
            "supported": False,
            "problems": ["No relevant chunks found"],
            "member": member["id"]
        }
    
    context_parts = []
    for i, c in enumerate(chunks):
        context_parts.append(f"[{i}] File: {c['file']}\n{c['text']}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    prompt = f"""You are {member['name']}, a specialist in {member['family']}.
Answer the question ONLY using the provided context chunks.
Return JSON: {{"answer": str, "quotes": [{{"file": str, "quote": str}}]}}
Each quote must be one short sentence copied exactly, word for word, from the context, without any citation marks.
If the context does not answer the question, return {{"answer": "", "quotes": []}}.

Context:
{context}

Question: {question}"""
    
    messages = [{"role": "user", "content": prompt}]
    reply = chat(messages)
    
    try:
        json_match = re.search(r'\{.*\}', reply, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in reply")
        data = json.loads(json_match.group())
    except Exception as e:
        return {
            "answer": "I can't back that up from my notes.",
            "quotes": [],
            "supported": False,
            "problems": [f"Failed to parse model reply: {str(e)}"],
            "member": member["id"]
        }
    
    answer = data.get("answer", "")
    quotes = data.get("quotes", [])
    
    verified_quotes = []
    problems = []
    for q in quotes:
        q_text = q.get("quote", "") if isinstance(q, dict) else ""
        hit = _match_quote(q_text, chunks) if q_text else None
        if not hit:
            problems.append("A quote did not match the notes")
            continue
        if hit["quote"] not in [v["quote"] for v in verified_quotes]:
            verified_quotes.append({"file": "/".join(str(hit["file"]).replace("\\", "/").split("/")[-2:]), "quote": hit["quote"]})

    supported = len(verified_quotes) > 0   # one real quote backs the answer; the ones that did not match are simply not shown

    if not supported:
        answer = "I can't back that up from my notes."
    
    return {
        "answer": answer,
        "quotes": verified_quotes,
        "supported": supported,
        "problems": problems,
        "member": member["id"]
    }

def default_chat(messages):
    from studio import llm_tiers
    ep = llm_tiers.endpoint()
    if not ep: raise RuntimeError("no language model is running; see /api/llm for the one that fits this machine")
    from studio import voice
    if voice.llm_state(lambda: ep) == "asleep": raise RuntimeError("the language model is asleep while a render holds the GPU")   # its chat route would hang until it wakes
    body = {
        "model": ep["model"],
        "messages": messages,
        "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False}
    }
    req = urllib.request.Request(ep["url"] + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def route(question, members):
    q_lower = question.lower()
    best_id = "master"
    best_score = 0
    
    for m in members:
        if m["tier"] != "family":
            continue
        
        family_lower = m["family"].lower()
        name_lower = m["name"].lower()
        
        score = 0
        if family_lower in q_lower:
            score += 10
        if name_lower in q_lower:
            score += 5
        
        for word in family_lower.split():
            if word in q_lower:
                score += 2
        
        if score > best_score:
            best_score = score
            best_id = m["id"]
    
    return best_id

# ---------- faces and voices: lookups by member id. The roster above does not change.
_CREW_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "crew")
CHARACTERS = {  # id: (Kokoro voice, speed, first line). Only Kokoro's 28 English voices read English well (the others garble it, checked by transcribing them with Whisper), so ten voices are used twice, at a clearly different pace.
    "master": ("af_heart", 1.0, "Hi, I'm Comfy Prime, your guide to this studio."),
    "3d-trellis-hunyuan3d-sam3d-mesh": ("bm_george", 0.94, "Ah, come in. I study 3D models: Trellis, Hunyuan3D and SAM 3D. What shall we examine?"),
    "anima": ("am_santa", 0.96, "Welcome aboard. I keep the charts for Anima, our anime model. Where are we sailing?"),
    "audio-fx-separation-foley-models": ("bf_emma", 0.98, "Charmed. Sound effects, foley and separating stems are my domain. What are you listening for?"),
    "chroma": ("bm_lewis", 0.98, "Well met! I have sworn my oath to Chroma. Ask, and I shall answer from my notes."),
    "cogvideox-mochi-cosmos-svd-animatediff-older-video": ("bm_daniel", 0.88, "Hello. I look after the older video models: CogVideoX, Mochi, Cosmos, SVD and AnimateDiff. Tell me where it hurts."),
    "depth-normals-pose": ("bf_isabella", 0.92, "Darling, I notice everything: depth, normals and pose. You have my full attention."),
    "dreamx-creator": ("am_puck", 1.14, "Psst. I know where DreamX Creator keeps its secrets. What do you want to know?"),
    "faces-identity-portrait-animation": ("af_bella", 1.08, "Hi! Faces, identity and portrait animation are on my workbench. What are we fixing?"),
    "flux-1-dev-schnell-kontext-fill": ("af_sky", 1.14, "Hello! I'm small, but I know FLUX.1 dev, Schnell, Kontext and Fill. What shall we grow?"),
    "flux-2-klein": ("am_fenrir", 1.14, "Hey! Sorry, was that loud? I run FLUX.2 Klein, the fast one. What do you need?"),
    "hidream": ("am_liam", 1.12, "Hi, I know HiDream down to the last pixel. What are you making?"),
    "hunyuanvideo-framepack": ("af_nova", 0.98, "Hello. HunyuanVideo and FramePack are my field, one smooth frame into the next. What would you like to know?"),
    "kandinsky-omnigen-ovis-hunyuanimage": ("af_jessica", 1.06, "Hi there! Kandinsky, OmniGen, Ovis and HunyuanImage: I've cracked them all open. Ask me."),
    "krea-2": ("af_kore", 1.02, "Hello, dear! Krea 2 is fresh out of my oven. What can I bake for you?"),
    "ltx-video-ltx-2": ("am_eric", 1.04, "Right on time. LTX Video is what I keep ticking. What would you like to know?"),
    "minimax-h3": ("am_adam", 0.86, "Oh. Hello. I know MiniMax H3, the bad days and the good ones. Go on, ask me."),
    "music-song-models": ("am_michael", 1.18, "Let's go! Music and song models keep me rolling. What are we making?"),
    "pony-illustrious-noobai": ("am_adam", 1.08, "Hey. Pony, Illustrious and NoobAI are my thing. What are you drawing?"),
    "prism-longcat-void-joyai-video": ("am_echo", 1.0, "Morning. I've walked every trail of Prism, LongCat, VOID and JoyAI Video, downhill one step at a time. Ask away."),
    "qwen-image-qwen-image-edit": ("bm_daniel", 1.08, "Hi, I work backstage on Qwen Image and Image Edit. Need anything moved or changed?"),
    "sam-segmentation-matting": ("af_alloy", 1.12, "Hi! Segmentation and matting, straight ahead. What should we cut out?"),
    "sd-1-5": ("am_liam", 0.84, "Oh, hey. I left school, but I never left SD 1.5. What's up?"),
    "sd3-sd3-5": ("am_michael", 0.92, "Good day. SD3 and 3.5, all filed in order. What do you need?"),
    "sdxl": ("af_aoede", 1.1, "Hey. SDXL is my ramp, and I've skated all of it. What trick are you after?"),
    "tts-voice-models": ("af_nicole", 0.92, "Hello, softly now. Voice models are what I listen to all day. What would you like to hear about?"),
    "upscale-restore-models": ("bm_fable", 0.96, "Hello there. I make small things bigger and old things new. What do you have for me?"),
    "vlm-captioning-tagging": ("af_sarah", 1.08, "Hi! I look at pictures and say what's in them: captions and tags. What are you looking at?"),
    "wan-version-not-stated": ("am_onyx", 1.04, "Hey there. I cover the Wan notes that don't say which version. Ask away."),
    "wan-2-1": ("af_river", 1.12, "Hi! Wan 2.1 is my court. Take your shot."),
    "wan-2-2": ("am_puck", 0.9, "Hello! Wan 2.2, a bit of everything and nothing matching. What's on your mind?"),
    "z-image-lumina2": ("am_eric", 0.84, "Hi! I stick Z-Image and Lumina 2 together. What are we building?"),
    "text-encoders": ("am_fenrir", 0.88, "Brr, hello. Text encoders come in layers, and I wear them all."),
    "vae": ("am_onyx", 0.84, "Good evening. I conduct the VAEs, in and out of latent space, all in time."),
    "vision": ("bf_alice", 0.92, "Hoo, hello. Vision encoders are how a model sees, and I see a lot."),
    "lora": ("bm_fable", 1.16, "Aha! LoRAs: little twists on a big model. I love a good twist."),
    "controlnet": ("am_echo", 1.18, "Hey, welcome to the deep end! ControlNets keep your picture in its lane."),
    "upscaler": ("bf_lily", 0.96, "Good afternoon. Upscalers, my dear: only the very finest detail."),
}
def portrait(member_id):
    """Path of a member's face under the web root (scripts/build_crew_art.py renders them), or None if there is none yet."""
    return f"crew/{member_id}.webp" if re.fullmatch(r"[a-z0-9-]+", str(member_id)) and os.path.isfile(os.path.join(_CREW_WEB, f"{member_id}.webp")) else None
def motion(member_id):
    """{idle, talk} paths of a member's silent video loops under the web root, or None. Talk is what makes a member animated; idle is optional (the portrait stands in). These loop; they are not lip sync."""
    if not re.fullmatch(r"[a-z0-9-]+", str(member_id)) or not os.path.isfile(os.path.join(_CREW_WEB, f"{member_id}.talk.mp4")): return None
    return {"idle": f"crew/{member_id}.idle.mp4" if os.path.isfile(os.path.join(_CREW_WEB, f"{member_id}.idle.mp4")) else None, "talk": f"crew/{member_id}.talk.mp4"}
def voice(member_id, available=None):
    """(voice, speed) for a member: the fixed pick, or a stable hash of the id when the member is new or the speech server lacks that voice. available = the voice names the server offers (None or empty = unknown, so trust the table)."""
    picked, speed = CHARACTERS.get(member_id, (None, 1.0))[:2]
    if picked and (not available or picked in available): return picked, speed
    pool = sorted(available or {c[0] for c in CHARACTERS.values()})
    return pool[zlib.crc32(str(member_id).encode()) % len(pool)], speed
def hello(member_id):
    """A member's first line, in character. New members get a plain one."""
    return CHARACTERS[member_id][2] if member_id in CHARACTERS else "Hello. Ask me anything my notes can answer."
