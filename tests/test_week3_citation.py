"""Week 3 Citation infra test (CitationResult Pydantic schema + helper)。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.citation.llamaindex_citation import (
    CitationResult,
    citation_id_array,
    create_citation_from_synthetic,
    try_llamaindex_available,
)


def test_citation_result_valid():
    cit = CitationResult(
        cit_id="CIT-000001",
        source_doc_id="DOC-000010",
        chunk_id="CHK-000123",
        page_no=5,
        bbox={"x": 100, "y": 200, "w": 300, "h": 50},
        excerpt_redacted="(redacted) 売掛回収サイトに関する記述",
    )
    assert cit.cit_id == "CIT-000001"
    assert cit.chunk_id == "CHK-000123"
    assert cit.page_no == 5


def test_citation_result_placeholder_accepted():
    """Week 3 PoC placeholder format も pattern ^CIT-[A-Z0-9-]+$ で literal 許可。"""
    cit = CitationResult(
        cit_id="CIT-PLACEHOLDER-000001",
        source_doc_id="SYNTH-DOC-000001",
        excerpt_redacted="(synthetic excerpt)",
    )
    assert cit.cit_id == "CIT-PLACEHOLDER-000001"


def test_citation_result_invalid_cit_id():
    with pytest.raises(ValidationError):
        CitationResult(
            cit_id="invalid_lower",
            source_doc_id="DOC-000001",
            excerpt_redacted="",
        )


def test_create_citation_from_synthetic():
    cit = create_citation_from_synthetic(cit_seq=42, source_label="SYNTH-DOC-000005")
    assert cit.cit_id == "CIT-000042"
    assert cit.source_doc_id == "SYNTH-DOC-000005"
    assert "synthetic" in cit.excerpt_redacted


def test_citation_id_array():
    cits = [
        create_citation_from_synthetic(cit_seq=1),
        create_citation_from_synthetic(cit_seq=2),
        create_citation_from_synthetic(cit_seq=3),
    ]
    ids = citation_id_array(cits)
    assert ids == ["CIT-000001", "CIT-000002", "CIT-000003"]


def test_try_llamaindex_available():
    """LlamaIndex import 可能性 verify (Week 4 で full active 確認用、 Week 3 では bool 返却のみ)。"""
    result = try_llamaindex_available()
    assert isinstance(result, bool)
