"""Tests for psn_nodes.gen.n_1_auto_generate_pipeline_docs_from_pdfs."""

import json

from psn_nodes.gen.n_1_auto_generate_pipeline_docs_from_pdfs import (
    PSN_PDF_Structured_Extractor,
    PSN_LLM_Doc_Generator,
    _is_safe_pdf_path,
    _split_text_blocks,
    _compute_confidence,
    _generate_markdown,
)


# ---------------------------------------------------------------------------
# PSN_PDF_Structured_Extractor
# ---------------------------------------------------------------------------

def test_extractor_valid_path_returns_blocks_and_metadata():
    node = PSN_PDF_Structured_Extractor()
    raw = "First block.\n\nSecond block.\n\nThird block."
    text, meta, status = node.run(
        pdf_path="docs/pipeline_guide.pdf",
        extract_images=False,
        extract_metadata=True,
        raw_text=raw,
    )
    assert "First block." in text
    assert "Second block." in text
    assert "Third block." in text
    meta_obj = json.loads(meta)
    assert meta_obj["source"] == "docs/pipeline_guide.pdf"
    assert "blocks=3" in status


def test_extractor_rejects_path_traversal():
    node = PSN_PDF_Structured_Extractor()
    text, meta, status = node.run(
        pdf_path="../../etc/passwd.pdf",
        extract_images=False,
        extract_metadata=False,
        raw_text="hello",
    )
    assert text == ""
    assert "ERROR" in status
    assert "path traversal" in status


def test_extractor_rejects_non_pdf_extension():
    node = PSN_PDF_Structured_Extractor()
    text, meta, status = node.run(
        pdf_path="notes.txt",
        extract_images=False,
        extract_metadata=False,
        raw_text="hello",
    )
    assert text == ""
    assert "ERROR" in status
    assert "safe extension" in status


def test_extractor_rejects_absolute_path():
    node = PSN_PDF_Structured_Extractor()
    text, meta, status = node.run(
        pdf_path="/etc/shadow.pdf",
        extract_images=False,
        extract_metadata=False,
        raw_text="hello",
    )
    assert text == ""
    assert "ERROR" in status
    assert "absolute" in status


def test_extractor_empty_raw_text_returns_empty_blocks():
    node = PSN_PDF_Structured_Extractor()
    text, meta, status = node.run(
        pdf_path="empty.pdf",
        extract_images=False,
        extract_metadata=True,
        raw_text="",
    )
    assert text == ""
    assert "blocks=0" in status
    meta_obj = json.loads(meta)
    assert meta_obj["source"] == "empty.pdf"


def test_extractor_metadata_disabled_returns_empty_json():
    node = PSN_PDF_Structured_Extractor()
    text, meta, status = node.run(
        pdf_path="ok.pdf",
        extract_images=False,
        extract_metadata=False,
        raw_text="some text",
    )
    assert json.loads(meta) == {}


# ---------------------------------------------------------------------------
# PSN_LLM_Doc_Generator
# ---------------------------------------------------------------------------

def test_generator_produces_valid_markdown_with_key_terms():
    node = PSN_LLM_Doc_Generator()
    raw = "Load a model.\n\nRun the sampler.\n\nSave the image."
    md, conf = node.run(
        raw_text=raw,
        llm_model="gpt-4",
        doc_style="Detailed",
    )
    assert md.startswith("# Pipeline Documentation")
    assert "Load a model." in md
    assert "Run the sampler." in md
    assert "Save the image." in md
    assert "### Section 1" in md
    assert "### Section 2" in md
    assert "### Section 3" in md
    assert 0.0 <= conf <= 1.0


def test_generator_concise_style_truncates_long_blocks():
    node = PSN_LLM_Doc_Generator()
    long_block = "A" * 500
    md, conf = node.run(
        raw_text=long_block,
        llm_model="llama3",
        doc_style="Concise",
    )
    # Concise style should truncate to ~200 chars + ellipsis.
    assert "…" in md
    # The full 500-char block should NOT appear verbatim.
    assert long_block not in md


def test_generator_tutorial_style_uses_step_headings():
    node = PSN_LLM_Doc_Generator()
    raw = "Step one text.\n\nStep two text."
    md, conf = node.run(
        raw_text=raw,
        llm_model="claude-3",
        doc_style="Tutorial",
    )
    assert "## Tutorial Overview" in md
    assert "### Step 1" in md
    assert "### Step 2" in md


def test_generator_confidence_zero_for_empty_input():
    node = PSN_LLM_Doc_Generator()
    md, conf = node.run(
        raw_text="",
        llm_model="gpt-4",
        doc_style="Detailed",
    )
    assert conf == 0.0
    assert md.startswith("# Pipeline Documentation")


def test_generator_confidence_penalises_very_large_input():
    node = PSN_LLM_Doc_Generator()
    # Create a large input (> 200k chars) to trigger the penalty.
    big_block = "x" * 250_000
    md, conf = node.run(
        raw_text=big_block,
        llm_model="gpt-4",
        doc_style="Concise",
    )
    # Confidence should be lower than for a small input.
    small_md, small_conf = node.run(
        raw_text="small text",
        llm_model="gpt-4",
        doc_style="Concise",
    )
    assert conf < small_conf


# ---------------------------------------------------------------------------
# Helper edge cases
# ---------------------------------------------------------------------------

def test_split_text_blocks_handles_crlf_and_extra_blank_lines():
    raw = "Block A\r\n\r\n\r\nBlock B\n\n\n\nBlock C"
    blocks = _split_text_blocks(raw)
    assert blocks == ["Block A", "Block B", "Block C"]


def test_split_text_blocks_non_string_returns_empty():
    assert _split_text_blocks(None) == []
    assert _split_text_blocks(123) == []


def test_is_safe_pdf_path_non_string():
    ok, reason = _is_safe_pdf_path(12345)
    assert ok is False
    assert "string" in reason


def test_is_safe_pdf_path_empty_string():
    ok, reason = _is_safe_pdf_path("")
    assert ok is False
    assert "empty" in reason


def test_compute_confidence_detailed_style_with_few_blocks():
    # Detailed style with only 1 block should get a penalty.
    conf = _compute_confidence(["short"], "Detailed")
    conf_concise = _compute_confidence(["short"], "Concise")
    assert conf < conf_concise
