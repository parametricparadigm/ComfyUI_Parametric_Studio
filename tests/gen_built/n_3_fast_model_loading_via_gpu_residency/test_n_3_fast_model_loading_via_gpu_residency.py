import torch

import n_3_fast_model_loading_via_gpu_residency as mod


def test_register_and_get():
    mod._cache_clear()
    reg = mod.PSN_Register_Resident_Model()
    model = mod._make_model(torch.ones(2, 2), {"name": "a"})
    handle = reg.run(model, "k1", 300)[0]
    assert handle == "k1"
    got = mod.PSN_Get_Resident_Model().run("k1")
    m, was = got
    assert was is True
    assert m is not None
    assert torch.equal(m["weights"], torch.ones(2, 2))
    # input not mutated
    assert model["meta"] == {"name": "a"}


def test_miss():
    mod._cache_clear()
    m, was = mod.PSN_Get_Resident_Model().run("nope")
    assert m is None
    assert was is False


def test_expiry():
    mod._cache_clear()
    reg = mod.PSN_Register_Resident_Model()
    reg.run(mod._make_model(torch.zeros(1, 1)), "k2", 0)  # ttl 0 -> expires immediately
    m, was = mod.PSN_Get_Resident_Model().run("k2")
    assert was is False
    assert m is None


def test_lru_eviction():
    mod._cache_clear()
    reg = mod.PSN_Register_Resident_Model()
    for i in range(mod._CACHE_MAX_ENTRIES + 2):
        reg.run(mod._make_model(torch.full((1,), float(i))), "key%d" % i, 300)
    # oldest two evicted
    m0, was0 = mod.PSN_Get_Resident_Model().run("key0")
    m1, was1 = mod.PSN_Get_Resident_Model().run("key1")
    assert was0 is False and m0 is None
    assert was1 is False and m1 is None
    mlast, waslast = mod.PSN_Get_Resident_Model().run("key%d" % (mod._CACHE_MAX_ENTRIES + 1))
    assert waslast is True


def test_bad_model():
    reg = mod.PSN_Register_Resident_Model()
    try:
        reg.run("not a model", "k", 10)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        reg.run({"weights": 5}, "k", 10)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_bad_key():
    reg = mod.PSN_Register_Resident_Model()
    try:
        reg.run(mod._make_model(), "", 10)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        mod.PSN_Get_Resident_Model().run(123)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_no_inplace_mutation():
    mod._cache_clear()
    reg = mod.PSN_Register_Resident_Model()
    w = torch.ones(2, 2)
    model = {"weights": w, "meta": {"a": 1}}
    reg.run(model, "k3", 300)
    m, _ = mod.PSN_Get_Resident_Model().run("k3")
    m["weights"].fill_(99)
    m["meta"]["a"] = 2
    assert torch.equal(model["weights"], torch.ones(2, 2))
    assert model["meta"] == {"a": 1}


def test_node_metadata():
    assert mod.NODE_CLASS_MAPPINGS["PSN_Register_Resident_Model"] is mod.PSN_Register_Resident_Model
    assert mod.PSN_Register_Resident_Model.FUNCTION == "run"
    assert mod.PSN_Register_Resident_Model.CATEGORY.startswith("ParametricStudio/")
    it = mod.PSN_Register_Resident_Model.INPUT_TYPES()
    assert "model" in it["required"] and "cache_key" in it["required"]
    assert mod.PSN_Get_Resident_Model.RETURN_TYPES == ("MODEL", "BOOLEAN")


if __name__ == "__main__":
    test_register_and_get()
    test_miss()
    test_expiry()
    test_lru_eviction()
    test_bad_model()
    test_bad_key()
    test_no_inplace_mutation()
    test_node_metadata()
    print("ok")
