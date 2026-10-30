"""Tests for PSN_TokenAnalyzer (pure-logic token analysis for debugging)."""

import json

from psn_nodes.gen.n_8_token_analysis_for_debugging import (
    PSN_TokenAnalyzer,
    _parse_conditioning,
    _normalize_weights,
    _rank_tokens,
    _build_report,
)


def _make_node():
    return PSN_TokenAnalyzer()


def test_basic_json_conditioning():
    node = _make_node()
    payload = json.dumps({"tokens": [1, 2, 3], "weights": [0.5, 0.3, 0.2]})
    count, max_w, report = node.run(payload)
    assert count == 3
    assert abs(max_w - 0.5 / 1.0) < 1e-9
    assert "Total tokens: 3" in report
    assert "token_id=1" in report


def test_weights_sum_to_one_after_normalization():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [10, 20], "weights": [3.0, 1.0]}))
    assert err is None
    normalized, total, all_zero = _normalize_weights(pairs)
    assert not all_zero
    assert abs(total - 4.0) < 1e-9
    s = sum(w for _, w in normalized)
    assert abs(s - 1.0) < 1e-9
    assert abs(normalized[0][1] - 0.75) < 1e-9
    assert abs(normalized[1][1] - 0.25) < 1e-9


def test_list_of_dicts_conditioning():
    node = _make_node()
    payload = json.dumps([{"id": 5, "weight": 2.0}, {"id": 7, "weight": 2.0}])
    count, max_w, report = node.run(payload)
    assert count == 2
    assert abs(max_w - 0.5) < 1e-9
    assert "token_id=5" in report
    assert "token_id=7" in report


def test_plain_int_list_defaults_weights():
    pairs, err = _parse_conditioning(json.dumps([1, 2, 3, 4]))
    assert err is None
    assert len(pairs) == 4
    assert all(w == 1.0 for _, w in pairs)
    normalized, total, all_zero = _normalize_weights(pairs)
    assert abs(total - 4.0) < 1e-9
    assert abs(normalized[0][1] - 0.25) < 1e-9


def test_all_zero_weights_edge_case():
    node = _make_node()
    payload = json.dumps({"tokens": [1, 2], "weights": [0.0, 0.0]})
    count, max_w, report = node.run(payload)
    assert count == 2
    assert max_w == 0.0
    assert "all weights are zero" in report


def test_empty_conditioning_returns_error_report():
    node = _make_node()
    count, max_w, report = node.run("")
    assert count == 0
    assert max_w == 0.0
    assert "Error" in report


def test_invalid_json_returns_error():
    node = _make_node()
    count, max_w, report = node.run("{not valid json")
    assert count == 0
    assert "invalid JSON" in report


def test_mismatched_lengths_rejected():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [1, 2], "weights": [0.5]}))
    assert err is not None
    assert "token count" in err


def test_negative_token_id_rejected():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [-1, 2], "weights": [0.5, 0.5]}))
    assert err is not None
    assert "negative" in err


def test_negative_weight_rejected():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [1], "weights": [-0.5]}))
    assert err is not None
    assert "negative" in err


def test_non_integer_token_id_rejected():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [1.5, 2], "weights": [0.5, 0.5]}))
    assert err is not None
    assert "not an integer" in err


def test_vocabulary_labels_appear_in_report():
    node = _make_node()
    vocab = json.dumps(["<pad>", "hello", "world"])
    payload = json.dumps({"tokens": [1, 2], "weights": [0.6, 0.4]})
    count, max_w, report = node.run(payload, vocabulary=vocab, top_n=5)
    assert count == 2
    assert "(hello)" in report
    assert "(world)" in report


def test_out_of_range_token_warning():
    node = _make_node()
    vocab = json.dumps(["a", "b"])
    payload = json.dumps({"tokens": [1, 99], "weights": [0.5, 0.5]})
    count, max_w, report = node.run(payload, vocabulary=vocab)
    assert "exceed vocabulary size" in report


def test_rank_tokens_orders_by_weight_desc():
    pairs = [(1, 0.1), (2, 0.9), (3, 0.5)]
    top = _rank_tokens(pairs, top_n=2)
    assert top[0] == (2, 0.9)
    assert top[1] == (3, 0.5)


def test_top_n_limits_output():
    node = _make_node()
    payload = json.dumps({"tokens": [1, 2, 3, 4, 5], "weights": [0.2, 0.2, 0.2, 0.2, 0.2]})
    count, max_w, report = node.run(payload, top_n=2)
    assert count == 5
    # Only top 2 lines should be listed
    assert "  1." in report
    assert "  2." in report
    assert "  3." not in report


def test_single_token_normalizes_to_one():
    pairs, err = _parse_conditioning(json.dumps({"tokens": [42], "weights": [7.0]}))
    assert err is None
    normalized, total, all_zero = _normalize_weights(pairs)
    assert not all_zero
    assert abs(normalized[0][1] - 1.0) < 1e-9


def test_unsupported_type_rejected():
    pairs, err = _parse_conditioning(12345)
    assert err is not None
    assert "unsupported" in err
