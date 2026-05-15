"""Week 3 5-stage hybrid pipeline test (BM25 + dense mock + RRF + cross-encoder mock + LLM listwise)。"""
from __future__ import annotations

import pytest

from src.pipeline.five_stage_hybrid import (
    HybridQuery,
    HybridResult,
    run_5_stage_hybrid,
    stage1_bm25,
    stage2_dense_mock,
    stage3_rrf,
    stage4_cross_encoder_mock,
    stage5_llm_listwise_rerank,
    try_dense_available,
)


@pytest.fixture
def sample_query() -> HybridQuery:
    """test fixture: sample query + 5 candidate docs。"""
    return HybridQuery(
        query_text="売掛 回収 遅延 cash flow",
        candidates=[
            "売掛金 回収 サイト 30 日 から 45 日 に 拡大",
            "在庫 削減 計画 立案",
            "売掛 cash flow 改善 余地",
            "vendor 統合 機会 検討",
            "退職率 上昇 中堅 企業",
        ],
        candidate_ids=["CIT-000001", "CIT-000002", "CIT-000003", "CIT-000004", "CIT-000005"],
    )


def test_stage1_bm25(sample_query):
    results = stage1_bm25(sample_query)
    assert len(results) == 5
    # query token に最 match (売掛 / 回収) する CIT-000001 + CIT-000003 が高 score
    by_id = {r.candidate_id: r for r in results}
    top_score = max(r.bm25_score for r in results)
    # CIT-000001 or CIT-000003 が top
    assert by_id["CIT-000001"].bm25_score == top_score or by_id["CIT-000003"].bm25_score == top_score


def test_stage2_dense_mock(sample_query):
    results = stage1_bm25(sample_query)
    results = stage2_dense_mock(sample_query, results)
    assert all(r.dense_score is not None for r in results)
    assert all(0.0 <= r.dense_score <= 1.0 for r in results)


def test_stage3_rrf(sample_query):
    results = stage1_bm25(sample_query)
    results = stage2_dense_mock(sample_query, results)
    results = stage3_rrf(results)
    assert all(r.rrf_score > 0 for r in results)
    # 最高 RRF score = bm25 + dense ともに rank 1 付近 の candidate (CIT-000001)
    sorted_by_rrf = sorted(results, key=lambda r: r.rrf_score, reverse=True)
    assert sorted_by_rrf[0].candidate_id in {"CIT-000001", "CIT-000003"}


def test_stage4_cross_encoder_mock(sample_query):
    results = stage1_bm25(sample_query)
    results = stage2_dense_mock(sample_query, results)
    results = stage4_cross_encoder_mock(sample_query, results)
    assert all(r.cross_encoder_score is not None for r in results)


def test_stage5_llm_listwise_rerank(sample_query):
    results = stage1_bm25(sample_query)
    results = stage2_dense_mock(sample_query, results)
    results = stage3_rrf(results)
    results = stage4_cross_encoder_mock(sample_query, results)
    ranked = stage5_llm_listwise_rerank(results, top_k=3)
    top_3 = [r for r in ranked if r.final_rank > 0]
    assert len(top_3) == 3
    assert top_3[0].final_rank == 1
    assert top_3[1].final_rank == 2
    assert top_3[2].final_rank == 3


def test_run_5_stage_hybrid_full(sample_query):
    """5-stage 全 stage literal 実行 + top-K=5 ranked return。"""
    results = run_5_stage_hybrid(sample_query, top_k=5)
    assert len(results) == 5
    # 全 result に final_rank > 0
    assert all(r.final_rank > 0 for r in results)
    # rank 1 が 最 query match (売掛 / 回収 含む candidate)
    rank_1 = next(r for r in results if r.final_rank == 1)
    assert rank_1.candidate_id in {"CIT-000001", "CIT-000003"}


def test_run_5_stage_hybrid_top_k_smaller_than_candidates(sample_query):
    results = run_5_stage_hybrid(sample_query, top_k=2)
    assert len(results) == 2


def test_try_dense_available():
    """sentence-transformers import 可能性 verify (Week 4 で full active 確認用)。"""
    result = try_dense_available()
    assert isinstance(result, bool)
