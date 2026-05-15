"""Citation infra (T2 ADR-101 inherit pattern、 LlamaIndex CitationQueryEngine literal reuse、 ADR-304 → Week 3 active)。

LlamaIndex CitationQueryEngine は Week 4 で full active (実 chunk index 経由)、 Week 3 = pattern 確立 + Pydantic schema integrity verify。

Citation array (T2 inherit、 CIT-XXXXXX prefix):
  - DriverInsight.citation_array → source chunk link back
  - NextAction → citation_array indirect via DriverInsight reference
  - SentimentEvent → topic_tag citation (本 module で wrap)
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ─── Citation result schema (internal、 operational DB は CIT-XXXXXX prefix string のみ persist) ─

class CitationResult(BaseModel):
    """1 citation entry の internal schema (T2 ADR-101 inherit pattern)。"""

    cit_id: str = Field(..., pattern=r"^CIT-[A-Z0-9-]+$")  # CIT-XXXXXX or CIT-PLACEHOLDER-XXXXXX
    source_doc_id: str  # T2 DOC-XXXXXX inherit or synthetic 「SYNTH-DOC-XXXXXX」
    chunk_id: Optional[str] = None  # T2 CHK-XXXXXX inherit (Week 4 で active)
    page_no: Optional[int] = None
    bbox: Optional[dict] = None  # Docling page/cell/bbox metadata
    excerpt_redacted: str  # 引用 text (PII redact 済)


def create_citation_from_synthetic(
    cit_seq: int,
    source_label: str = "SYNTH-DOC-000001",
    excerpt: str = "(synthetic excerpt for PoC)",
) -> CitationResult:
    """合成 Citation literal 生成 (Week 3 PoC、 Week 4 で T2 LlamaIndex 経由 actual chunk index 接続)。"""
    return CitationResult(
        cit_id=f"CIT-{cit_seq:06d}",
        source_doc_id=source_label,
        chunk_id=None,
        page_no=None,
        bbox=None,
        excerpt_redacted=excerpt,
    )


def citation_id_array(citations: list[CitationResult]) -> list[str]:
    """CitationResult list → CIT-XXXXXX string list (operational DB persist 用)。"""
    return [c.cit_id for c in citations]


# ─── LlamaIndex integration (optional、 Week 4 で full active path) ────

def try_llamaindex_available() -> bool:
    """LlamaIndex CitationQueryEngine が import 可能か verify (Week 4 で active path 確認用)。"""
    try:
        import llama_index.core  # noqa: F401
        return True
    except ImportError:
        return False
