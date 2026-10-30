import json, os, struct
import pytest, torch
from safetensors.torch import save_file
from psn import modelsort as M, instances

def mk(path, tensors):
    os.makedirs(os.path.dirname(path), exist_ok=True); save_file({k: torch.zeros(*s, dtype=torch.float16) for k, s in tensors.items()}, path)
FLUX = {f"double_blocks.{i}.img_attn.qkv.weight": (64, 64) for i in range(2)} | {f"single_blocks.{i}.linear1.weight": (64, 64) for i in range(2)}
WAN = {f"blocks.{i}.self_attn.q.weight": (64, 64) for i in range(2)} | {"head.head.weight": (16, 64), "text_embedding.0.weight": (64, 32)}

@pytest.fixture()
def lib(tmp_path, monkeypatch):
    m = tmp_path / "models"; monkeypatch.setattr(M, "MODELS", str(m)); monkeypatch.setattr(instances, "MODELS", str(m))
    mk(f"{m}/_complete_pipelines/Flux.1/diffusion_models/flux1-dev.safetensors", FLUX); mk(f"{m}/_complete_pipelines/Wan2.2/diffusion_models/wan2.2_t2v.safetensors", WAN); (m / "_complete_pipelines" / "SDXL").mkdir(parents=True)
    return m

def test_layout_signature_places_an_unknown_name_with_its_family(lib, tmp_path):
    idx = M.build_index(str(lib), min_bytes=0); p = tmp_path / "in" / "mystery_finetune_v3.safetensors"; mk(str(p), FLUX)
    r = M.classify(str(p), idx); assert r["family"] == "Flux.1" and r["decision"] == "family" and r["confidence"] in ("medium", "high") and "same tensor layout" in r["candidates"][0]["why"][0] and r["role"] == "diffusion_models"
    q = tmp_path / "in" / "other.safetensors"; mk(str(q), WAN); assert M.classify(str(q), idx)["family"] == "Wan2.2"

def test_unknown_layout_is_reported_not_forced(lib, tmp_path):
    p = tmp_path / "in" / "strange_model.safetensors"; mk(str(p), {"foo.bar.weight": (8, 8)}); r = M.classify(str(p), M.build_index(str(lib), min_bytes=0))
    assert r["decision"] == "unknown" and r["family"] is None and r["candidates"] == []

def test_folder_class_and_metadata_are_used_as_evidence(lib, tmp_path):
    d = tmp_path / "in" / "x"; mk(str(d / "unet" / "diffusion_pytorch_model.safetensors"), {"foo.bar.weight": (8, 8)}); json.dump({"_class_name": "StableDiffusionXLPipeline"}, open(d / "unet" / "model_index.json", "w"))
    r = M.classify(str(d / "unet" / "diffusion_pytorch_model.safetensors"), M.build_index(str(lib), min_bytes=0)); assert r["family"] == "SDXL" and "model_index class" in r["candidates"][0]["why"][0]
    p = tmp_path / "in" / "lora.safetensors"; mk(str(p), {"lora_unet_a.lora_down.weight": (4, 8), "lora_unet_a.lora_up.weight": (8, 4)}); assert M.classify(str(p), M.build_index(str(lib), min_bytes=0))["role"] == "loras"

def test_roles_from_tensor_names(lib, tmp_path):
    cases = {"vae": {"encoder.down.0.block.0.conv1.weight": (8, 8), "decoder.up.0.block.0.conv1.weight": (8, 8), "post_quant_conv.weight": (4, 4)}, "text_encoders": {"encoder.block.0.layer.0.SelfAttention.q.weight": (8, 8), "shared.weight": (32, 8)},
             "controlnet": {"input_hint_block.0.weight": (8, 8), "zero_convs.0.0.weight": (8, 8)}, "clip_vision": {"vision_model.embeddings.weight": (8, 8)}}
    for role, t in cases.items():
        p = tmp_path / "r" / f"{role}.safetensors"; mk(str(p), t); assert M.classify(str(p), M.build_index(str(lib), min_bytes=0))["role"] == role, role

def test_gguf_header_reader(tmp_path):
    def kv(k, v): kb = k.encode(); vb = v.encode(); return struct.pack("<Q", len(kb)) + kb + struct.pack("<I", 8) + struct.pack("<Q", len(vb)) + vb
    p = tmp_path / "m.gguf"; p.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 0, 2) + kv("general.architecture", "qwen3") + kv("general.name", "Qwen3 27B") + b"\0" * 4_000_000)
    assert M.gguf_header(str(p)) == {"general.architecture": "qwen3", "general.name": "Qwen3 27B"}; r = M.classify(str(p), M.build_index(str(tmp_path / "none")) if False else {"sig": {}, "params": {}, "families": []}); assert r["role"] == "llm_gguf"

def test_apply_only_adds_symlinks_and_is_idempotent(lib, tmp_path):
    p = tmp_path / "in" / "mystery.safetensors"; mk(str(p), FLUX); idx = M.build_index(str(lib), min_bytes=0); rows = [M.classify(str(p), idx)]
    assert M.apply_links(rows, str(lib), dry=True) and not (lib / "_complete_pipelines/Flux.1/diffusion_models/mystery.safetensors").exists()
    made = M.apply_links(rows, str(lib), dry=False); link = lib / "_complete_pipelines/Flux.1/diffusion_models/mystery.safetensors"; assert made and os.path.islink(link) and os.path.realpath(link) == os.path.realpath(p) and p.exists()
    assert M.apply_links(rows, str(lib), dry=False) == []                                         # second run adds nothing
    amb = dict(rows[0], decision="ambiguous"); assert M.apply_links([amb], str(lib), dry=True) == []  # only confident decisions are linked
