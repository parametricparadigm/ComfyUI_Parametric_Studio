"""The V3 flagship nodes (psn_nodes/flagship.py). Needs a ComfyUI checkout for comfy_api (COMFYUI_PATH or the author's default); skipped without one. Runs on the CPU, writes only to tmp folders, touches no port."""
import asyncio, importlib, json, os, sys, time
import pytest
torch = pytest.importorskip("torch")
COMFY = __import__("psn.paths", fromlist=["x"]).setting("COMFYUI_PATH", default=os.path.expanduser("~/ComfyUI"))
if not os.path.isdir(os.path.join(COMFY, "comfy_api")): pytest.skip("no ComfyUI checkout", allow_module_level=True)
_before = set(sys.modules); _path_added = COMFY not in sys.path
if _path_added: sys.path.append(COMFY)     # append: ComfyUI's own utils/ and app/ must not shadow anything
from comfy.cli_args import args as _comfy_args
_comfy_args.cpu = True     # model_management must never touch the GPU from a test
fs = importlib.import_module("psn_nodes.flagship")
from comfy_api.latest import io

@pytest.fixture(scope="module", autouse=True)
def _forget_comfy_after():
    yield
    if _path_added and COMFY in sys.path: sys.path.remove(COMFY)     # other test files expect a machine without ComfyUI
    for name in set(sys.modules) - _before:
        if name.split(".")[0] in ("comfy", "comfy_api", "comfy_execution", "comfy_config", "folder_paths", "latent_preview", "node_helpers", "nodes", "server", "psn_nodes.flagship"): sys.modules.pop(name, None)
    sys.modules.pop("psn_nodes.flagship", None)

@pytest.fixture()
def folders(tmp_path, monkeypatch):
    import folder_paths
    monkeypatch.setattr(folder_paths, "output_directory", str(tmp_path / "output")); monkeypatch.setattr(folder_paths, "temp_directory", str(tmp_path / "temp"))
    (tmp_path / "output").mkdir(); (tmp_path / "temp").mkdir()
    return tmp_path

def goals():
    pytest.importorskip("fastapi")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path: sys.path.insert(0, root)
    return importlib.import_module("studio.goals")

# ---- every node is a valid V3 node
@pytest.mark.parametrize("cls", fs.NODES)
def test_schema_validates_and_serializes(cls):
    schema = cls.GET_SCHEMA(); assert schema.node_id == cls.__name__ and schema.category == "Parametric/Flagship" and schema.display_name and schema.description
    assert issubclass(cls, io.ComfyNode)
    json.dumps(cls.GET_NODE_INFO_V1()); json.dumps(cls.INPUT_TYPES()); assert list(cls.RETURN_TYPES)

@pytest.mark.parametrize("cls", fs.NODES)
def test_every_input_and_output_has_a_tooltip(cls):
    schema = cls.GET_SCHEMA()
    for i in schema.inputs: assert i.tooltip or i.id in ("idea",) or isinstance(i, io.DynamicInput), (cls.__name__, i.id)
    for o in schema.outputs: assert o.tooltip, (cls.__name__, o.id)

# ---- Director Prompt shares the studio's words
def test_tables_are_the_studios_tables():
    g = goals(); t = fs.goal_tables()
    for name in fs._WANT: assert t[name] == getattr(g, name), name

def test_defaults_write_exactly_what_the_studio_writes():
    g = goals()
    for move in g.CAMERA_MOVES:
        o = {"camera": move, "shot": "auto", "lens": "auto", "lighting": "auto", "mood": "auto"}
        assert fs.compose_director("a boat at dawn.", {"camera": move}, "auto", "auto", "auto", "auto") == g.director_prompt("a boat at dawn.", o)
        for key, values in (("shot", g.SHOTS), ("lens", g.LENSES), ("lighting", g.LIGHTING), ("mood", g.MOODS)):
            for v in values:
                oo = {**o, key: v}; assert fs.compose_director("a boat", {"camera": move}, oo["shot"], oo["lens"], oo["lighting"], oo["mood"]) == g.director_prompt("a boat", oo)

