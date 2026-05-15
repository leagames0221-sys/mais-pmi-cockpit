"""T4 LangGraph DAG build (KPI ingestion → 4 dim parallel anomaly → driver → next action → finalize、 ADR-304 順守)。

DAG 構造:
  START → ingest_t3
        → [kpi_anomaly_cost, kpi_anomaly_revenue, kpi_anomaly_cash_gen, kpi_anomaly_working_capital] (parallel merge)
        → top_anomaly_select
        → driver_insight
        → next_action_recommender
        → finalize_t4_output
        → END

T3 ADR-204 inherit (CVE-2026-28277 不発設計):
  - MemorySaver checkpointer (memory-only、 SQLite / file 系 不使用)
  - parallel agent merge は Annotated[list, _merge_list] reducer 明示 (state.py)
  - Pydantic schema は src/schema/types.py SSoT、 state 内 reference のみ
"""
from __future__ import annotations

from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.anomaly.detect_isolation_forest import (
    AnomalyResult,
    detect_anomalies,
    filter_top_anomalies,
)
from src.driver.extract_driver import batch_extract_drivers
from src.integration.ingest_t3_output import ingest_t3_output
from src.llm.provider import LLMProvider, default_provider
from src.next_action.recommend import batch_recommend_with_kpi_map
from src.orchestrator.state import T4State
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
from src.sentiment.analyze_message import batch_analyze_messages
from src.vendor.detect_overlap import detect_saas_overlap, detect_vendor_overlap


# ─── Node functions ────────────────────────────────────────────────────

def ingest_t3_node(state: T4State) -> dict:
    """T3 API output → CockpitProject + KpiDefinition 4 dim + RetentionRisk (ADR-302 mapping)。"""
    t3_output = state["t3_output"]
    t4_partial = ingest_t3_output(t3_output)
    return {
        "cockpit_project": t4_partial.cockpit_project,
        "kpi_definitions": t4_partial.kpi_definitions,
        "retention_risks": t4_partial.retention_risks,
        # kpi_snapshots は data gen 経由で先に state にあるか、 別 node で生成
    }


def _build_anomaly_node_for_dim(dimension: str):
    """4 KPI dim ごとに parallel anomaly detect node (T3 4 軸 agent parallel pattern inherit)。"""

    def anomaly_node(state: T4State) -> dict:
        kpi_defs = state.get("kpi_definitions", [])
        kpi_snapshots = state.get("kpi_snapshots", [])
        # dimension に該当する kpi_def filter
        dim_kpi_defs = [kp for kp in kpi_defs if kp.dimension == dimension]
        if not dim_kpi_defs:
            return {"anomaly_results": []}
        results: list[AnomalyResult] = []
        for kp in dim_kpi_defs:
            kp_snapshots = [s for s in kpi_snapshots if s.kp_id == kp.kp_id]
            results.extend(detect_anomalies(kp_snapshots, kp))
        return {"anomaly_results": results}

    return anomaly_node


def top_anomaly_select_node(state: T4State) -> dict:
    """全 dim merge 後の anomaly_results から top-K (default 5) を filter (NextAction trigger source)。"""
    all_anomalies = state.get("anomaly_results", [])
    top = filter_top_anomalies(all_anomalies, top_k=5)
    return {"top_anomalies": top}


def driver_insight_node(state: T4State, provider: Optional[LLMProvider] = None) -> dict:
    """top-K anomaly → DriverInsight 抽出 (LLMProvider 経由)。"""
    top = state.get("top_anomalies", [])
    kpi_defs = state.get("kpi_definitions", [])
    cp = state["cockpit_project"]
    kpi_def_by_kp_id = {kp.kp_id: kp for kp in kpi_defs}
    insights = batch_extract_drivers(
        anomalies=top,
        kpi_defs=kpi_def_by_kp_id,
        cp_id=cp.cp_id,
        start_seq=1,
        provider=provider,
    )
    return {"driver_insights": insights}


def next_action_node(state: T4State, provider: Optional[LLMProvider] = None) -> dict:
    """DriverInsight → NextAction 5 候補 ranked + audience_mapping reference。"""
    insights = state.get("driver_insights", [])
    top = state.get("top_anomalies", [])
    kpi_defs = state.get("kpi_definitions", [])
    kpi_def_by_kp_id = {kp.kp_id: kp for kp in kpi_defs}
    anomaly_by_ks = {a.ks_id: a for a in top}

    # (DriverInsight, KpiDefinition, current_day_n) triple 構築
    pairs = []
    for dr in insights:
        anomaly = anomaly_by_ks.get(dr.ks_id_ref)
        if anomaly is None:
            continue
        kpi_def = kpi_def_by_kp_id.get(anomaly.kp_id)
        if kpi_def is None:
            continue
        pairs.append((dr, kpi_def, anomaly.day_n))

    actions = batch_recommend_with_kpi_map(pairs=pairs, start_seq=1, provider=provider)
    return {"next_actions": actions}


