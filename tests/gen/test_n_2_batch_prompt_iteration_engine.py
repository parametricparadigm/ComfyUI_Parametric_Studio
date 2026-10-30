"""Tests for PSN Batch Prompt Iteration Engine nodes."""

import json
import pytest

from psn_nodes.gen.n_2_batch_prompt_iteration_engine import (
    PSN_Batch_Prompt_Loader,
    PSN_Batch_Iterator,
)


def _loader():
    return PSN_Batch_Prompt_Loader()


def _iterator():
    return PSN_Batch_Iterator()


class TestPSN_Batch_Prompt_Loader:
    def test_csv_three_prompts(self):
        node = _loader()
        csv_text = "a cat\na dog\na bird"
        (result_json,) = node.run(csv_text, "csv", ",")
        prompts = json.loads(result_json)
        assert prompts == ["a cat", "a dog", "a bird"]

    def test_csv_with_delimiter(self):
        node = _loader()
        csv_text = "hello,world\nfoo,bar"
        (result_json,) = node.run(csv_text, "csv", ",")
        prompts = json.loads(result_json)
        assert prompts == ["hello", "foo"]

    def test_json_list_of_strings(self):
        node = _loader()
        json_text = json.dumps(["prompt one", "prompt two", "prompt three"])
        (result_json,) = node.run(json_text, "json", ",")
        prompts = json.loads(result_json)
        assert prompts == ["prompt one", "prompt two", "prompt three"]

    def test_json_list_of_objects(self):
        node = _loader()
        json_text = json.dumps([{"prompt": "alpha"}, {"prompt": "beta"}])
        (result_json,) = node.run(json_text, "json", ",")
        prompts = json.loads(result_json)
        assert prompts == ["alpha", "beta"]

    def test_empty_csv_returns_empty_list(self):
        node = _loader()
        (result_json,) = node.run("", "csv", ",")
        assert json.loads(result_json) == []

    def test_empty_json_returns_empty_list(self):
        node = _loader()
        (result_json,) = node.run("", "json", ",")
        assert json.loads(result_json) == []

    def test_invalid_format_raises(self):
        node = _loader()
        with pytest.raises(ValueError, match="format must be"):
            node.run("data", "xml", ",")

    def test_invalid_json_raises(self):
        node = _loader()
        with pytest.raises(json.JSONDecodeError):
            node.run("{not valid json", "json", ",")

    def test_json_non_list_raises(self):
        node = _loader()
        with pytest.raises(ValueError, match="must be a list"):
            node.run('{"key": "val"}', "json", ",")

    def test_json_item_wrong_type_raises(self):
        node = _loader()
        with pytest.raises(ValueError, match="string or an object"):
            node.run("[42]", "json", ",")


class TestPSN_Batch_Iterator:
    def test_iterate_three_prompts_auto_advance(self):
        prompts = ["first", "second", "third"]
        plist_json = json.dumps(prompts)
        node = _iterator()

        current, next_idx, is_done = node.run(plist_json, True)
        assert current == "first"
        assert next_idx == 1
        assert is_done is False

        current, next_idx, is_done = node.run(plist_json, True)
        assert current == "second"
        assert next_idx == 2
        assert is_done is False

        current, next_idx, is_done = node.run(plist_json, True)
        assert current == "third"
        assert next_idx == 3
        assert is_done is True

    def test_iterate_beyond_end_returns_done(self):
        prompts = ["only"]
        plist_json = json.dumps(prompts)
        node = _iterator()

        current, next_idx, is_done = node.run(plist_json, True)
        assert current == "only"
        assert next_idx == 1
        assert is_done is True

        current, next_idx, is_done = node.run(plist_json, True)
        assert current == ""
        assert next_idx == 1
        assert is_done is True

    def test_manual_index_override(self):
        prompts = ["a", "b", "c", "d"]
        plist_json = json.dumps(prompts)
        node = _iterator()

        current, next_idx, is_done = node.run(plist_json, False, index=2)
        assert current == "c"
        assert next_idx == 2
        assert is_done is False

    def test_no_auto_advance_keeps_index(self):
        prompts = ["x", "y", "z"]
        plist_json = json.dumps(prompts)
        node = _iterator()

        current, next_idx, is_done = node.run(plist_json, False)
        assert current == "x"
        assert next_idx == 0
        assert is_done is False

        current, next_idx, is_done = node.run(plist_json, False)
        assert current == "x"
        assert next_idx == 0
        assert is_done is False

    def test_empty_list_immediately_done(self):
        plist_json = json.dumps([])
        node = _iterator()
        current, next_idx, is_done = node.run(plist_json, True)
        assert current == ""
        assert next_idx == 0
        assert is_done is True

    def test_index_clamped_to_valid_range(self):
        prompts = ["a", "b"]
        plist_json = json.dumps(prompts)
        node = _iterator()
        current, next_idx, is_done = node.run(plist_json, False, index=99)
        assert current == ""
        assert next_idx == 2
        assert is_done is True

    def test_invalid_prompt_list_json_raises(self):
        node = _iterator()
        with pytest.raises(json.JSONDecodeError):
            node.run("not json", True)