def test_every_move_has_a_control_entry_and_every_choice_changes_only_its_phrase():
    t = fs.goal_tables(); assert set(fs.MOVE_CONTROLS) == set(t["CAMERA_MOVES"])
    for move, controls in fs.MOVE_CONTROLS.items():
        base = t["CAMERA_MOVES"][move]
        for name, choices in controls.items():
            keys = list(choices); assert fs.camera_sentence({"camera": move, name: keys[0]}) == base, (move, name)
            for k in keys[1:]:
                changed = fs.camera_sentence({"camera": move, name: k}); assert changed != base and choices[k] in changed, (move, name, k)

def test_a_longer_orbit_does_not_promise_the_quarter_circles_ending():
    assert "side view" in fs.camera_sentence({"camera": "orbit_left", "arc": "quarter"}) and "side view" not in fs.camera_sentence({"camera": "orbit_left", "arc": "full"})

def test_dynamic_combo_reveals_each_moves_own_controls():
    info = fs.PSN_DirectorPrompt.INPUT_TYPES()["required"]["camera"]; assert info[0] == "COMFY_DYNAMICCOMBO_V3"
    options = {o["key"]: o["inputs"] for o in info[1]["options"]}
    assert set(options["orbit_left"]["required"]) == {"pace", "arc"} and set(options["tracking"]["required"]) == {"speed"} and not options["locked"]["required"]

def test_execute_reads_the_nested_combo_value():
    out = fs.PSN_DirectorPrompt.execute("a boat", {"camera": "orbit_left", "arc": "full", "pace": "slow"}, "wide", "macro", "noir", "tense")
    assert "smooth full circle at a slow pace" in out[0] and out[0].startswith("a boat. Wide shot.") and out[0].endswith("One continuous shot, no cuts.")

# ---- Recast Prompt
def test_recast_defaults_match_the_studio():
    g = goals()
    assert fs.compose_recast("the waiter", "Keep it subtle.") == g.SWAP_PROMPT.format(target="the waiter") + " Keep it subtle."
    assert fs.compose_recast("") == g.SWAP_PROMPT.format(target="the main person")

def test_recast_reference_tags_follow_the_numbers():
    text, tags = fs.PSN_RecastPrompt.execute("the waiter", "", 2, 3).args
    assert "<Video 2>" in text and "<Picture 3>" in text and "<Video 1>" not in text and tags == "<Video 2>,<Picture 3>"

# ---- VRAM Gate
def run_gate(monkeypatch, free_seq, peak=8.0, margin=4.0, free_idle=True):
    import comfy.model_management as mm
    seq, calls = list(free_seq), []
    monkeypatch.setattr(fs, "memory_state", lambda: (seq.pop(0) if len(seq) > 1 else seq[0], "cuda:0"))
    monkeypatch.setattr(mm, "free_memory", lambda need, dev: calls.append(need))
    monkeypatch.setattr(mm, "get_torch_device", lambda: "cuda:0")
    return fs.PSN_VRAMGate.execute("payload", peak, margin, free_idle), calls

def test_gate_passes_the_value_through_when_there_is_room(monkeypatch):
    out, calls = run_gate(monkeypatch, [20.0]); assert out.block_execution is None and out[0] == "payload" and out[1] == 20.0 and "Open" in out[2] and not calls

def test_gate_blocks_with_a_plain_reason_and_a_result_for_the_blocker(monkeypatch):
    out, calls = run_gate(monkeypatch, [5.0, 5.0], free_idle=True)
    assert "5.0 GB free" in out.block_execution and "12.0 GB" in out.block_execution and "Nothing downstream ran" in out.block_execution
    assert out.result is not None     # execution.py ignores block_execution when NodeOutput has no result
    assert calls == [int(12 * 1024 ** 3)]

