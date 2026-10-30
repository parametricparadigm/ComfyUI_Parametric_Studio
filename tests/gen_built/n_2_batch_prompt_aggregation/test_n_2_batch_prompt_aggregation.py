import json
import n_2_batch_prompt_aggregation as m


def test_module_mappings():
    assert "PSN_Batch_Prompt_Loop" in m.NODE_CLASS_MAPPINGS
    assert "PSN_Accumulate_Json" in m.NODE_CLASS_MAPPINGS
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Batch_Prompt_Loop"] == "Batch Prompt Loop"
    assert m.NODE_DISPLAY_NAME_MAPPINGS["PSN_Accumulate_Json"] == "Accumulate JSON"


def test_loop_three_prompts():
    loop = m.PSN_Batch_Prompt_Loop()
    acc = m.PSN_Accumulate_Json()
    ctx = m._new_ctx()
    prompts = "a cat\na dog\na bird"
    paths = []
    for _ in range(3):
        prompt, ctx = loop.run(prompts, ctx)
        # Simulate generation: the "path" is derived from the prompt.
        path = "output/" + prompt.replace(" ", "_") + ".png"
        ctx, json_list = acc.run(path, ctx)
        paths.append(path)
    # After 3 iterations the context should be done.
    assert ctx["done"] is True
    assert ctx["index"] == 3
    assert ctx["paths"] == paths
    # The JSON list must contain exactly 3 paths.
    parsed = json.loads(json_list)
    assert len(parsed) == 3
    assert parsed == paths


def test_loop_exhaustion_returns_empty():
    loop = m.PSN_Batch_Prompt_Loop()
    ctx = m._new_ctx(["only one"])
    p1, ctx = loop.run("", ctx)
    assert p1 == "only one"
    assert ctx["done"] is True
    p2, ctx2 = loop.run("", ctx)
    assert p2 == ""
    assert ctx2["done"] is True
    assert ctx2["index"] == 1


def test_accumulate_special_characters():
    acc = m.PSN_Accumulate_Json()
    ctx = m._new_ctx()
    weird = 'out/"quoted" \\ backslash \u00e9.png'
    ctx, json_list = acc.run(weird, ctx)
    parsed = json.loads(json_list)
    assert parsed == [weird]
    # A second item appends, does not replace.
    ctx, json_list2 = acc.run("second.png", ctx)
    parsed2 = json.loads(json_list2)
    assert parsed2 == [weird, "second.png"]


def test_no_in_place_mutation():
    loop = m.PSN_Batch_Prompt_Loop()
    acc = m.PSN_Accumulate_Json()
    original = m._new_ctx(["p1", "p2"])
    snapshot = json.loads(json.dumps(original))
    _, ctx = loop.run("", original)
    ctx, _ = acc.run("x.png", ctx)
    # The original dict must be untouched.
    assert original == snapshot
    assert original["index"] == 0
    assert original["paths"] == []


def test_bad_ctx_input():
    loop = m.PSN_Batch_Prompt_Loop()
    acc = m.PSN_Accumulate_Json()
    # Passing a non-dict context should not crash; it is normalised.
    prompt, ctx = loop.run("hello\nworld", "not a dict")
    assert prompt == "hello"
    assert isinstance(ctx, dict)
    assert ctx["prompts"] == ["hello", "world"]
    # Bad item type is coerced to string.
    ctx, json_list = acc.run(12345, ctx)
    parsed = json.loads(json_list)
    assert parsed == ["12345"]


def test_empty_prompts():
    loop = m.PSN_Batch_Prompt_Loop()
    ctx = m._new_ctx()
    prompt, ctx = loop.run("   ", ctx)
    assert prompt == ""
    assert ctx["done"] is True
    assert ctx["index"] == 0


def test_input_types_and_metadata():
    for cls in (m.PSN_Batch_Prompt_Loop, m.PSN_Accumulate_Json):
        it = cls.INPUT_TYPES()
        assert "required" in it
        assert cls.FUNCTION == "run"
        assert cls.CATEGORY.startswith("ParametricStudio/")
        assert isinstance(cls.RETURN_TYPES, tuple)
        assert isinstance(cls.RETURN_NAMES, tuple)
        assert len(cls.RETURN_TYPES) == len(cls.RETURN_NAMES)


def main():
    test_module_mappings()
    test_loop_three_prompts()
    test_loop_exhaustion_returns_empty()
    test_accumulate_special_characters()
    test_no_in_place_mutation()
    test_bad_ctx_input()
    test_empty_prompts()
    test_input_types_and_metadata()
    print("ok")


if __name__ == "__main__":
    main()
