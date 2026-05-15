"""NextAction recommender。

flow:
  1. DriverInsight → LLMProvider.generate_next_action_candidates で 5 候補 ranked
  2. T3 CommunicationKit (CK-XXXXXX) から audience_mapping を literal reference
  3. priority_rank = anomaly_score weight + dimension priority で決定 (Week 2 PoC = anomaly score 順)
  4. due_day_n = current day_n + dimension-specific buffer (Week 2 PoC = default 14 日)
"""
from __future__ import annotations

import secrets
from typing import Optional

from src.llm.provider import LLMProvider, default_provider
from src.schema.types import (
    DriverInsight,
    KpiDefinition,
    NextAction,
    NextActionCandidate,
)


def _seq_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:06d}"


# Week 2 PoC = mock CommunicationKit reference (Week 3 で literal active、 T3 API output 流用)
def _mock_ck_id_for_dim(dimension: str) -> str:
    """dimension → mock CK-XXXXXX reference (Week 2 placeholder、 Week 3 で literal T3 CK ingestion 経由)。"""
    DIM_TO_CK = {
        "cost": "CK-000001",
        "revenue": "CK-000002",
        "cash_gen": "CK-000003",
        "working_capital": "CK-000004",
        "retention": "CK-000005",
        "vendor_consolidation": "CK-000006",
    }
    return DIM_TO_CK.get(dimension, "CK-000001")


def _due_day_n(current_day_n: int, dimension: str) -> int:
    """dimension-specific buffer で due_day_n 算出。"""
    BUFFER_BY_DIM = {
        "cost": 14,
        "revenue": 14,
        "cash_gen": 7, # 高 urgency
        "working_capital": 14,
        "retention": 7, # 高 urgency
        "vendor_consolidation": 30,
    }
    buf = BUFFER_BY_DIM.get(dimension, 14)
    due = current_day_n + buf
    return min(due, 100) # day_n は 1-100 範囲


def recommend_next_action(
    driver_insight: DriverInsight,
    kpi_def: KpiDefinition,
    current_day_n: int,
    na_seq: int,
    priority_rank: int,
    provider: Optional[LLMProvider] = None,
) -> NextAction:
    """1 DriverInsight → 1 NextAction 推奨 (LLM listwise CoT)。"""
    if provider is None:
        provider = default_provider()

    candidates = provider.generate_next_action_candidates(
        driver_statement=driver_insight.statement_redacted,
        driver_factors=driver_insight.driver_factors,
        kpi_dimension=kpi_def.dimension,
    )

    # Top-ranked candidate を action_statement_redacted に literal 採用 (T3 CK pattern inherit)
    top_action = candidates[0].action if candidates else "(no action proposed)"

    return NextAction(
        na_id=_seq_id("NA", na_seq),
        cp_id=driver_insight.cp_id,
        dr_id_ref=driver_insight.dr_id,
        action_statement_redacted=top_action, # PII redacted: 取引先実名 / 担当者氏名 mention literal 無し
        audience_mapping=_mock_ck_id_for_dim(kpi_def.dimension),
        priority_rank=priority_rank,
        due_day_n=_due_day_n(current_day_n, kpi_def.dimension),
        status="proposed",
        candidates_ranked=candidates,
    )


def batch_recommend(
    driver_insights: list[DriverInsight],
    kpi_defs: dict[str, KpiDefinition],
    ks_to_day_n: dict[str, int],
    start_seq: int = 1,
    provider: Optional[LLMProvider] = None,
) -> list[NextAction]:
    """DriverInsight list 全件 → NextAction list 推奨 (orchestrator から call、 priority_rank = list 順)。"""
    if provider is None:
        provider = default_provider()
    actions: list[NextAction] = []
    for i, dr in enumerate(driver_insights):
        # kpi_def は DriverInsight.ks_id_ref → KpiSnapshot.kp_id → KpiDefinition で resolve
        # ただし本関数では simplification: kpi_defs map と ks_to_day_n map を upstream で構築
        # kp_id は ks_id 経由で resolve、 ただし anomaly 経由で kpi_def 既知のため
        # 簡略: kpi_defs values から DR ↔ kpi_def match (Week 2 PoC、 Week 3 で proper key resolution)
        # ここでは ks_id_ref から kp_id 推定不能のため、 caller 側で kpi_def explicit pass が ideal
        # → orchestrator 側で kpi_def 渡す path を確立 (本関数は kpi_defs map から first match を採用 = PoC simplification)
        kpi_def = next(iter(kpi_defs.values())) # PoC: orchestrator 側で正しい kpi_def を pass する path に依存
        current_day_n = ks_to_day_n.get(dr.ks_id_ref, 1)
        priority_rank = min(i + 1, 5)
        actions.append(recommend_next_action(
            driver_insight=dr,
            kpi_def=kpi_def,
            current_day_n=current_day_n,
            na_seq=start_seq + i,
            priority_rank=priority_rank,
            provider=provider,
        ))
    return actions


def batch_recommend_with_kpi_map(
    pairs: list[tuple[DriverInsight, KpiDefinition, int]],
    start_seq: int = 1,
    provider: Optional[LLMProvider] = None,
) -> list[NextAction]:
    """(DriverInsight, KpiDefinition, current_day_n) triple list → NextAction list (orchestrator-friendly path)。"""
    if provider is None:
        provider = default_provider()
    actions: list[NextAction] = []
    for i, (dr, kpi_def, day_n) in enumerate(pairs):
        priority_rank = min(i + 1, 5)
        actions.append(recommend_next_action(
            driver_insight=dr,
            kpi_def=kpi_def,
            current_day_n=day_n,
            na_seq=start_seq + i,
            priority_rank=priority_rank,
            provider=provider,
        ))
    return actions
