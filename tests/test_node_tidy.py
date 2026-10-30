"""The registration tidy pass (psn_nodes/tidy.py): one category tree, names, descriptions, tooltips and hidden duplicates, with no node id or input name changed."""
import importlib, importlib.util, json, os, subprocess, sys
import pytest
from psn_nodes import tidy as T
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_pack(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT]); m = importlib.util.module_from_spec(spec); sys.modules[name] = m
    spec.loader.exec_module(m); return m
@pytest.fixture(scope="module")
def pack():
    pytest.importorskip("torch"); m = load_pack("psn_pack_tidy_test"); yield m
    for k in [k for k in sys.modules if k == "psn_pack_tidy_test" or k.startswith("psn_pack_tidy_test.")]: sys.modules.pop(k, None)
def v1(pack): return {k: c for k, c in pack.NODE_CLASS_MAPPINGS.items() if not hasattr(c, "GET_SCHEMA")}

def test_every_node_sits_in_one_tree_and_none_in_misc(pack):
    cats = {c.CATEGORY for c in v1(pack).values()}; assert all(c.startswith("Parametric/") for c in cats) and "Parametric/Misc" not in cats and len(cats) <= 15

def test_every_node_has_a_name_a_description_and_serializes_with_tooltips(pack):
    for k, c in v1(pack).items():
        assert pack.NODE_DISPLAY_NAME_MAPPINGS[k] != k and c.DESCRIPTION, k
        types = c.INPUT_TYPES(); json.dumps(types); json.dumps(list(c.RETURN_TYPES))
        for section in ("required", "optional"):
            for name, spec in (types.get(section) or {}).items(): assert spec[1]["tooltip"], (k, name)

def test_input_names_types_and_widget_options_are_untouched(pack):
    """Old graphs store widget values by position: order, names and the widget's own options must survive; only tooltip is added."""
    mod = importlib.import_module("psn_nodes.latent"); raw = mod.PSN_LatentNoiseInject.INPUT_TYPES(); done = T.with_tooltips(raw)
    assert list(raw["required"]) == list(done["required"])
    for name, spec in raw["required"].items():
        assert done["required"][name][0] == spec[0]; extra = dict(done["required"][name][1]); extra.pop("tooltip"); assert extra == (spec[1] if len(spec) > 1 else {})
    assert "tooltip" not in raw["required"]["seed"][1]     # the module's own dicts are not written to

def test_a_tooltip_already_written_is_kept():
    assert T.with_tooltips({"required": {"a": ("INT", {"tooltip": "mine"})}})["required"]["a"][1]["tooltip"] == "mine"

def test_tooltip_says_only_what_the_spec_says():
    assert T.tooltip_for("seed", ("INT", {"default": 0, "min": 0, "max": 9})) == "Random seed: the same seed repeats the same result. From 0 to 9. Default 0."
    assert T.tooltip_for("my_value", (["a", "b"],)) == "My value. One of 2 choices."

def test_weak_duplicates_are_hidden_not_deleted_and_point_at_a_real_node(pack):
    for weak, better in T.HIDDEN.items():
        c = pack.NODE_CLASS_MAPPINGS[weak]; assert c.DEPRECATED is True and better in c.DESCRIPTION and hasattr(c, "FUNCTION")
        if better != "PSN_VRAMGate" or "comfy_api" in sys.modules: assert better in pack.NODE_CLASS_MAPPINGS

def test_hidden_only_means_hidden(pack):
    visible = [k for k, c in v1(pack).items() if getattr(c, "DEPRECATED", False)]; assert sorted(visible) == sorted(T.HIDDEN)

def test_network_nodes_say_so_and_the_list_is_current(pack):
    for k in T.NETWORK: assert k in pack.NODE_CLASS_MAPPINGS, k
    assert {"PSN_HttpRequest", "PSN_SlackSend", "PSN_TelegramSend", "PSN_RemoteQueue"} <= T.NETWORK
    import re
    for k in T.NETWORK: assert re.search(r"network|internet|online|http|api|webhook|url|remote|download|upload|server|bridge", pack.NODE_CLASS_MAPPINGS[k].DESCRIPTION, re.I), k

def test_old_categories_stay_searchable(pack):
    c = pack.NODE_CLASS_MAPPINGS["PSN_Semantic_Mask_Gen"]; assert c.CATEGORY == "Parametric/Image" and c.SEARCH_ALIASES == ["semanticmasking"]

def test_lazy_libraries_are_not_imported_by_loading_the_pack():
    code = f"import importlib.util,sys;r={ROOT!r};s=importlib.util.spec_from_file_location('p',r+'/__init__.py',submodule_search_locations=[r]);m=importlib.util.module_from_spec(s);sys.modules['p']=m;s.loader.exec_module(m);print(sorted({{'matplotlib','pandas','pyarrow','cryptography'}}&set(sys.modules)))"
    out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""}, cwd=ROOT, timeout=120)
    assert out.stdout.strip().splitlines()[-1] == "[]", out.stdout + out.stderr[-400:]

def test_lazy_module_imports_on_first_use_and_runs_setup_once():
    from psn_nodes.gen._lazy import LazyModule
    calls = []; m = LazyModule("json", setup=lambda: calls.append(1)); assert not calls and m.dumps({}) == "{}" and m.loads("1") == 1 and calls == [1]
