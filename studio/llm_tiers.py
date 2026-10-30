"""Which in-house LLM the crew characters should use on a given box, and exactly how to run it.
All listed models are Apache-2.0 and ungated on Hugging Face (checked 2026-10-30). GGUF file names and sizes were read from the unsloth repos on the same day; sampling presets are the ones the Qwen model cards print for non-thinking chat (the crew
never needs a hidden thinking pass, which only adds latency). Placement matters as much as size: on boxes that need their GPU for image/video models, a small LLM runs on the CPU (llama.cpp) so generation never competes with the crew for VRAM.
Speed figures are ESTIMATES from memory bandwidth (decode tok/s ~ bandwidth / bytes read per token), not benchmarks on this box; the Calibrate card replaces them with measured numbers."""
import json, os, re, shlex, shutil, subprocess, sys, time, urllib.request

SAMPLING = {  # Qwen model cards: "non-thinking / instruct, general tasks" (the 2B card lists its own text preset)
    "tiny": {"temperature": 1.0, "top_p": 1.0, "top_k": 20, "min_p": 0.0, "presence_penalty": 2.0},
    "chat": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0, "presence_penalty": 1.5},
    "studio": {"temperature": 1.0, "top_p": 0.95, "top_k": 20},  # Qwen3.8-27B-FP8 generation_config.json
}
TIERS = [  # ordered smallest to largest
 {"id": "tiny", "model": "Qwen/Qwen3.5-2B", "quant": "Q8_0", "weights_gb": 2.0, "min_ram_gb": 6, "min_vram_gb": 0, "placement": "cpu", "ctx": 8192, "sampling": "tiny", "est_tok_s": "20-35 on a 4-core CPU",
  "gguf": {"repo": "unsloth/Qwen3.5-2B-GGUF", "file": "Qwen3.5-2B-Q8_0.gguf"}, "note": "any machine; short answers, quick. Small models lose the most to quantizing, so this one keeps 8 bits"},
 {"id": "small", "model": "Qwen/Qwen3.5-4B", "quant": "UD-Q6_K_XL", "weights_gb": 4.1, "min_ram_gb": 8, "min_vram_gb": 0, "placement": "cpu", "ctx": 8192, "sampling": "chat", "est_tok_s": "10-18 on a modern 8-core CPU",
  "gguf": {"repo": "unsloth/Qwen3.5-4B-GGUF", "file": "Qwen3.5-4B-UD-Q6_K_XL.gguf"}, "note": "good default for 8-12 GB cards: runs on the CPU so the GPU stays free for images and video"},
 {"id": "medium", "model": "Qwen/Qwen3.5-9B", "quant": "UD-Q5_K_XL", "weights_gb": 6.7, "min_ram_gb": 16, "min_vram_gb": 0, "placement": "cpu", "ctx": 16384, "sampling": "chat", "est_tok_s": "6-10 on CPU, 60+ on a spare GPU",
  "gguf": {"repo": "unsloth/Qwen3.5-9B-GGUF", "file": "Qwen3.5-9B-UD-Q5_K_XL.gguf"}, "note": "16 GB+ RAM; clearly better notes-reading; CPU or spare GPU"},
 {"id": "moe", "model": "Qwen/Qwen3.5-35B-A3B", "quant": "UD-Q4_K_XL", "weights_gb": 22.2, "min_ram_gb": 32, "min_vram_gb": 0, "placement": "cpu", "ctx": 16384, "sampling": "chat", "est_tok_s": "15-30 on CPU (only ~3B parameters are read per token)",
  "gguf": {"repo": "unsloth/Qwen3.5-35B-A3B-GGUF", "file": "Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf"}, "note": "mixture of experts: 35B knowledge but only 3B active per token, so it is fast even on a CPU with 32 GB+ RAM"},
 {"id": "large", "model": "Qwen/Qwen3.5-27B", "quant": "UD-Q4_K_XL", "weights_gb": 17.6, "min_ram_gb": 32, "min_vram_gb": 24, "placement": "gpu", "ctx": 32768, "sampling": "chat", "est_tok_s": "35-60 on a 24 GB card",
  "gguf": {"repo": "unsloth/Qwen3.5-27B-GGUF", "file": "Qwen3.5-27B-UD-Q4_K_XL.gguf"}, "note": "24 GB+ card; best quality per GB; unload it while rendering on a single small GPU"},
 {"id": "studio", "model": "Qwen/Qwen3.8-27B-FP8", "quant": "FP8", "weights_gb": 29.0, "min_ram_gb": 64, "min_vram_gb": 64, "placement": "gpu", "ctx": 131072, "sampling": "studio", "est_tok_s": "~70 per stream, 800+ aggregate with many agents",
  "gguf": None, "note": "what this studio's author runs: 64 GB+ (96 GB card recommended) with vLLM; many agents at once"},
]
BY_ID = {t["id"]: t for t in TIERS}

def pick(profile, reserve_vram_gb=0.0):
    """profile: {ram_gb, gpus:[{vram_gb}], backend}. -> {tier, model, placement, why}. Chooses the strongest tier whose RAM/VRAM needs are met; a GPU tier is only chosen when the GPU would still have room for image models."""
    ram = float(profile.get("ram_gb") or 0); vram = max([float(g.get("vram_gb") or 0) for g in profile.get("gpus", [])] or [0.0]) - reserve_vram_gb
    best = None
    for t in TIERS:
        if ram < t["min_ram_gb"]: continue
        if t["placement"] == "gpu" and vram < t["min_vram_gb"]: continue
        best = t
    if best is None: return {"tier": None, "why": f"not enough memory for any tier ({ram:.0f} GB RAM)"}
    return {"tier": best["id"], "model": best["model"], "quant": best["quant"], "placement": best["placement"], "approx_download_gb": best["weights_gb"], "gguf": best["gguf"], "sampling": SAMPLING[best["sampling"]],
            "est_tok_s": best["est_tok_s"], "why": f"{ram:.0f} GB RAM, {max(vram, 0):.0f} GB VRAM -> {best['note']}"}

