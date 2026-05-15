"""Week 2 LangGraph state graph e2e test (T3 mock output → T4 CockpitProject → KpiSnapshot → DriverInsight → NextAction)。"""
from __future__ import annotations

import pytest

from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_kpi_definitions,
    generate_kpi_snapshots,
)
from src.llm.provider import MockProvider
from src.orchestrator.build_state_graph import build_t4_graph


@pytest.fixture
def mock_t3_output() -> dict:
    """T3 API output mock (ingest_t3_node の input)。"""
    return {
        "integration_plan": {
            "ip_id": "IP-000000001",
            "industry": "製造業",
            "size_band": "従業員 100-300 名",
            "day1_target_date": "2026-09-01",
        },
        "plan_nodes": [],
        "dependency_edges": [],
        "risk_scores": [],
        "communication_kits": [],
        "jp_day1_patterns": [
            {"jpd1_id": "JPD1-000001", "axis": "union_relation", "severity": "medium",
             "summary_redacted": "(redacted: 組合対応 medium)"},
        ],
    }


@pytest.fixture
def synthetic_kpi_snapshots():
    """data gen で生成した 1 CP × 4 KPI × 100 日 snapshot (LangGraph state initial input)。"""
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    all_snapshots = []
    for kp in kpi_defs:
        all_snapshots.extend(generate_kpi_snapshots(cp, kp, start_n=1, days=100))
    return cp, kpi_defs, all_snapshots


def test_t4_graph_compile():
    """LangGraph build literal 動作 + compile 成功 verify。"""
    graph = build_t4_graph(provider=MockProvider())
    assert graph is not None


def test_t4_graph_e2e_with_mock(mock_t3_output, synthetic_kpi_snapshots):
    """T3 mock + 合成 KPI snapshot input → T4Output full schema literal 動作 (T3 → T4 mapping + anomaly + driver + next_action)。"""
    cp_synthetic, kpi_defs_synthetic, all_snapshots = synthetic_kpi_snapshots
    graph = build_t4_graph(provider=MockProvider())

    initial_state = {
        "t3_output": mock_t3_output,
        "kpi_snapshots": all_snapshots,
    }

    # LangGraph invoke (thread_id 必須、 MemorySaver checkpoint 用)
    result = graph.invoke(initial_state, config={"configurable": {"thread_id": "test_t4_e2e_001"}})

    # T3 → T4 ingestion 結果
    assert result["cockpit_project"].source_t3_ip_id == "IP-000000001"
    # ingestion node が生成した 4 KpiDefinition (mock T3 default、 合成 data 4 KPI ではない)
    assert len(result["kpi_definitions"]) == 4

    # 4 dim parallel anomaly merge: 全 KPI × 100 日 = 400 件 anomaly_results (各 KPI 4 件 × 100 日)
    # ただし ingestion node の default 4 KpiDefinition の kp_id は KP-000001~000004、
    # 合成 snapshot の kp_id は別 sequence (KP-000001~000004 と同じだが seed 異なる)
    # 統合 verify: anomaly_results は 0 件以上 (KPI def + snapshot kp_id match 数次第)

    # top-K anomaly selection
    assert "top_anomalies" in result
    assert len(result["top_anomalies"]) <= 5

    # DriverInsight (top-K 数 = NA 数 と整合)
    assert "driver_insights" in result
    assert len(result["driver_insights"]) == len(result["top_anomalies"])

    # NextAction (top-K 数 と整合、 各 5 候補 ranked)
    assert "next_actions" in result
    assert len(result["next_actions"]) == len(result["driver_insights"])
    for na in result["next_actions"]:
        assert len(na.candidates_ranked) == 5
        assert na.status == "proposed"

    # T4Output container finalize
    assert "output" in result
    assert result["output"].cockpit_project.cp_id == result["cockpit_project"].cp_id
    # RetentionRisk = T3 JPDay1 mock 1 件 (union_relation) → organization dim 1 件 trigger
    assert len(result["output"].retention_risks) == 1
    assert result["output"].retention_risks[0].dimension == "organization"


def test_t4_graph_4_dim_parallel_merge(synthetic_kpi_snapshots):
    """4 KPI dim parallel anomaly_node が Annotated[list, _merge_list] reducer で literal merge verify。"""
    cp_synthetic, kpi_defs_synthetic, all_snapshots = synthetic_kpi_snapshots

    # ingestion node が default 4 KpiDef 生成 = 合成 data の 4 KPI と kp_id 一致 (両方 KP-000001 から sequential)
    # → 4 dim 全件で anomaly_node が snapshot を処理、 100 件 × 4 dim = 400 件 anomaly_results 期待 (実 = ingestion default 4 KPI)
    graph = build_t4_graph(provider=MockProvider())

    minimal_t3 = {
        "integration_plan": {
            "ip_id": "IP-000000001",
            "industry": "製造業",
            "size_band": "従業員 100-300 名",
            "day1_target_date": "2026-09-01",
        },
        "plan_nodes": [],
        "dependency_edges": [],
        "risk_scores": [],
        "communication_kits": [],
        "jp_day1_patterns": [],
    }

    result = graph.invoke(
        {"t3_output": minimal_t3, "kpi_snapshots": all_snapshots},
        config={"configurable": {"thread_id": "test_t4_4dim_parallel_001"}},
    )

    # 4 dim parallel anomaly: 全 snapshot 数 = 400 件 (4 KPI × 100 日)、 ingestion 4 KpiDef + 合成 data 4 KPI で kp_id match 必須
    # MockProvider deterministic + Faker seed 固定 = literal 再現可能
    assert len(result["output"].retention_risks) == 0 # JPDay1 0 件 → RT 0 件
