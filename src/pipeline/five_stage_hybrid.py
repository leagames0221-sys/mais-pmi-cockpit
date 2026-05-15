"""5-stage hybrid pipeline。

Stage 構成:
  Stage 1: BM25 sparse (rank-bm25、 active = lightweight)
  Stage 2: dense embedding (sentence-transformers multilingual-e5、 optional import for heavy load)
  Stage 3: RRF (Reciprocal Rank Fusion、 active = pure Python)
  Stage 4: cross-encoder rerank (sentence-transformers ms-marco、 optional import)
  Stage 5: LLM listwise (LLMProvider 経由、 active = MockProvider deterministic)

Week 3 default behavior:
  - BM25 + RRF + LLM listwise = active (lightweight、 PoC 確立必須)
  - dense + cross-encoder = optional (実 model load = heavy、 mock fallback path)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rank_bm25 import BM25Okapi


@dataclass
class HybridQuery:
    """5-stage hybrid pipeline 入力 query。"""
    query_text: str
    candidates: list[str] # source document chunk texts (BM25 fit 対象)
    candidate_ids: list[str] # corresponding chunk ids (CIT-XXXXXX or synthetic)


@dataclass
class HybridResult:
    """1 candidate に対する hybrid score 結果 (final ranking 用)。"""
    candidate_id: str
    candidate_text: str
    bm25_score: float
    dense_score: Optional[float] = None # Stage 2 (sentence-transformers active 時のみ)
    rrf_score: float = 0.0
    cross_encoder_score: Optional[float] = None # Stage 4
    final_rank: int = 0 # 0 = unranked


# ─── Stage 1: BM25 ────────────────────────────────────────────────────

def stage1_bm25(query: HybridQuery) -> list[HybridResult]:
    """rank-bm25 で sparse lexical 検索、 全 candidate に score 付与。"""
    tokenized_candidates = [c.split() for c in query.candidates]
    bm25 = BM25Okapi(tokenized_candidates)
    scores = bm25.get_scores(query.query_text.split())
    return [
        HybridResult(
            candidate_id=cid,
            candidate_text=ctext,
            bm25_score=float(s),
        )
        for cid, ctext, s in zip(query.candidate_ids, query.candidates, scores)
    ]


# ─── Stage 2: dense embedding (optional、 sentence-transformers heavy) ─

def try_dense_available() -> bool:
    """sentence-transformers 利用可能 verify (Week 4 で full active path 確認用)。"""
    try:
        import sentence_transformers # noqa: F401
        return True
    except ImportError:
        return False


def stage2_dense_mock(query: HybridQuery, results: list[HybridResult]) -> list[HybridResult]:
    """dense embedding score の mock (Week 3 PoC、 Week 4 で actual e5-large encode に literal swap)。

    PoC mock: query token と candidate token の Jaccard 類似度を proxy 採用 (deterministic + lightweight)。
    """
    query_tokens = set(query.query_text.split())
    for r in results:
        candidate_tokens = set(r.candidate_text.split())
        if query_tokens and candidate_tokens:
            jaccard = len(query_tokens & candidate_tokens) / len(query_tokens | candidate_tokens)
            r.dense_score = float(jaccard)
        else:
            r.dense_score = 0.0
    return results


# ─── Stage 3: RRF (Reciprocal Rank Fusion、 active = pure Python) ────

def stage3_rrf(results: list[HybridResult], k: int = 60) -> list[HybridResult]:
    """BM25 rank + dense rank を RRF score に literal fuse。"""
    # BM25 rank
    sorted_by_bm25 = sorted(results, key=lambda r: r.bm25_score, reverse=True)
    bm25_rank = {id(r): rank + 1 for rank, r in enumerate(sorted_by_bm25)}
    # dense rank (None なら BM25 rank 単独 使用)
    has_dense = all(r.dense_score is not None for r in results)
    if has_dense:
        sorted_by_dense = sorted(results, key=lambda r: r.dense_score, reverse=True)
        dense_rank = {id(r): rank + 1 for rank, r in enumerate(sorted_by_dense)}
    else:
        dense_rank = {}

    for r in results:
        rrf = 1.0 / (k + bm25_rank[id(r)])
        if has_dense:
            rrf += 1.0 / (k + dense_rank[id(r)])
        r.rrf_score = rrf
    return results


# ─── Stage 4: cross-encoder rerank (optional) ─────────────────────────

def stage4_cross_encoder_mock(query: HybridQuery, results: list[HybridResult]) -> list[HybridResult]:
    """cross-encoder rerank の mock (Week 4 で actual ms-marco-MiniLM-L-12-v2 に swap)。

    PoC mock: BM25 + dense scores の weighted sum (BM25=0.4, dense=0.6) を cross-encoder proxy。
    """
    for r in results:
        bm25_norm = r.bm25_score / (max((rr.bm25_score for rr in results), default=1.0) + 1e-9)
        dense = r.dense_score or 0.0
        r.cross_encoder_score = 0.4 * bm25_norm + 0.6 * dense
    return results


# ─── Stage 5: LLM listwise rerank (LLMProvider 経由、 MockProvider default) ─

def stage5_llm_listwise_rerank(results: list[HybridResult], top_k: int = 5) -> list[HybridResult]:
    """LLM listwise CoT で最終 ranking。

    実 LLM listwise call は LLMProvider 経由で Week 4 active、 本 PoC = cross_encoder_score 順 採用。
    """
    sorted_results = sorted(
        results,
        key=lambda r: (r.cross_encoder_score or r.rrf_score),
        reverse=True,
    )
    for rank, r in enumerate(sorted_results[:top_k], start=1):
        r.final_rank = rank
    return sorted_results


# ─── Full pipeline entry ──────────────────────────────────────────────

def run_5_stage_hybrid(query: HybridQuery, top_k: int = 5) -> list[HybridResult]:
    """5-stage hybrid pipeline literal run、 top-K ranked results 返却。"""
    results = stage1_bm25(query)
    results = stage2_dense_mock(query, results) # Week 4 で real swap path
    results = stage3_rrf(results)
    results = stage4_cross_encoder_mock(query, results) # Week 4 で real swap path
    results = stage5_llm_listwise_rerank(results, top_k=top_k)
    return [r for r in results if r.final_rank > 0]