def test_gate_frees_idle_models_then_opens(monkeypatch):
    out, calls = run_gate(monkeypatch, [5.0, 15.0]); assert out.block_execution is None and "after unloading idle models" in out[2] and calls

def test_gate_never_unloads_when_told_not_to(monkeypatch):
    out, calls = run_gate(monkeypatch, [5.0], free_idle=False); assert out.block_execution and not calls

def test_gate_fingerprint_keeps_a_passing_render_cached_and_never_caches_a_block(monkeypatch):
    monkeypatch.setattr(fs, "memory_state", lambda: (20.0, "cuda:0"))
    assert fs.PSN_VRAMGate.fingerprint_inputs(peak_gb=8.0, margin_gb=4.0) == "open" == fs.PSN_VRAMGate.fingerprint_inputs(peak_gb=8.0, margin_gb=4.0)
    monkeypatch.setattr(fs, "memory_state", lambda: (2.0, "cuda:0"))
    a = fs.PSN_VRAMGate.fingerprint_inputs(peak_gb=8.0, margin_gb=4.0); time.sleep(0.01); assert a != fs.PSN_VRAMGate.fingerprint_inputs(peak_gb=8.0, margin_gb=4.0)
    v = fs.PSN_VRAMGate.fingerprint_inputs(peak_gb=None, margin_gb=4.0); assert v != v     # a linked peak is unknown here: always check

def test_gate_output_type_follows_its_input():
    info = fs.PSN_VRAMGate.GET_NODE_INFO_V1(); assert info["output_matchtypes"][0] == "value" and info["input"]["required"]["value"][0] == "COMFY_MATCHTYPE_V3"

# ---- Shot List
def expand(shots, render):
    out = fs.PSN_ShotList.execute(shots, render); return out, out.expand

def test_storyboard_expands_to_one_card_per_shot_in_number_order_and_joins_them():
    out, g = expand({"shot_0": "a", "shot_10": "c", "shot_2": "b", "shot_3": None}, {"render": "storyboard", "width": 64, "height": 64})
    cards = [n for n in g.values() if n["class_type"] == "PSN_ShotCard"]; batch = [n for n in g.values() if n["class_type"] == "BatchImagesNode"]
    assert [c["inputs"]["text"] for c in cards] == ["a", "b", "c"] and [c["inputs"]["number"] for c in cards] == [1, 2, 3]
    assert len(batch) == 1 and len(batch[0]["inputs"]) == 3 and out[1] == 3 and out[2] == "a\nb\nc" and out[0][0] in g

def test_one_shot_needs_no_join():
    out, g = expand({"shot_0": "a"}, {"render": "storyboard", "width": 64, "height": 64}); assert not [n for n in g.values() if n["class_type"] == "BatchImagesNode"] and g[out[0][0]]["class_type"] == "PSN_ShotCard"

def test_sampler_expands_to_one_render_per_shot_with_forwarded_links_and_rising_seeds():
    r = {"render": "sampler", "model": ["1", 0], "clip": ["1", 1], "vae": ["1", 2], "negative": "blurry", "width": 512, "height": 512, "seed": 7, "steps": 3, "cfg": 2.0, "sampler_name": "euler", "scheduler": "normal"}
    out, g = expand({"shot_0": "a", "shot_1": "b"}, r); by = lambda c: [n for n in g.values() if n["class_type"] == c]
    assert [k["inputs"]["seed"] for k in by("KSampler")] == [7, 8] and all(k["inputs"]["model"] == ["1", 0] for k in by("KSampler")) and all(v["inputs"]["vae"] == ["1", 2] for v in by("VAEDecode"))
    assert len(by("CLIPTextEncode")) == 4 and len(by("EmptyLatentImage")) == 2 and len(by("BatchImagesNode")) == 1

