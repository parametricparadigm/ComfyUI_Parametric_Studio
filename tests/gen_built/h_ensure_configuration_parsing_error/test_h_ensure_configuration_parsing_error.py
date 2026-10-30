"""Tests for h_ensure_configuration_parsing_error."""

import h_ensure_configuration_parsing_error as mod


def test_module_structure():
    assert hasattr(mod, "NODE_CLASS_MAPPINGS")
    assert hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS")
    assert "PSN_ConfigParseGuard" in mod.NODE_CLASS_MAPPINGS
    node_cls = mod.NODE_CLASS_MAPPINGS["PSN_ConfigParseGuard"]
    assert node_cls.FUNCTION == "run"
    assert node_cls.CATEGORY.startswith("ParametricStudio/")
    assert node_cls.RETURN_TYPES == ("INT", "STRING")
    assert node_cls.RETURN_NAMES == ("key_count", "result_or_error")
    it = node_cls.INPUT_TYPES()
    assert "required" in it
    assert "config_text" in it["required"]
    assert "source_name" in it["required"]


def test_parse_success():
    text = "# comment\n\nname: my-skill\nversion: 2\n"
    parsed = mod._parse_config(text, "a.txt")
    assert parsed == {"name": "my-skill", "version": "2"}


def test_parse_empty():
    parsed = mod._parse_config("", "empty.txt")
    assert parsed == {}


def test_error_names_source_missing_colon():
    try:
        mod._parse_config("no separator here", "bad1.txt")
        assert False, "expected ConfigParseError"
    except mod.ConfigParseError as exc:
        assert "bad1.txt" in str(exc)
        assert exc.source == "bad1.txt"


def test_error_names_source_duplicate_key():
    try:
        mod._parse_config("a: 1\na: 2", "bad2.txt")
        assert False, "expected ConfigParseError"
    except mod.ConfigParseError as exc:
        assert "bad2.txt" in str(exc)
        assert "duplicate" in str(exc)


def test_error_names_source_invalid_key():
    try:
        mod._parse_config("bad key: v", "bad3.txt")
        assert False, "expected ConfigParseError"
    except mod.ConfigParseError as exc:
        assert "bad3.txt" in str(exc)
        assert "invalid key" in str(exc)


def test_error_non_string_input():
    try:
        mod._parse_config(12345, "bad4.txt")
        assert False, "expected ConfigParseError"
    except mod.ConfigParseError as exc:
        assert "bad4.txt" in str(exc)


def test_node_run_success():
    node = mod.PSN_ConfigParseGuard()
    count, summary = node.run("a: 1\nb: 2", "cfg.txt")
    assert count == 2
    assert "a=1" in summary and "b=2" in summary


def test_node_run_failure_names_file():
    node = mod.PSN_ConfigParseGuard()
    count, msg = node.run("oops no colon", "myfile.md")
    assert count == 0
    assert "myfile.md" in msg


def test_node_run_blank_source_falls_back():
    node = mod.PSN_ConfigParseGuard()
    count, msg = node.run("oops", "   ")
    assert count == 0
    assert "<unnamed>" in msg


def test_parse_file_wrapper():
    parsed = mod._parse_config_file("x: y", "wrap.txt")
    assert parsed == {"x": "y"}


if __name__ == "__main__":
    test_module_structure()
    test_parse_success()
    test_parse_empty()
    test_error_names_source_missing_colon()
    test_error_names_source_duplicate_key()
    test_error_names_source_invalid_key()
    test_error_non_string_input()
    test_node_run_success()
    test_node_run_failure_names_file()
    test_node_run_blank_source_falls_back()
    test_parse_file_wrapper()
    print("ok")