def _ram_gb(platform=None):
    """Installed RAM in GB on Linux, macOS or Windows; 0.0 when it cannot be read."""
    platform = platform or sys.platform
    try:
        if platform == "darwin": return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=10).stdout.strip()) / 2**30
        if platform == "win32":
            import ctypes
            kb = ctypes.c_ulonglong(0); return kb.value / 1048576 if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(kb)) else 0.0
        m = re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read()); return int(m.group(1)) / 1048576 if m else 0.0
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError): return 0.0

def detect_profile():
    """Read this machine's RAM and NVIDIA GPUs without importing torch. Missing tools just mean 'no GPU' / 'unknown RAM'."""
    ram = _ram_gb()
    gpus = []
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
            gpus = [{"vram_gb": int(x) / 1024} for x in out.split() if x.isdigit()]
        except (OSError, subprocess.SubprocessError): pass
    return {"ram_gb": round(ram, 1), "gpus": gpus, "cores": os.cpu_count() or 4}

def llama_args(tier_id, models_dir, port=8301, threads=None, cores=None):
    """llama-server argv for a GGUF tier. Same choices as the author's llama-swap stack: flash attention, q8_0 KV cache (half the memory, no measurable loss for chat), jinja template, thinking off.
    CPU tiers use about half the logical cores (physical cores; hyper-threads slow decode); GPU tiers offload every layer."""
    t = BY_ID[tier_id]
    if not t["gguf"]: raise ValueError(f"{tier_id} is served by vLLM, see vllm_args()")
    threads = threads or max(2, min(16, (cores or os.cpu_count() or 4) // 2))
    a = ["llama-server", "--host", "127.0.0.1", "--port", str(port), "--model", os.path.join(models_dir, t["gguf"]["file"]), "--alias", tier_id,
         "-c", str(t["ctx"]), "-np", "1", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--jinja", "--reasoning", "off", "--chat-template-kwargs", '{"enable_thinking":false}']
    a += ["-ngl", "99"] if t["placement"] == "gpu" else ["-ngl", "0", "-t", str(threads)]
    return a

def vllm_args(models_dir, port=8002, kv_gib=46, max_seqs=224):
    """vLLM argv for the studio tier, from the author's measured unit (2026-10-30). --kv-cache-memory-bytes pins the footprint (weights ~29 GiB + KV) so it does not depend on what else is on the card; size KV to the lane count.
    vLLM reports 636,321 tokens for 46 GiB, about 78 KB per token (raw KV is 64 KiB: 16 full-attention layers x 4 KV heads x 256 dims x K,V x 2 bytes; the rest is block padding for the hybrid model's Mamba state). 12 GiB holds ~178k tokens.
    Measured on the author's box: 12 GiB saturated at 12 parallel lanes with requests queueing; 46 GiB averaged 26% with lanes running, and reached 99.9% only at the 25-running, 18-waiting peak."""
    t = BY_ID["studio"]
    return ["python", "-m", "vllm.entrypoints.openai.api_server", "--model", os.path.join(models_dir, "Qwen__Qwen3.8-27B-FP8"), "--served-model-name", "qwen38-27b-fp8", "--host", "127.0.0.1", "--port", str(port),
            "--gpu-memory-utilization", "0.52", "--kv-cache-memory-bytes", str(int(kv_gib * 2**30)), "--max-model-len", str(t["ctx"]), "--max-num-seqs", str(max_seqs), "--enable-sleep-mode",
            "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_xml", "--reasoning-parser", "qwen3", "--speculative-config", '{"method":"mtp","num_speculative_tokens":4}']

def kv_budget(tokens_in_flight, kv_bytes_per_token=77_620):
    """GiB of KV cache needed to hold this many tokens at once (studio tier), using vLLM's own reported capacity. Size --kv-cache-memory-bytes from lane count x average context."""
    return round(tokens_in_flight * kv_bytes_per_token / 2**30, 1)

def _models_at(base, timeout=1.5):
    with urllib.request.urlopen(base + "/models", timeout=timeout) as r: return [m["id"] for m in json.load(r).get("data", [])]

_found = {"at": 0.0, "value": None}
def endpoint(probe=_models_at, now=time.time):
    """Find the LLM the crew should talk to: {url, model}, or None. Order: STUDIO_LLM_URL (with optional STUDIO_LLM_MODEL), then any OpenAI-style server on the usual local ports: vLLM 8002, the llama-server tier 8301, Ollama 11434. A hit is remembered for 30 s."""
    if _found["value"] and now() - _found["at"] < 30: return _found["value"]
    env = os.environ.get("STUDIO_LLM_URL", "").rstrip("/")
    for base in ([env] if env else []) + ["http://127.0.0.1:8002/v1", "http://127.0.0.1:8301/v1", "http://127.0.0.1:11434/v1"]:
        try: ids = probe(base)
        except Exception: continue
        model = os.environ.get("STUDIO_LLM_MODEL") or (ids[0] if ids else None)
        if model: _found.update(at=now(), value={"url": base, "model": model}); return _found["value"]
    return None

def command_line(argv): return " ".join(shlex.quote(x) for x in argv)