def test_sampler_expansion_only_uses_nodes_and_inputs_core_really_has():
    nodes = pytest.importorskip("nodes")
    for cls_name, used in {"CLIPTextEncode": {"text", "clip"}, "EmptyLatentImage": {"width", "height", "batch_size"}, "KSampler": {"model", "seed", "steps", "cfg", "sampler_name", "scheduler", "positive", "negative", "latent_image", "denoise"}, "VAEDecode": {"samples", "vae"}}.items():
        assert set(nodes.NODE_CLASS_MAPPINGS[cls_name].INPUT_TYPES()["required"]) == used, cls_name

def test_no_shots_is_a_plain_error():
    with pytest.raises(ValueError, match="at least one"): fs.PSN_ShotList.execute({"shot_0": None}, {"render": "storyboard", "width": 64, "height": 64})

def test_shot_card_draws_a_real_image():
    im = fs.PSN_ShotCard.execute("a very long shot description " * 20, 3, 256, 128)[0]
    assert im.shape == (1, 128, 256, 3) and 0.0 <= im.min() and im.max() <= 1.0 and im.std() > 0.01

# ---- Latent Inspector
def smooth_latent(c=4, h=64, w=64):
    yy, xx = torch.meshgrid(torch.linspace(0, 3, h), torch.linspace(0, 3, w), indexing="ij")
    return torch.stack([torch.sin(xx * (i + 1)) + torch.cos(yy * (i + 2)) for i in range(c)])[None]

def test_stats_read_noise_structure_and_flat():
    torch.manual_seed(0)
    assert "pure noise" in fs.read_stats(fs.channel_stats(torch.randn(4, 64, 64)))
    assert "structured" in fs.read_stats(fs.channel_stats(smooth_latent()[0]))
    assert "flat" in fs.read_stats(fs.channel_stats(torch.zeros(4, 64, 64)))

def test_stats_numbers_are_right():
    x = torch.tensor([[[1.0, 3.0], [1.0, 3.0]]]); r = fs.channel_stats(x)[0]
    assert r["mean"] == 2.0 and r["std"] == 1.0 and r["min"] == 1.0 and r["max"] == 3.0 and r["corr"] == pytest.approx(-1.0)
    assert "Latent [1, 1, 2, 2]: 1 channels" in fs.stats_text([r], (1, 1, 2, 2))

def test_views_have_the_right_shape_and_range():
    x = smooth_latent(16, 32, 48)[0]
    g = fs.channel_grid(x); assert g.shape == (4 * 33 - 1, 4 * 49 - 1, 3) and 0 <= g.min() and g.max() <= 1
    assert fs.channel_grid(x, columns=16).shape[:2] == (32, 16 * 49 - 1)
    p = fs.pca_rgb(x); assert p.shape == (32, 48, 3) and 0 <= p.min() and p.max() <= 1 and p.std() > 0.05
    assert fs.histogram_panel(x, 32).shape[2] == 3 and fs.upscale(p, 8).shape == (256, 384, 3)

def test_pca_is_deterministic_and_handles_few_channels_and_flat_latents():
    x = smooth_latent(4, 32, 32)[0]; assert torch.equal(fs.pca_rgb(x), fs.pca_rgb(x.clone()))
    assert fs.pca_rgb(smooth_latent(1, 16, 16)[0]).shape == (16, 16, 3) and fs.pca_rgb(torch.zeros(4, 16, 16)).sum() == 0

def test_video_latents_and_out_of_range_indexes():
    v = torch.randn(2, 16, 5, 8, 8); assert fs.latent_frame(v, 1, 2).shape == (16, 8, 8) and torch.equal(fs.latent_frame(v, 99, 99), v[1, :, 4])

@pytest.mark.parametrize("view,shape", [({"view": "channel_grid", "columns": 2, "per_channel": True, "scale": 2}, (1, 34, 34, 3)), ({"view": "pca_rgb", "clip_percent": 1.0, "scale": 8}, (1, 64, 64, 3)), ({"view": "histogram", "bins": 16}, None)])
def test_execute_returns_a_view_and_stats(folders, view, shape):
    out = asyncio.run(fs.PSN_LatentInspector.execute({"samples": smooth_latent(4, 8, 8)}, view, 0, 0))
    assert out[0].ndim == 4 and (shape is None or tuple(out[0].shape) == shape) and "Reading:" in out[1] and out.ui is not None

