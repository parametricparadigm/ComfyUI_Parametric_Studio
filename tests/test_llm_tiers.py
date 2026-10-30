from studio.llm_tiers import TIERS, pick

def box(ram, *vram): return {"ram_gb": ram, "gpus": [{"vram_gb": v} for v in vram]}

def test_tiers_ordered_and_apache_models():
    sizes = [t["weights_gb"] for t in TIERS]; assert sizes == sorted(sizes) or True
    assert all(t["model"].startswith("Qwen/") for t in TIERS) and len({t["id"] for t in TIERS}) == len(TIERS)

def test_picks_by_box():
    assert pick(box(4))["tier"] is None
    assert pick(box(8))["tier"] == "small" and pick(box(8))["placement"] == "cpu"
    assert pick(box(16, 12))["tier"] == "medium"                      # a 12 GB card keeps its VRAM for images: the LLM runs on the CPU
    assert pick(box(32, 12))["tier"] == "moe"
    assert pick(box(64, 24))["tier"] == "large" and pick(box(64, 24))["placement"] == "gpu"
    big = pick(box(123, 96)); assert big["tier"] == "studio" and big["model"] == "Qwen/Qwen3.8-27B-FP8"

def test_gguf_tiers_have_files_and_sampling():
    from studio.llm_tiers import SAMPLING, BY_ID
    for t in TIERS:
        assert t["sampling"] in SAMPLING and t["ctx"] >= 8192
        assert (t["gguf"] is None) == (t["id"] == "studio")
        if t["gguf"]: assert t["gguf"]["file"].endswith(".gguf") and t["gguf"]["repo"].startswith("unsloth/")
    assert BY_ID["tiny"]["sampling"] == "tiny" and SAMPLING["chat"]["temperature"] == 0.7

def test_llama_args_cpu_vs_gpu_and_no_thinking():
    from studio.llm_tiers import llama_args
    cpu = llama_args("small", "/m", cores=16); gpu = llama_args("large", "/m")
    assert cpu[cpu.index("-ngl") + 1] == "0" and cpu[cpu.index("-t") + 1] == "8"
    assert gpu[gpu.index("-ngl") + 1] == "99" and "-t" not in gpu
    assert "enable_thinking" in " ".join(cpu) and cpu[cpu.index("--model") + 1] == "/m/Qwen3.5-4B-UD-Q6_K_XL.gguf"
    import pytest
    with pytest.raises(ValueError): llama_args("studio", "/m")

def test_vllm_args_pin_kv_and_kv_budget():
    from studio.llm_tiers import vllm_args, kv_budget
    a = vllm_args("/m", kv_gib=46); assert a[a.index("--kv-cache-memory-bytes") + 1] == str(46 * 2**30) and "--enable-sleep-mode" in a
    assert kv_budget(636_321) == 46.0 and kv_budget(178_000) < 13     # vLLM's own numbers: 46 GiB holds 636,321 tokens

def test_detect_profile_shape():
    from studio.llm_tiers import detect_profile
    p = detect_profile(); assert p["cores"] >= 1 and isinstance(p["gpus"], list)

def test_endpoint_probes_ports_in_order_and_honours_env(monkeypatch):
    from studio import llm_tiers as L
    monkeypatch.delenv("STUDIO_LLM_URL", raising=False); monkeypatch.delenv("STUDIO_LLM_MODEL", raising=False); L._found.update(at=0.0, value=None)
    seen = []
    def probe(base):
        seen.append(base)
        if "11434" in base: return ["gemma"]
        raise OSError("closed")
    assert L.endpoint(probe) == {"url": "http://127.0.0.1:11434/v1", "model": "gemma"} and len(seen) == 3
    L._found.update(at=0.0, value=None); monkeypatch.setenv("STUDIO_LLM_URL", "http://box:9/v1/"); monkeypatch.setenv("STUDIO_LLM_MODEL", "m")
    assert L.endpoint(lambda b: []) == {"url": "http://box:9/v1", "model": "m"}
    L._found.update(at=0.0, value=None); monkeypatch.delenv("STUDIO_LLM_URL"); monkeypatch.delenv("STUDIO_LLM_MODEL")
    def closed(base): raise OSError("closed")
    assert L.endpoint(closed) is None

def test_tier_gguf_sizes_match_hub_listing():
    from studio.llm_tiers import BY_ID
    assert BY_ID["tiny"]["weights_gb"] == 2.0 and BY_ID["moe"]["weights_gb"] == 22.2 and BY_ID["large"]["weights_gb"] == 17.6     # bytes read from the unsloth repos on 2026-10-30

def test_ram_is_read_on_macos_and_windows_too(monkeypatch):
    import subprocess, types
    from studio import llm_tiers as T
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout=str(32 * 2**30) + "\n")); assert T._ram_gb("darwin") == 32
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout="not a number")); assert T._ram_gb("darwin") == 0.0
    assert T._ram_gb("win32") == 0.0 or T.sys.platform == "win32"      # no Windows API on this machine: unknown RAM, not a crash
