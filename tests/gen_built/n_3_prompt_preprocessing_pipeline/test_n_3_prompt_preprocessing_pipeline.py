import json
from n_3_prompt_preprocessing_pipeline import PSN_PromptCleaner, PSN_PromptSplitter


def test_cleaner_basic():
    node = PSN_PromptCleaner()
    result = node.run("Hello, World!", True, True, 512)
    clean, count = result
    assert clean == "hello world", f"Expected 'hello world', got '{clean}'"
    assert count == 11, f"Expected 11, got {count}"


def test_cleaner_empty_string():
    node = PSN_PromptCleaner()
    result = node.run("", True, True, 512)
    clean, count = result
    assert clean == "", f"Expected empty string, got '{clean}'"
    assert count == 0, f"Expected 0, got {count}"


def test_cleaner_no_normalize_case():
    node = PSN_PromptCleaner()
    result = node.run("Hello, World!", False, True, 512)
    clean, count = result
    assert clean == "Hello World", f"Expected 'Hello World', got '{clean}'"


def test_cleaner_keep_punctuation():
    node = PSN_PromptCleaner()
    result = node.run("Hello, World!", True, False, 512)
    clean, count = result
    assert clean == "hello, world!", f"Expected 'hello, world!', got '{clean}'"


def test_cleaner_max_length():
    node = PSN_PromptCleaner()
    result = node.run("a" * 100, True, True, 10)
    clean, count = result
    assert clean == "a" * 10, f"Expected 10 a's, got '{clean}'"
    assert count == 10, f"Expected 10, got {count}"


def test_cleaner_special_chars():
    node = PSN_PromptCleaner()
    result = node.run("  multiple   spaces  and\ttabs\nnewlines  ", True, True, 512)
    clean, count = result
    assert clean == "multiple spaces and tabs newlines", f"Unexpected: '{clean}'"


def test_splitter_basic():
    node = PSN_PromptSplitter()
    result = node.run("one,two,three", ",")
    parts = json.loads(result[0])
    assert parts == ["one", "two", "three"], f"Expected ['one','two','three'], got {parts}"


def test_splitter_empty_string():
    node = PSN_PromptSplitter()
    result = node.run("", ",")
    parts = json.loads(result[0])
    assert parts == [], f"Expected empty list, got {parts}"


def test_splitter_whitespace_handling():
    node = PSN_PromptSplitter()
    result = node.run("  one ,  two  , three  ", ",")
    parts = json.loads(result[0])
    assert parts == ["one", "two", "three"], f"Expected ['one','two','three'], got {parts}"


def test_splitter_bad_input_empty_delimiter():
    node = PSN_PromptSplitter()
    try:
        node.run("test", "")
        assert False, "Expected ValueError for empty delimiter"
    except ValueError:
        pass


def test_splitter_single_element():
    node = PSN_PromptSplitter()
    result = node.run("just one part", ",")
    parts = json.loads(result[0])
    assert parts == ["just one part"], f"Expected ['just one part'], got {parts}"


if __name__ == "__main__":
    test_cleaner_basic()
    test_cleaner_empty_string()
    test_cleaner_no_normalize_case()
    test_cleaner_keep_punctuation()
    test_cleaner_max_length()
    test_cleaner_special_chars()
    test_splitter_basic()
    test_splitter_empty_string()
    test_splitter_whitespace_handling()
    test_splitter_bad_input_empty_delimiter()
    test_splitter_single_element()
    print("ok")
