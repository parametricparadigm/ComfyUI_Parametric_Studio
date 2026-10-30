import pytest
from psn_nodes.gen.n_9_string_preprocessing_pipeline import (
    PSN_String_Cleaner,
    PSN_String_Normalizer,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_psn_string_cleaner_basic_whitespace():
    node = PSN_String_Cleaner()
    result = node.run("  Hello   World  ", True, False, False)
    assert result[0] == "Hello World"


def test_psn_string_cleaner_lowercase():
    node = PSN_String_Cleaner()
    result = node.run("Hello World", False, True, False)
    assert result[0] == "hello world"


def test_psn_string_cleaner_punctuation():
    node = PSN_String_Cleaner()
    result = node.run("Hello, World! How are you?", False, False, True)
    assert result[0] == "Hello World How are you"


def test_psn_string_cleaner_combined_operations():
    node = PSN_String_Cleaner()
    result = node.run("  Hello,   WORLD!  ", True, True, True)
    assert result[0] == "hello world"


def test_psn_string_cleaner_no_operations():
    node = PSN_String_Cleaner()
    result = node.run("  Hello,   WORLD!  ", False, False, False)
    assert result[0] == "  Hello,   WORLD!  "


def test_psn_string_cleaner_empty_string():
    node = PSN_String_Cleaner()
    result = node.run("", True, True, True)
    assert result[0] == ""


def test_psn_string_cleaner_only_punctuation():
    node = PSN_String_Cleaner()
    result = node.run("!!! ??? ...", True, False, True)
    assert result[0] == ""


def test_psn_string_normalizer_nfc():
    node = PSN_String_Normalizer()
    # é can be represented as a single character (U+00E9) or as e + combining acute accent (U+0065 U+0301)
    decomposed = "e\u0301"  # e + combining acute accent
    result = node.run(decomposed, "NFC")
    assert result[0] == "\u00e9"  # Single character é


def test_psn_string_normalizer_nfd():
    node = PSN_String_Normalizer()
    composed = "\u00e9"  # Single character é
    result = node.run(composed, "NFD")
    assert result[0] == "e\u0301"  # e + combining acute accent


def test_psn_string_normalizer_nfkc():
    node = PSN_String_Normalizer()
    # ﬁ ligature should be decomposed to fi in NFKC
    result = node.run("\ufb01", "NFKC")
    assert result[0] == "fi"


def test_psn_string_normalizer_nfd_ligature():
    node = PSN_String_Normalizer()
    # ﬁ ligature should be decomposed to fi in NFKD
    result = node.run("\ufb01", "NFKD")
    assert result[0] == "fi"


def test_psn_string_normalizer_invalid_form():
    node = PSN_String_Normalizer()
    with pytest.raises(ValueError):
        node.run("test", "INVALID")


def test_psn_string_normalizer_empty_string():
    node = PSN_String_Normalizer()
    result = node.run("", "NFC")
    assert result[0] == ""


def test_node_class_mappings_exist():
    assert "PSN_String_Cleaner" in NODE_CLASS_MAPPINGS
    assert "PSN_String_Normalizer" in NODE_CLASS_MAPPINGS


def test_node_display_names_exist():
    assert "PSN_String_Cleaner" in NODE_DISPLAY_NAME_MAPPINGS
    assert "PSN_String_Normalizer" in NODE_DISPLAY_NAME_MAPPINGS


def test_psn_string_cleaner_input_types_structure():
    input_types = PSN_String_Cleaner.INPUT_TYPES()
    assert "required" in input_types
    assert "text" in input_types["required"]
    assert "remove_whitespace" in input_types["required"]
    assert "lowercase" in input_types["required"]
    assert "remove_punctuation" in input_types["required"]


def test_psn_string_normalizer_input_types_structure():
    input_types = PSN_String_Normalizer.INPUT_TYPES()
    assert "required" in input_types
    assert "text" in input_types["required"]
    assert "normalization_form" in input_types["required"]
    # In ComfyUI, combo inputs are represented as a tuple (list_of_options,)
    assert input_types["required"]["normalization_form"] == (["NFC", "NFD", "NFKC", "NFKD"],)
