"""Tests for PSN OCR-based prompt extraction (pure-logic core)."""

import json

from psn_nodes.gen.n_3_ocr_based_prompt_extraction_from_tutor import (
    PSN_Tutorial_OCR_Extractor,
    PSN_Prompt_Cleaner,
    _strip_ui,
    _split_sections,
    _build_structured,
    _validate_engine,
    _validate_language,
)


def test_extractor_valid_config_returns_text_and_mask():
    node = PSN_Tutorial_OCR_Extractor()
    raw, mask = node.run("a cat on a mat\nnegative: blur", "Chandra", "en")
    assert raw == "a cat on a mat\nnegative: blur"
    parsed = json.loads(mask)
    assert parsed["language"] == "en"
    assert len(parsed["regions"]) == 2
    assert parsed["regions"][0]["text"] == "a cat on a mat"


def test_extractor_rejects_bad_engine():
    node = PSN_Tutorial_OCR_Extractor()
    raw, mask = node.run("hello", "NotAnEngine", "en")
    assert raw == ""
    assert "error" in json.loads(mask)


def test_extractor_rejects_bad_language():
    node = PSN_Tutorial_OCR_Extractor()
    raw, mask = node.run("hello", "Chandra", "xx")
    assert raw == ""
    assert "error" in json.loads(mask)


def test_extractor_handles_non_string_image():
    node = PSN_Tutorial_OCR_Extractor()
    raw, mask = node.run(12345, "PaddleOCR", "zh")
    assert raw == ""
    parsed = json.loads(mask)
    assert parsed["regions"] == []


def test_cleaner_removes_ui_elements():
    node = PSN_Prompt_Cleaner()
    raw = "Submit\na beautiful sunset\nCancel\nnegative: blur\nOK"
    cleaned, structured = node.run(raw, True, True)
    assert "Submit" not in cleaned
    assert "Cancel" not in cleaned
    assert "OK" not in cleaned
    assert "a beautiful sunset" in cleaned
    doc = json.loads(structured)
    assert doc["prompt"] == "a beautiful sunset"
    assert doc["negative_prompt"] == "blur"


def test_cleaner_keeps_ui_when_disabled():
    node = PSN_Prompt_Cleaner()
    raw = "Submit\na beautiful sunset"
    cleaned, _ = node.run(raw, False, True)
    assert "Submit" in cleaned


def test_cleaner_splits_sections_correctly():
    node = PSN_Prompt_Cleaner()
    raw = ("a red car\n"
           "negative prompt: blur, low quality\n"
           "settings: steps 30, cfg 7")
    cleaned, structured = node.run(raw, True, True)
    doc = json.loads(structured)
    assert doc["prompt"] == "a red car"
    assert "blur" in doc["negative_prompt"]
    assert "steps 30" in doc["settings"]


def test_cleaner_no_format_still_valid_json():
    node = PSN_Prompt_Cleaner()
    raw = "a dog"
    cleaned, structured = node.run(raw, True, False)
    doc = json.loads(structured)
    assert doc["prompt"] == "a dog"


def test_cleaner_handles_empty_and_bad_input():
    node = PSN_Prompt_Cleaner()
    cleaned, structured = node.run("", True, True)
    assert cleaned == ""
    doc = json.loads(structured)
    assert doc["prompt"] == ""
    cleaned2, structured2 = node.run(None, True, True)
    assert cleaned2 == ""
    json.loads(structured2)


def test_strip_ui_removes_embedded_tokens():
    assert _strip_ui("Submit a form") == "a form"
    assert _strip_ui("Cancel") == ""


def test_validate_helpers():
    assert _validate_engine("Chandra")[0] is True
    assert _validate_engine("bad")[0] is False
    assert _validate_language("multi")[0] is True
    assert _validate_language(5)[0] is False


def test_build_structured_roundtrip():
    doc = json.loads(_build_structured("p", "n", "s"))
    assert doc == {"prompt": "p", "negative_prompt": "n", "settings": "s"}
