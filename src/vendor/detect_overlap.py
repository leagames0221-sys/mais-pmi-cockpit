"""Vendor / SaaS overlap detect (T2 docling reuse + 5-stage hybrid 機能類似度 + 中堅日本企業 vendor 統合 pattern detector 自作、 ADR-301 + ADR-305 順守)。

Stage 構成:
  Stage A: T2 docling parse (Excel/Word/PPT/PDF vendor 契約文書 ingestion、 optional heavy import)
  Stage B: 5-stage hybrid 機能類似度 (BM25 + dense + RRF + cross-encoder + LLM listwise) で vendor 機能 overlap detect
  Stage C: 中堅日本企業 vendor 統合 pattern detector 自作 (印刷 / 物流 / 人材 / 通信 等の業界 vendor の overlap 経験的 pattern、 differentiation core)

PoC default behavior:
  - docling = optional (Week 4 で actual parser swap)、 mock vendor data から直接 detect
  - 5-stage hybrid 機能類似度 = active (rank-bm25 経由)
  - 中堅日本企業 pattern detector = literal active (MAIS 内部 pattern library)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.pipeline.five_stage_hybrid import HybridQuery, run_5_stage_hybrid
from src.schema.types import SaasLicense, VendorContract


# ─── docling availability check ────────────────────────────────────────

def try_docling_available() -> bool:
    """docling 利用可能 verify (Week 4 で actual vendor 契約文書 parser swap path)。"""
    try:
        import docling  # noqa: F401
        return True
    except ImportError:
        return False


# ─── 中堅日本企業 vendor 統合 pattern detector (differentiation core、 ADR-305) ─

# 同 industry_tag = literal 統合候補 default、 + 業界横断 経験的 pattern (印刷 + 物流 = 紙系 / クラウド + 通信 = IT インフラ 等)
INDUSTRY_OVERLAP_CLUSTERS = [
    {"クラウド", "通信", "ソフトウェア"},  # IT インフラ群
    {"印刷", "物流"},  # 紙系
    {"人材", "コンサル"},  # 知的サービス群
]


def _industry_overlap(industry_a: str, industry_b: str) -> bool:
    """同 industry_tag or 業界横断 cluster 内なら overlap 候補 True (中堅日本企業 pattern detector)。"""
    if industry_a == industry_b:
        return True
    for cluster in INDUSTRY_OVERLAP_CLUSTERS:
        if industry_a in cluster and industry_b in cluster:
            return True
    return False


def detect_vendor_overlap(contracts: list[VendorContract], threshold: float = 0.0) -> list[VendorContract]:
    """vendor 契約 list 内で overlap_candidate を literal 算出 (中堅日本企業 pattern + 機能類似度 5-stage)。

    Returns: input list と同件数 VendorContract list、 overlap_candidate field が literal 更新済。
    """
    # 1. industry cluster overlap (中堅日本企業 pattern、 lightweight)
    for vc in contracts:
        overlap_ids = []
        for other in contracts:
            if other.vc_id == vc.vc_id:
                continue
            if _industry_overlap(vc.industry_tag, other.industry_tag):
                overlap_ids.append(other.vc_id)
        vc.overlap_candidate = overlap_ids

    # 2. 5-stage hybrid 機能類似度 (vendor_pseudonym + industry_tag を candidate text、 各 vendor を query で literal 比較)
    # PoC simplified: industry overlap だけで literal 確定 (Week 4 で actual docling 経由 contract text + 5-stage hybrid full active path)
    return contracts


def detect_saas_overlap(licenses: list[SaasLicense], usage_threshold: float = 30.0) -> list[SaasLicense]:
    """SaaS license overlap + 未使用 seat 30% 未満 detect (中堅日本企業 SaaS 統合 pattern)。

    overlap_candidate: usage_pct が threshold 未満 = consolidation 候補 とし、 全 license の overlap_candidate に literal 追加。
    """
    low_usage_ids = [sl.sl_id for sl in licenses if sl.usage_pct < usage_threshold]
    for sl in licenses:
        # 自分自身が low usage → 他 license が overlap_candidate
        # 自分自身が high usage → low usage licenses が overlap_candidate
        if sl.usage_pct < usage_threshold:
            sl.overlap_candidate = [other_id for other_id in low_usage_ids if other_id != sl.sl_id]
        else:
            sl.overlap_candidate = low_usage_ids
    return licenses


def detect_vendor_overlap_with_5stage(contracts: list[VendorContract]) -> list[VendorContract]:
    """5-stage hybrid 経由 vendor 機能類似度 + industry cluster 統合 (PoC active path)。"""
    # Stage 1: industry cluster (lightweight)
    contracts = detect_vendor_overlap(contracts)

    # Stage 2: 5-stage hybrid 機能類似度 (各 vendor を query、 他 vendor を candidate)
    if len(contracts) < 2:
        return contracts

    # candidate texts: pseudonym + industry_tag を結合
    candidate_texts = [f"{vc.vendor_pseudonym} {vc.industry_tag}" for vc in contracts]
    candidate_ids = [vc.vc_id for vc in contracts]

    # 各 vendor を query、 自分以外を candidate にして hybrid run
    # PoC simplified: 全 vendor を 1 query で literal hybrid run、 top-K 1 件以上 match で overlap_candidate に追加
    for query_vc in contracts:
        other_indices = [i for i, c in enumerate(contracts) if c.vc_id != query_vc.vc_id]
        if not other_indices:
            continue
        other_texts = [candidate_texts[i] for i in other_indices]
        other_ids = [candidate_ids[i] for i in other_indices]
        query = HybridQuery(
            query_text=f"{query_vc.vendor_pseudonym} {query_vc.industry_tag}",
            candidates=other_texts,
            candidate_ids=other_ids,
        )
        top_results = run_5_stage_hybrid(query, top_k=3)
        # 5-stage で top-3 + industry cluster で既 追加済 を merge
        existing = set(query_vc.overlap_candidate)
        for r in top_results:
            if r.cross_encoder_score and r.cross_encoder_score > 0.3:
                existing.add(r.candidate_id)
        query_vc.overlap_candidate = sorted(existing)
    return contracts