def sentiment_node(state: T4State, provider: Optional[LLMProvider] = None) -> dict:
    """Slack/Teams/アンケート message → SentimentEvent (Week 3 active、 parallel to anomaly)。"""
    cp = state["cockpit_project"]
    messages = state.get("raw_messages", [])
    if not messages:
        return {"sentiment_events": []}
    events = batch_analyze_messages(cp_id=cp.cp_id, messages=messages, start_seq=1, provider=provider)
    return {"sentiment_events": events}


def vendor_overlap_node(state: T4State) -> dict:
    """VendorContract + SaasLicense overlap detect (Week 3 active、 parallel to anomaly)。"""
    contracts = state.get("raw_vendor_contracts", [])
    licenses = state.get("raw_saas_licenses", [])
    contracts = detect_vendor_overlap(contracts) if contracts else []
    licenses = detect_saas_overlap(licenses) if licenses else []
    return {"vendor_contracts": contracts, "saas_licenses": licenses}


def finalize_node(state: T4State) -> dict:
    """全 entity 集約、 T4Output container 構築。"""
    output = T4Output(
        cockpit_project=state["cockpit_project"],
        kpi_definitions=state.get("kpi_definitions", []),
        kpi_snapshots=state.get("kpi_snapshots", []),
        driver_insights=state.get("driver_insights", []),
        next_actions=state.get("next_actions", []),
        sentiment_events=state.get("sentiment_events", []),  # Week 3 active
        vendor_contracts=state.get("vendor_contracts", []),  # Week 3 active
        saas_licenses=state.get("saas_licenses", []),  # Week 3 active
        retention_risks=state.get("retention_risks", []),
    )
    return {"output": output}


# ─── DAG build ─────────────────────────────────────────────────────────

KPI_DIMENSIONS = ["cost", "revenue", "cash_gen", "working_capital"]


def build_t4_graph(provider: Optional[LLMProvider] = None):
    """T4 LangGraph DAG build + compile with MemorySaver (CVE-2026-28277 不発設計、 ADR-304)。

    Args:
        provider: LLMProvider instance (default = MockProvider)

    Returns:
        Compiled LangGraph executable (.invoke(initial_state) で literal 実行可)。
    """
    if provider is None:
        provider = default_provider()

    g = StateGraph(T4State)

    # Node 配置
    g.add_node("ingest_t3", ingest_t3_node)
    for dim in KPI_DIMENSIONS:
        g.add_node(f"anomaly_{dim}", _build_anomaly_node_for_dim(dim))
    g.add_node("top_anomaly_select", top_anomaly_select_node)
    g.add_node("driver_insight", lambda s: driver_insight_node(s, provider=provider))
    g.add_node("next_action", lambda s: next_action_node(s, provider=provider))
    g.add_node("sentiment", lambda s: sentiment_node(s, provider=provider))  # Week 3 active
    g.add_node("vendor_overlap", vendor_overlap_node)  # Week 3 active
    g.add_node("finalize", finalize_node)

    # Edge 配置
    g.add_edge(START, "ingest_t3")
    # 4 dim parallel anomaly + sentiment + vendor_overlap = 6 parallel branch from ingest_t3
    for dim in KPI_DIMENSIONS:
        g.add_edge("ingest_t3", f"anomaly_{dim}")
        g.add_edge(f"anomaly_{dim}", "top_anomaly_select")
    g.add_edge("ingest_t3", "sentiment")
    g.add_edge("ingest_t3", "vendor_overlap")
    # sequential: select → driver → next_action → finalize
    g.add_edge("top_anomaly_select", "driver_insight")
    g.add_edge("driver_insight", "next_action")
    # finalize は next_action + sentiment + vendor_overlap 3 branch を待つ
    g.add_edge("next_action", "finalize")
    g.add_edge("sentiment", "finalize")
    g.add_edge("vendor_overlap", "finalize")
    g.add_edge("finalize", END)

    # MemorySaver checkpointer (CVE-2026-28277 pattern 不発設計 = file 系 / SQLite 系 不使用)
    return g.compile(checkpointer=MemorySaver())
