"""Tests for PSN_Hash_Phrase_Generator."""

import pytest
from psn_nodes.gen.n_9_deterministic_hash_phrases_for_debuggi import (
    PSN_Hash_Phrase_Generator,
    _hash_to_phrase,
    _WORD_LIST,
    _WORD_LIST_VERSION,
)


def test_deterministic_same_input_same_phrase():
    """Same input always produces the same phrase."""
    node = PSN_Hash_Phrase_Generator()
    result1 = node.run("hello world", 6)
    result2 = node.run("hello world", 6)
    assert result1 == result2
    assert isinstance(result1[0], str)
    assert len(result1[0].split()) == 6


def test_different_inputs_different_phrases():
    """Different inputs produce different phrases."""
    node = PSN_Hash_Phrase_Generator()
    result1 = node.run("input_one", 6)
    result2 = node.run("input_two", 6)
    assert result1[0] != result2[0]


def test_word_count_respected():
    """Phrase contains exactly the requested number of words."""
    node = PSN_Hash_Phrase_Generator()
    for wc in [1, 3, 6, 10, 20]:
        result = node.run("test input", wc)
        words = result[0].split()
        assert len(words) == wc, "Expected %d words, got %d" % (wc, len(words))


def test_all_words_from_word_list():
    """All words in the phrase must come from the static word list."""
    node = PSN_Hash_Phrase_Generator()
    result = node.run("some test string", 10)
    words = result[0].split()
    for word in words:
        assert word in _WORD_LIST, "Word '%s' not in word list" % word


def test_empty_string_input():
    """Empty string should still produce a valid phrase."""
    node = PSN_Hash_Phrase_Generator()
    result = node.run("", 6)
    assert isinstance(result[0], str)
    assert len(result[0].split()) == 6
    # Empty string hash is deterministic
    result2 = node.run("", 6)
    assert result == result2


def test_unicode_input():
    """Unicode input should be handled correctly and deterministically."""
    node = PSN_Hash_Phrase_Generator()
    result1 = node.run("héllo wörld", 6)
    result2 = node.run("héllo wörld", 6)
    assert result1 == result2
    assert len(result1[0].split()) == 6


def test_invalid_word_count_zero():
    """Word count of 0 should raise ValueError."""
    with pytest.raises(ValueError, match="at least 1"):
        _hash_to_phrase("test", 0)


def test_invalid_word_count_negative():
    """Negative word count should raise ValueError."""
    with pytest.raises(ValueError, match="at least 1"):
        _hash_to_phrase("test", -5)


def test_invalid_word_count_too_large():
    """Word count exceeding max should raise ValueError."""
    with pytest.raises(ValueError, match="at most"):
        _hash_to_phrase("test", 100)


def test_invalid_input_type():
    """Non-string input should raise ValueError."""
    with pytest.raises(ValueError, match="must be a string"):
        _hash_to_phrase(12345, 6)


def test_invalid_word_count_type():
    """Non-integer word count should raise ValueError."""
    with pytest.raises(ValueError, match="must be an integer"):
        _hash_to_phrase("test", 6.5)


def test_bool_word_count_rejected():
    """Boolean word count should be rejected (bool is subclass of int)."""
    with pytest.raises(ValueError, match="must be an integer"):
        _hash_to_phrase("test", True)


def test_json_string_input():
    """JSON string input should work and be deterministic."""
    node = PSN_Hash_Phrase_Generator()
    json_input = '{"key": "value", "num": 42}'
    result1 = node.run(json_input, 6)
    result2 = node.run(json_input, 6)
    assert result1 == result2
    assert len(result1[0].split()) == 6


def test_max_word_count():
    """Maximum word count should work."""
    node = PSN_Hash_Phrase_Generator()
    result = node.run("test", 43)
    assert len(result[0].split()) == 43
