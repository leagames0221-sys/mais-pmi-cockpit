"""Week 1 ingestion test (ADR-302 T3 → T4 mapping literal verify)。"""
from __future__ import annotations

import pytest

from src.integration.ingest_t3_output import ingest_t3_output


# ─── Mock T3 output fixtures ───────────────────────────────────────────

@pytest.fixture
def mock_t3_output_minimal() -> dict:
    """T3 API output minimal (IntegrationPlan のみ、 JPDay1Pattern 0 件)。"""
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
        "jp_day1_patterns": [],
    }


@pytest.fixture
def mock_t3_output_full() -> dict:
    """T3 API output full (5 軸 JPDay1Pattern 全 hit)。"""
    return {
        "integration_plan": {
            "ip_id": "IP-000000002",
            "industry": "小売",
            "size_band": "従業員 50-100 名",
            "day1_target_date": "2026-10-15",
        },
        "plan_nodes": [],
        "dependency_edges": [],
        "risk_scores": [],
        "communication_kits": [],
        "jp_day1_patterns": [
            {"jpd1_id": "JPD1-000001", "axis": "union_relation", "severity": "high",
             "summary_redacted": "(redacted: 組合対応 high)"},
            {"jpd1_id": "JPD1-000002", "axis": "family_integration", "severity": "medium",
             "summary_redacted": "(redacted: 同族統合 medium)"},
            {"jpd1_id": "JPD1-000003", "axis": "business_practice", "severity": "low",
             "summary_redacted": "(redacted: 商習慣 low)"},
            {"jpd1_id": "JPD1-000004", "axis": "bank_relation", "severity": "high",
             "summary_redacted": "(redacted: 取引銀行折衝 high)"},
            {"jpd1_id": "JPD1-000005", "axis": "trade_custom", "severity": "medium",
             "summary_redacted": "(redacted: 取引慣行 medium)"},
        ],
    }


# ─── Test: T3 IP → T4 CP 1:1 inherit ───────────────────────────────────

def test_ingest_cp_inherit_ip(mock_t3_output_minimal):
    output = ingest_t3_output(mock_t3_output_minimal)
    assert output.cockpit_project.source_t3_ip_id == "IP-000000001"
    assert output.cockpit_project.cp_id == "CP-000001"
    assert output.cockpit_project.industry == "製造業"
    assert output.cockpit_project.status == "initialized"


def test_ingest_day100_auto_calc(mock_t3_output_minimal):
    output = ingest_t3_output(mock_t3_output_minimal)
    # day1=2026-09-01 + 100 日 = 2026-12-10
    assert output.cockpit_project.day1_anchor_date == "2026-09-01"
    assert output.cockpit_project.day100_end_date == "2026-12-10"


# ─── Test: Default KPI 4 dim 生成 ──────────────────────────────────────

def test_ingest_default_kpi_4_dim(mock_t3_output_minimal):
    output = ingest_t3_output(mock_t3_output_minimal)
    assert len(output.kpi_definitions) == 4
    dimensions = {kp.dimension for kp in output.kpi_definitions}
    assert dimensions == {"cost", "revenue", "cash_gen", "working_capital"}


# ─── Test: T3 JPDay1Pattern → T4 RetentionRisk trigger (ADR-302 mapping) ─

def test_ingest_jp_patterns_empty_no_rt(mock_t3_output_minimal):
    output = ingest_t3_output(mock_t3_output_minimal)
    assert output.retention_risks == []


def test_ingest_jp_patterns_full_rt_trigger(mock_t3_output_full):
    output = ingest_t3_output(mock_t3_output_full)
    # 5 軸 中、 RT trigger 対象 = union_relation / family_integration / business_practice = 3 件
    # bank_relation / trade_custom = VC trigger 対象 (Week 3、 本 Week 1 では 0)
    assert len(output.retention_risks) == 3
    triggered_axes_dims = {rt.dimension for rt in output.retention_risks}
    assert triggered_axes_dims == {"organization", "culture", "business_practice"}


def test_ingest_severity_to_score(mock_t3_output_full):
    output = ingest_t3_output(mock_t3_output_full)
    # severity high → 85、 medium → 60、 low → 30
    rt_by_dim = {rt.dimension: rt for rt in output.retention_risks}
    assert rt_by_dim["organization"].score == 85  # union_relation high
    assert rt_by_dim["culture"].score == 60  # family_integration medium
    assert rt_by_dim["business_practice"].score == 30  # business_practice low


def test_ingest_rt_jpd1_link(mock_t3_output_full):
    output = ingest_t3_output(mock_t3_output_full)
    # 全 RT に triggered_jp_patterns literal 含まれる
    for rt in output.retention_risks:
        assert len(rt.triggered_jp_patterns) >= 1
        assert rt.triggered_jp_patterns[0].startswith("JPD1-")


# ─── Test: empty list invariants ───────────────────────────────────────

def test_ingest_empty_lists_for_week2_3(mock_t3_output_full):
    output = ingest_t3_output(mock_t3_output_full)
    # KpiSnapshot / DriverInsight / NextAction / SentimentEvent / VendorContract / SaasLicense
    # は Week 2-3 で literal 生成、 Week 1 では empty literal verify
    assert output.kpi_snapshots == []
    assert output.driver_insights == []
    assert output.next_actions == []
    assert output.sentiment_events == []
    assert output.vendor_contracts == []
    assert output.saas_licenses == []
