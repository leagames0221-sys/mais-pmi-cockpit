"""T4 LangGraph state graph: state schema (TypedDict + Annotated parallel agent merge、 T3 inherit pattern)。

T3 only checkpoint):
  - MemorySaver checkpointer (file 系 / SQLite 系 不使用、 memory-only)
  - parallel agent merge は Annotated[list, _merge_list] で reducer 明示
  - Pydantic schema は src/schema/types.py で literal 統一、 state 内 list field の type は schema reference

T4 specific:
  - 4 KPI dimension parallel anomaly detect (T3 4 軸 parallel agent pattern inherit)
  - top-K anomaly → DriverInsight → NextAction の sequential pipeline
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from src.anomaly.detect_isolation_forest import AnomalyResult
from src.schema.types import (
    CockpitProject,
    DriverInsight,
    KpiDefinition,
    KpiSnapshot,
    NextAction,
    RetentionRisk,
    SaasLicense,
    SentimentEvent,
    T4Output,
    VendorContract,
)


def _merge_list(left: list, right: list) -> list:
    """LangGraph parallel agent merge reducer。"""
    return left + right


class T4State(TypedDict, total=False):
    """LangGraph DAG state (parallel agent merge 対応、 T3 pattern inherit)。"""

    # T3 input
    t3_output: dict # T3 API output dict (ingest_t3_node の input)

    # T3 → T4 ingestion 結果
    cockpit_project: CockpitProject
    kpi_definitions: list[KpiDefinition]
    retention_risks: list[RetentionRisk]

    # 合成 KpiSnapshot (data gen 経由、 actual = real KPI feed)
    kpi_snapshots: list[KpiSnapshot]

    # parallel agent output (4 dim 並列で anomaly 検出 → merge)
    anomaly_results: Annotated[list[AnomalyResult], _merge_list]

    # top-K anomaly → DriverInsight → NextAction (sequential)
    top_anomalies: list[AnomalyResult]
    driver_insights: list[DriverInsight]
    next_actions: list[NextAction]

    # Week 3 layer (sentiment + vendor、 parallel to anomaly)
    raw_messages: list[dict] # Slack/Teams/アンケート mock input
    raw_vendor_contracts: list[VendorContract] # data gen 経由の合成 vendor
    raw_saas_licenses: list[SaasLicense] # data gen 経由の合成 SaaS
    sentiment_events: list[SentimentEvent] # sentiment_node output
    vendor_contracts: list[VendorContract] # vendor_node output (overlap_candidate 更新済)
    saas_licenses: list[SaasLicense] # vendor_node output (overlap_candidate 更新済)

    # finalize: T4Output container
    output: T4Output