# ---- Graph Proof
GRAPH = {"1": {"class_type": "KSampler", "inputs": {"seed": 5, "model": ["2", 0]}}, "2": {"class_type": "Loader", "inputs": {"name": "m.safetensors", "api_key": "hunter2"}}}
def prove(prompt, **kw):
    cls = fs.PSN_GraphProof.PREPARE_CLASS_CLONE({"hidden_inputs": {io.Hidden.prompt: prompt, io.Hidden.extra_pnginfo: {"workflow": {}}}})
    return cls.execute("proof/run", **kw)

def test_same_graph_same_hash_changed_graph_new_hash(folders):
    a, b = prove(GRAPH), prove(json.loads(json.dumps(GRAPH))); assert a[0] == b[0]
    assert prove({**GRAPH, "1": {"class_type": "KSampler", "inputs": {"seed": 6, "model": ["2", 0]}}})[0] != a[0]

def test_hash_ignores_titles_and_the_is_changed_value_execution_writes_into_the_prompt(folders):
    noisy = json.loads(json.dumps(GRAPH)); noisy["1"]["is_changed"] = [time.time()]; noisy["1"]["_meta"] = {"title": "renamed"}
    assert prove(noisy)[0] == prove(GRAPH)[0]

def test_proof_file_holds_settings_verifies_and_catches_tampering(folders):
    out = prove(GRAPH, images=torch.ones(1, 4, 4, 3), note="take 1"); path = folders / "output" / out[1]; doc = json.loads(path.read_text())
    assert out[1].endswith(f"run_{out[0][:12]}.proof.json") and doc["graph_sha256"] == out[0] and doc["note"] == "take 1" and doc["workflow_included"] and doc["pixels"]["shape"] == [1, 4, 4, 3]
    assert doc["settings"]["1"] == {"class_type": "KSampler", "values": {"seed": 5}} and fs.verify_proof(str(path))
    doc["graph"]["1"]["inputs"]["seed"] = 99; path.write_text(json.dumps(doc)); assert not fs.verify_proof(str(path))

def test_secrets_never_reach_the_proof_file(folders):
    out = prove(GRAPH); text = (folders / "output" / out[1]).read_text(); assert "hunter2" not in text and "[redacted]" in text

def test_proof_stays_inside_the_output_folder(folders):
    with pytest.raises(Exception): fs.PSN_GraphProof.PREPARE_CLASS_CLONE({"hidden_inputs": {io.Hidden.prompt: GRAPH}}).execute("../../escape")

def test_proof_always_runs_because_it_cannot_see_the_graph_in_a_fingerprint():
    v = fs.PSN_GraphProof.fingerprint_inputs(); assert v != v

# ---- registration beside V1 nodes
def test_pack_registers_v3_classes_in_the_v1_mapping_the_way_load_custom_node_reads_them():
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("psn_pack_v3_test", os.path.join(root, "__init__.py"), submodule_search_locations=[root])
    m = importlib.util.module_from_spec(spec); sys.modules["psn_pack_v3_test"] = m
    try: spec.loader.exec_module(m)
    finally:
        for k in [k for k in sys.modules if k == "psn_pack_v3_test" or k.startswith("psn_pack_v3_test.")]: sys.modules.pop(k, None)
    for name in fs.NODE_CLASS_MAPPINGS:
        assert m.NODE_CLASS_MAPPINGS[name].__name__ == name and m.NODE_DISPLAY_NAME_MAPPINGS[name] == fs.NODE_DISPLAY_NAME_MAPPINGS[name]
        assert issubclass(m.NODE_CLASS_MAPPINGS[name], io.ComfyNode)
    assert "PSN_Expression" in m.NODE_CLASS_MAPPINGS     # the V1 nodes are still there
