import json
import torch

import h_purpose_first_prompt_linting_with_ as M


def test_module_structure():
    assert hasattr(M, "NODE_CLASS_MAPPINGS")
    assert hasattr(M, "NODE_DISPLAY_NAME_MAPPINGS")
    assert "PSN_PromptFillerLint" in M.NODE_CLASS_MAPPINGS
    assert "PSN_PromptBeatPlan" in M.NODE_CLASS_MAPPINGS
    cls = M.PSN_PromptFillerLint
    assert cls.FUNCTION == "run"
    assert cls.CATEGORY.startswith("ParametricStudio/")
    it = cls.INPUT_TYPES()
    assert "required" in it and "prompt" in it["required"]
    assert cls.RETURN_TYPES == ("STRING", "STRING", "INT", "FLOAT")


def test_filler_report_basic():
    text = "a very nice shot of a beautiful city"
    rep = M.filler_report(text)
    assert rep["n_words"] == 8
    assert rep["filler_words"] >= 3  # very, nice, beautiful
    assert rep["worst_category"] in M.FILLER_LEXICON
    assert 0.0 <= rep["shares"]["filler"] <= 1.0
    assert abs(rep["shares"]["filler"] + rep["shares"]["purposeful"] + rep["shares"]["neutral"] - 1.0) < 1e-9


def test_filler_report_empty():
    rep = M.filler_report("")
    assert rep["n_words"] == 0
    assert rep["filler_words"] == 0
    assert rep["worst_category"] is None
    assert rep["shares"]["filler"] == 0.0


def test_retry_message_quotes_and_budget():
    text = "a very nice shot, really beautiful and quite stunning"
    rep = M.filler_report(text)
    msg = M.retry_message(rep, secs=5.0, dialogue=False)
    assert '"very"' in msg
    assert '"nice"' in msg
    assert "Rewrite in" in msg
    assert "Structure:" in msg
    assert "hook" in msg


def test_retry_message_empty_prompt():
    rep = M.filler_report("")
    msg = M.retry_message(rep)
    assert "empty" in msg.lower()


def test_beat_plan_tiles_duration():
    beats = M.beat_plan(5.0)
    assert 3 <= len(beats) <= 5
    assert beats[0][1] == 0.0
    assert abs(beats[-1][2] - 5.0) < 1e-9
    for i in range(1, len(beats)):
        assert abs(beats[i][1] - beats[i - 1][2]) < 1e-9
    # half-second grid
    for _, s, e in beats:
        assert abs(s * 2 - round(s * 2)) < 1e-9
        assert abs(e * 2 - round(e * 2)) < 1e-9


def test_beat_plan_short():
    beats = M.beat_plan(1.0)
    assert len(beats) == 3
    assert abs(beats[-1][2] - 1.0) < 1e-9


def test_node_run_lint():
    node = M.PSN_PromptFillerLint()
    msg, report_json, filler_words, filler_share = node.run(
        "a very nice shot of a beautiful city", 5.0, False, 0, 0
    )
    assert isinstance(msg, str) and len(msg) > 10
    data = json.loads(report_json)
    assert data["n_words"] == 8
    assert filler_words >= 3
    assert 0.0 <= filler_share <= 1.0
    assert "beats" in data


def test_node_run_bad_input():
    node = M.PSN_PromptFillerLint()
    try:
        node.run(12345, 5.0, False, 0, 0)
        assert False, "expected TypeError"
    except TypeError:
        pass
    try:
        node.run("hello", -1.0, False, 0, 0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_node_beat_plan_tensor():
    node = M.PSN_PromptBeatPlan()
    text, tensor = node.run(5.0)
    assert isinstance(text, str) and "hook" in text
    assert isinstance(tensor, torch.Tensor)
    assert tensor.dtype == torch.float32
    assert tensor.shape == (1, 5)  # 4 beats -> 5 boundaries
    assert tensor[0, 0].item() == 0.0
    assert abs(tensor[0, -1].item() - 5.0) < 1e-6


def test_keep_clauses():
    text = "a very nice shot"
    rep = M.filler_report(text, keep_clauses=True)
    kept = rep["kept_clauses"]
    assert "very" not in kept
    assert "nice" not in kept
    assert "shot" in kept


def test_no_in_place_mutation():
    text = "a very nice shot"
    rep1 = M.filler_report(text)
    rep2 = M.filler_report(text)
    assert rep1 == rep2
    assert text == "a very nice shot"


if __name__ == "__main__":
    test_module_structure()
    test_filler_report_basic()
    test_filler_report_empty()
    test_retry_message_quotes_and_budget()
    test_retry_message_empty_prompt()
    test_beat_plan_tiles_duration()
    test_beat_plan_short()
    test_node_run_lint()
    test_node_run_bad_input()
    test_node_beat_plan_tensor()
    test_keep_clauses()
    test_no_in_place_mutation()
    print("ok")
