"""DriverInsight 抽出 (T1/T2/T3 既存 5-stage hybrid pipeline literal reuse + LLMProvider 経由、 ADR-304 順守)。

Week 2 PoC simplified path:
  - anomaly 検出 結果 (AnomalyResult) を入力 source
  - LLMProvider.generate_kpi_driver_insight で driver statement + factors + confidence 生成
  - Citation link back は Week 2 では mock placeholder (Week 3 で literal active = T2 LlamaIndex Citation reuse)

5-stage hybrid pipeline literal reuse path (Week 3 で full active):
  - Stage 1 BM25: 過去 PMI driver factor library から sparse 検索
  - Stage 2 dense: e5-large で driver factor semantic search
  - Stage 3 RRF: rank fusion
  - Stage 4 cross-encoder: ms-marco rerank
  - Stage 5 LLM listwise: Claude CoT で 最終 driver factor + reasoning
"""
from __future__ import annotations

import secrets
from typing import Optional

from src.anomaly.detect_isolation_forest import AnomalyResult
from src.llm.provider import LLMProvider, default_provider
from src.schema.types import DriverInsight, KpiDefinition


def _seq_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:06d}"


def extract_driver_insight(
    anomaly: AnomalyResult,
    kpi_def: KpiDefinition,
    cp_id: str,
    dr_seq: int,
    provider: Optional[LLMProvider] = None,
) -> DriverInsight:
    """1 AnomalyResult → 1 DriverInsight 抽出 (LLMProvider 経由、 試作 = MockProvider)。

    Citation link back は Week 2 では mock placeholder (`CIT-PLACEHOLDER-XXXXXX`)、 Week 3 で literal active。
    """
    if provider is None:
        provider = default_provider()

    statement, factors, confidence = provider.generate_kpi_driver_insight(
        kpi_name=kpi_def.name,
        kpi_dimension=kpi_def.dimension,
        observed_value=anomaly.value,
        target_value=kpi_def.target,
        day_n=anomaly.day_n,
        anomaly_score=anomaly.anomaly_score,
    )

    # Citation array = Week 2 placeholder (T2 LlamaIndex Citation literal reuse は Week 3 で active)
    citation_array = [f"CIT-PLACEHOLDER-{anomaly.day_n:06d}"]

    return DriverInsight(
        dr_id=_seq_id("DR", dr_seq),
        cp_id=cp_id,
        ks_id_ref=anomaly.ks_id,
        statement_redacted=statement,
        driver_factors=factors,
        citation_array=citation_array,
        confidence=confidence,
    )


def batch_extract_drivers(
    anomalies: list[AnomalyResult],
    kpi_defs: dict[str, KpiDefinition],
    cp_id: str,
    start_seq: int = 1,
    provider: Optional[LLMProvider] = None,
) -> list[DriverInsight]:
    """top-K anomaly 全件 → DriverInsight list 生成 (orchestrator から call)。"""
    insights: list[DriverInsight] = []
    for i, a in enumerate(anomalies):
        kpi_def = kpi_defs.get(a.kp_id)
        if kpi_def is None:
            continue
        insights.append(extract_driver_insight(
            anomaly=a,
            kpi_def=kpi_def,
            cp_id=cp_id,
            dr_seq=start_seq + i,
            provider=provider,
        ))
    return insights
